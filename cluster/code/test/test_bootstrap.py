'''
对 Bootstrap 进行测试
'''
from cluster import *
import mock
from . import utils

class Tests(utils.ComponentTestCase):

    def setUp(self):
        super(Tests, self).setUp()
        self.cb_args = None
        self.execute_fn = mock.Mock()

        self.Replica = mock.Mock(autospec=Replica)
        self.Acceptor = mock.Mock(autospec=Acceptor)
        self.Leader = mock.Mock(autospec=Leader)
        self.Commander = mock.Mock(autospec=Commander)
        self.Scout = mock.Mock(autospec=Scout)

        self.bs = Bootstrap(self.node, ['p1', 'p2', 'p3'], self.execute_fn,
            replica_cls=self.Replica, acceptor_cls=self.Acceptor,
            leader_cls=self.Leader, commander_cls=self.Commander,
            scout_cls=self.Scout)

    def test_retransmit(self):
        """ start()之后，bootstrap 依次发送 JOIN 消息到每个节点直到接收到 Welcome 消息"""
        self.bs.start()
        for recip in 'p1', 'p2', 'p3', 'p1':
            self.assertMessage([recip], Join())
            self.network.tick(JOIN_RETRANSMIT)
        self.assertMessage(['p2'], Join())

        self.node.fake_message(Welcome(state='st', slot='s1', decisions={}, leader=None))
        self.Acceptor.assert_called_with(self.node)
        self.Replica.assert_called_with(self.node, execute_fn=self.execute_fn, decisions={},
            state='st', slot='s1', peers=['p1', 'p2', 'p3'], leader=None)
        self.Leader.assert_called_with(self.node, peers=['p1', 'p2', 'p3'],
            commander_cls=self.Commander,
            scout_cls=self.Scout)
        self.Leader().start.assert_called_with()
        self.assertTimers([])
        self.assertUnregistered()