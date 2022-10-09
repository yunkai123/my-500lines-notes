from cluster import *
from . import utils

class Tests(utils.ComponentTestCase):

    def setUp(self):
        super(Tests, self).setUp()
        self.ac = Acceptor(self.node)

    def assertState(self, ballot_num, accepted_proposals):
        self.assertEqual(self.ac.ballot_num, ballot_num)
        self.assertEqual(self.ac.accepted_proposals, accepted_proposals)

    def test_prepare_new_ballot(self):
        """当 PREPARE 中为新选票, Acceptor 返回 PROMISE 消息和新选票
        并发送 ACCEPTING 消息"""
        proposal = Proposal('cli', 123, 'INC')
        self.ac.accepted_proposals = {33: (Ballot(19, 19), proposal)}
        self.ac.ballot_num = Ballot(10, 10)
        self.node.fake_message(Prepare(
            # 比 acceptor 的选票编号更新
            ballot_num=Ballot(19, 19)
        ), sender='SC')
        self.assertMessage(['F999'], Accepting(leader='SC'))
        accepted_proposals = {33: (Ballot(19, 19), proposal)}
        self.verifyAcceptedProposals(accepted_proposals)
        self.assertMessage(['SC'], Promise(
            # 回复更新后的选票编号
            ballot_num=Ballot(19, 19),
            # 包含 accepted_proposals 选票
            accepted_proposals=accepted_proposals
        ))
        
        self.assertState(Ballot(19, 19), {33: (Ballot(19, 19), proposal)})

    def test_prepare_old_ballot(self):
        """当 PREPARE 中为旧选票, Acceptor 返回 PROMISE 消息和存在的较新的选票，
        不会发送 ACCEPTING 消息"""
        self.ac.ballot_num = Ballot(10, 10)
        self.node.fake_message(Prepare(
            ballot_num=Ballot(5, 10)
        ), sender='SC')
        accepted_proposals = {}
        self.verifyAcceptedProposals(accepted_proposals)
        self.assertMessage(['SC'], Promise(
            # 回复较新的选票编号
            ballot_num=Ballot(10, 10),
            accepted_proposals=accepted_proposals
        ))
        self.assertState(Ballot(10, 10), {})

    def test_accepted_new_ballot(self):
        """当 ACCEPT 中包含新选票, Acceptor 返回 ACCEPTED 和新选票编号
            并记录 proposal 为 accepted_proposals"""
        proposal = Proposal('cli', 123, 'INC')
        self.ac.ballot_num = Ballot(10, 10)
        self.node.fake_message(Accept(
            slot=33,
            ballot_num=Ballot(19, 19),
            proposal=proposal
        ), sender='CMD')
        self.assertMessage(['CMD'], Accepted(
            slot=33,
            # 回复更新后的选票编号
            ballot_num=Ballot(19, 19)
        ))
        self.assertState(Ballot(19, 19), {33: (Ballot(19, 19), proposal)})

    def test_accepted_old_ballot(self):
        """当 ACCEPT 中包含旧选票, Acceptor 返回 ACCEPTED 以及那个
            已经接受的选票, 并不再接受选票"""
        proposal = Proposal('cli', 123, 'INC')
        self.ac.ballot_num = Ballot(10, 10)
        self.node.fake_message(Accept(
            slot=33,
            ballot_num=Ballot(5, 5),
            proposal=proposal
        ), sender='CMD')
        self.assertMessage(['CMD'], Accepted(
            slot=33,
            # 回复较新的选票编号
            ballot_num = Ballot(10, 10)
        ))
        # 不接受提议
        self.assertState(Ballot(10, 10), {})