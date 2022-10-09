from cluster import *
from . import utils

class Tests(utils.ComponentTestCase):

    def setUp(self):
        super(Tests, self).setUp()
        self.cb_args = None
        self.slot = 10
        self.proposal = Proposal(caller='cli', client_id=123, input='inc')
        self.ballot_num = Ballot(91, 82)
        self.cmd = Commander(
            self.node, ballot_num=self.ballot_num,
            slot=self.slot, proposal=self.proposal,
            peers=['p1', 'p2', 'p3']
        )
        self.accept_message = Accept(slot=self.slot, ballot_num=self.ballot_num,
            proposal=self.proposal)

    def test_retransmit(self):
        """start() 之后， commander 重复发送 ACCEPT 消息给没有回复的对等节点"""
        self.cmd.start()
        self.assertMessage(['p1', 'p2', 'p3'], self.accept_message)
        self.network.tick(ACCEPT_RETRANSMIT)
        self.assertMessage(['p1', 'p2', 'p3'], self.accept_message)
        
        self.node.fake_message(
            Accepted(slot=self.slot, ballot_num=self.ballot_num), sender='p2'
        )
        self.network.tick(ACCEPT_RETRANSMIT)
        self.assertMessage(['p1', 'p3'], self.accept_message)
        self.network.tick(ACCEPT_RETRANSMIT)
        self.assertMessage(['p1', 'p3'], self.accept_message)
        self.node.fake_message(
            Accepted(slot=self.slot, ballot_num=self.ballot_num), sender='p1'
        )

        # quorum (3/2+1 = 2) reached
        self.assertMessage(['p1', 'p2', 'p3'], Decision(slot=self.slot, proposal=self.proposal))
        self.assertMessage(['F999'], Decided(slot=self.slot))
        self.assertTimers([])
        self.assertUnregistered()

    def test_wrong_slot(self):
        """Commander 忽略其它 commander 的 ACCEPTED 消息"""
        self.cmd.start()
        self.assertMessage(['p1', 'p2', 'p3'], self.accept_message)
        other_slot = 999
        self.node.fake_message(
            Accepted(slot=other_slot, ballot_num=self.ballot_num), sender='p1')
        self.network.tick(ACCEPT_RETRANSMIT)
        # p1 依旧在列表中
        self.assertMessage(['p1', 'p2', 'p3'], self.accept_message)

    def test_preempted(self):
        """如果 commander 接收到一个拥有不同选票编号的 ACCEPTED 响应，说明它被抢占"""
        self.cmd.start()
        self.assertMessage(['p1', 'p2', 'p3'], self.accept_message)
        other_ballot_num = Ballot(99, 99)
        self.node.fake_message(
            Accepted(slot=self.slot, ballot_num=other_ballot_num), sender='p1')
        self.assertMessage(['F999'], Preempted(slot=self.slot, preempted_by=other_ballot_num))
        self.assertTimers([])
        self.assertUnregistered()
