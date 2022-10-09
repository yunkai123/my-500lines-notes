'''
测试工具类，为所有测试类的父类，存放一些测试公共方法
'''

from cluster import *
from . import fake_network
import unittest

class ComponentTestCase(unittest.TestCase):

    def setUp(self):
        '''所有测试执行前的启动方法，创建伪网络和伪节点'''
        self.network = fake_network.FakeNetwork()
        self.node = fake_network.FakeNode(self.network)

    def tearDown(self):
        '''所有测试执行后的结尾方法，判断节点中是否还有未发送消息'''
        if self.node.sent:
            self.fail("extra messages from node: %r" % (self.node.sent,))

    def assertMessage(self, destinations, message):
        '''断言消息'''
        got = self.node.sent.pop(0)
        self.assertEqual((sorted(got[0]), got[1]),
            (sorted(destinations), message))

    def assertNoMessages(self):
        '''断言空消息'''
        self.assertEqual(self.node.sent, [])

    def assertTimers(self, times):
        '''断言计时器'''
        self.assertEqual(self.node.network.get_times(), times)

    def assertUnregistered(self):
        '''断言角色是否均注销'''
        self.assertEqual(self.node.roles, [])

    def verifyAcceptedProposals(self, accepted_proposals):
        """验证 promise 的 ``accepted_proposals`` 字段的格式是
        将 slot 映射到 (ballot, proposal) 元组的字典"""
        self.assertIsInstance(accepted_proposals, dict)
        for k, v in accepted_proposals.items(): # Python3 中使用 items()
            self.assertIsInstance(k, int)
            self.assertIsInstance(v, tuple)
            self.assertEqual(len(v), 2)
            self.assertIsInstance(v[0], Ballot)
            self.assertIsInstance(v[1], Proposal)