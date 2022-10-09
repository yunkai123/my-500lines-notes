from cluster import *
from . import utils
import mock

CLIENT_ID = 999999


"""
测试 Requester 类
"""

class Tests(utils.ComponentTestCase):

    def setUp(self):
        super(Tests, self).setUp()
        self.callback = mock.Mock(name='callback')
        # mock next(client_ids) 的返回
        with mock.patch.object(Requester, 'client_ids') as client_ids:
            # next方法实际是由 __next__封装来的
            client_ids.__next__.return_value = CLIENT_ID
            self.req = Requester(self.node, 10, self.callback)
        self.assertEqual(self.req.client_id, CLIENT_ID)

    def test_function(self):
        """Requester should repeatedly send INVOKE until receiving a matching INVOKED"""
        self.req.start()
        self.assertMessage(['F999'], Invoke(caller='F999', client_id=CLIENT_ID, input_value=10))
        self.network.tick(INVOKE_RETRANSMIT)
        self.assertMessage(['F999'], Invoke(caller='F999', client_id=CLIENT_ID, input_value=10))
        # non-matching
        self.node.fake_message(Invoked(client_id=333, output=22))
        self.network.tick(INVOKE_RETRANSMIT)
        self.assertMessage(['F999'], Invoke(caller='F999', client_id=CLIENT_ID, input_value=10))
        self.assertFalse(self.callback.called)
        self.node.fake_message(Invoked(client_id=CLIENT_ID, output=20))
        self.callback.assert_called_with(20)
        self.assertUnregistered()