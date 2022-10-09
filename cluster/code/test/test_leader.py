"""
测试 Leader 类
"""

from cluster import *
from . import utils
import mock

PROPOSAL1 = Proposal(caller='cli', client_id=123, input='one')
PROPOSAL2 = Proposal(caller='cli', client_id=125, input='two')
PROPOSAL3 = Proposal(caller='cli', client_id=127, input='tre')

Commander = mock.create_autospec(Commander)
Scout = mock.create_autospec(Scout)


class Tests(utils.ComponentTestCase):

    def setUp(self):
        super(Tests, self).setUp()
        Scout.reset_mock()
        Commander.reset_mock()
        self.ldr = Leader(self.node, ['p1', 'p2'],
                          commander_cls=Commander,
                          scout_cls=Scout)

    def assertScoutStarted(self, ballot_num):
        Scout.assert_called_once_with(self.node, ballot_num, ['p1', 'p2'])
        scout = Scout(self.node, ballot_num, ['p1', 'p2'])
        scout.start.assert_called_once_with()

    def assertNoScout(self):
        self.assertFalse(self.ldr.scouting)

    def assertCommanderStarted(self, ballot_num, slot, proposal):
        Commander.assert_called_once_with(self.node, ballot_num, slot, proposal, ['p1', 'p2'])
        cmd = Commander(self.node, ballot_num, slot, proposal, ['p1', 'p2'])
        cmd.start.assert_called_with()

    def activate_leader(self):
        self.ldr.active = True

    def fake_proposal(self, slot, proposal):
        self.ldr.proposals[slot] = proposal

    # 测试用例

    def test_propose_inactive(self):
        """当不活动时接收到 PROPOSE 会产生 scout """
        self.node.fake_message(Propose(slot=10, proposal=PROPOSAL1))
        self.assertScoutStarted(Ballot(0, 'F999'))

    def test_propose_scouting(self):
        """已经 scount 的时候接收到 PROPOSE 会被忽略"""
        self.node.fake_message(Propose(slot=10, proposal=PROPOSAL1))
        self.node.fake_message(Propose(slot=10, proposal=PROPOSAL1))
        self.assertScoutStarted(Ballot(0, 'F999'))

    def test_propose_active(self):
        """活动的时候接收到 PROPOSE 产生 commander"""
        self.activate_leader()
        self.node.fake_message(Propose(slot=10, proposal=PROPOSAL1))
        self.assertCommanderStarted(Ballot(0, 'F999'), 10, PROPOSAL1)

    def test_propose_already(self):
        """对于已使用 slot 的 PROPOSE 会被忽略"""
        self.activate_leader()
        self.fake_proposal(10, PROPOSAL2)
        self.node.fake_message(Propose(slot=10, proposal=PROPOSAL1))
        self.assertEqual(Commander.mock_calls, []) 
        self.assertMessage(['F999'], Conflict(slot=10, max_slot=10, proposal=Proposal(caller='cli', client_id=123, input='one')))

    def test_commander_finished_preempted(self):
        """当 commander 被抢占，选票编号增加，
        leader不再活跃， 但没有 scout 产生"""
        self.activate_leader()
        self.node.fake_message(Propose(slot=10, proposal=PROPOSAL1))
        self.node.fake_message(Preempted(slot=10, preempted_by=Ballot(22, 'XXXX')))
        self.assertEqual(self.ldr.ballot_num, Ballot(23, 'F999'))
        self.assertNoScout()
        self.assertFalse(self.ldr.active)

    def test_scout_finished_adopted(self):
        """当一个 scout 结束且 leader 被采纳，
        接受的提议合并且 leader 变得活跃"""
        self.ldr.spawn_scout()
        self.ldr.proposals[9] = PROPOSAL2
        self.node.fake_message(Adopted(ballot_num=Ballot(0, 'F999'),
            accepted_proposals={10: PROPOSAL3}))
        self.assertNoScout()
        self.assertTrue(self.ldr.active)
        self.assertEqual(self.ldr.proposals, {
            9: PROPOSAL2,
            10: PROPOSAL3,
        })

    def test_scout_finished_preempted(self):
        """当一个 scout 结束且 leader 被抢占，
        leader 变得不活跃且投票编号更新"""
        self.ldr.spawn_scout()
        self.node.fake_message(Preempted(slot=None, preempted_by=Ballot(22, 'F999')))
        self.assertNoScout()
        self.assertEqual(self.ldr.ballot_num, Ballot(23, 'F999'))
        self.assertFalse(self.ldr.active)