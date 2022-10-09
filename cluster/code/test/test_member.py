""" 
测试 Member 对象
"""

from cluster import *
from . import fake_network
import mock
import unittest


class FakeRequest(object):

    def __init__(self, node, input_value, callback):
        self.node = node
        self.input_value = input_value
        self.callback = callback

    def start(self):
        self.callback(('ROTATED', self.node, self.input_value))


class Tests(unittest.TestCase):

    def setUp(self):
        self.Node = mock.create_autospec(Node)
        self.Bootstrap = mock.create_autospec(Bootstrap)
        self.Seed = mock.create_autospec(Seed)
        self.network = fake_network.FakeNetwork()
        self.state_machine = mock.Mock(name='state_machine')
        self.cls_args = dict(bootstrap_cls=self.Bootstrap, seed_cls=self.Seed)

    def test_no_seed(self):
        """在没有 seed 的情况下, Member 构造函数创建一个 Bootstrap"""
        sh = Member(self.state_machine, network=self.network,
                           peers=['p1', 'p2'], **self.cls_args)
        self.assertFalse(self.Seed.called)
        self.Bootstrap.assert_called_with(
            self.network.node, execute_fn=self.state_machine, peers=['p1', 'p2'])

    def test_Member(self):
        """在包含 seed 的情况下, Member 构造函数创建一个 Node 和一个 ClusterSeed"""
        sh = Member(self.state_machine, network=self.network,
                           peers=['p1', 'p2'], seed=44,
                           **self.cls_args)
        self.assertFalse(self.Bootstrap.called)
        self.Seed.assert_called_with(
            self.network.node, initial_state=44, peers=['p1', 'p2'],
            execute_fn=self.state_machine)

    def test_start(self):
        """Member.start 启动角色和 self.thread 中的节点"""
        sh = Member(self.state_machine, network=self.network,
                       peers=['p1', 'p2'], **self.cls_args)
        sh.start()
        sh.thread.join()
        sh.startup_role.start.assert_called_once_with()
        self.assertTrue(self.network.ran)

    def test_invoke(self):
        """Member.invoke 创建一个新 Request， 启动它并等待它的回调被调用"""
        sh = Member(self.state_machine, network=self.network,
                       peers=['p1', 'p2'], **self.cls_args)
        res = sh.invoke('ROTATE', request_cls=FakeRequest)
        self.assertEqual(sh.requester, None)
        self.assertEqual(res, ('ROTATED', sh.node, 'ROTATE'))