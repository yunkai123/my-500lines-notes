"""
测试 Network 类
"""

from cluster import *
import mock
import unittest


class TestComp(Role):
    join_called = False

    def do_Join(self, sender):
        self.join_called = True
        self.kill()


class NetworkTests(unittest.TestCase):

    def setUp(self):
        self.network = Network(1234)

    def kill(self, node):
        del self.network.nodes[node.address]

    def test_comm(self):
        """Node 可以成功地在实例之间发送消息"""
        sender = self.network.new_node('S')
        receiver = self.network.new_node('R')
        comp = TestComp(receiver)
        comp.kill = lambda: self.kill(receiver)
        sender.send([receiver.address], Join())
        self.network.run()
        self.assertTrue(comp.join_called)

    def test_timeout(self):
        """Node 的超时在合适的时间触发"""
        node = self.network.new_node('T')

        cb = mock.Mock(side_effect=lambda: self.kill(node))
        self.network.set_timer(node.address, 0.01, cb)
        self.network.run()
        self.assertTrue(cb.called)

    def test_cancel_timeout(self):
        """Node 的超时如果被撤消则不会发生"""
        node = self.network.new_node('C')

        def fail():
            raise RuntimeError("nooo")

        nonex = self.network.set_timer(node.address, 0.01, fail)

        cb = mock.Mock(side_effect=lambda: self.kill(node))
        self.network.set_timer(node.address, 0.02, cb)
        nonex.cancel()
        self.network.run()
        self.assertTrue(cb.called)