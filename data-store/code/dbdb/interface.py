'''
接口文件，定义 DBDB，包含 get set del 等方法
'''

from dbdb.binary_tree import BinaryTree
from dbdb.physical import Storage

class DBDB(object):

    def __init__(self, f):
        # 存储
        self._storage = Storage(f)
        # 二叉树
        self._tree = BinaryTree(self._storage)

    def _assert_not_closed(self):
        """断言数据库夫是否关闭
        """
        if self._storage.closed:
            raise ValueError('Database closed.')

    def close(self):
        """关闭数据库
        """
        self._storage.close()

    def commit(self):
        """提交更新
        """
        self._assert_not_closed()
        self._tree.commit()

    def __getitem__(self, key):
        """ get 操作
        """
        self._assert_not_closed()
        return self._tree.get(key)

    def __setitem__(self, key, value):
        """ set 操作
        """
        self._assert_not_closed()
        return self._tree.set(key, value)

    def __delitem__(self, key):
        """ del 操作
        """
        self._assert_not_closed()
        return self._tree.pop(key)

    def __contains__(self, key):
        """ 判断 key 是否存在
        """
        try:
            self[key]
        except KeyError:
            return False
        else:
            return True
    
    def __len__(self):
        """ 计算长度
        """
        return len(self._tree)
