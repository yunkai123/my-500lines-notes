class ValueRef(object):
    """ 用来在数据库中存储二进制对象的Python对象
    """
    def prepare_to_store(self, storage):
        pass

    @staticmethod
    def referent_to_string(referent):
        """二进制转字符串
        """
        return referent.encode('utf-8')

    @staticmethod
    def string_to_referent(string):
        """字符串转二进制
        """
        return string.decode('utf-8')

    def __init__(self, referent=None, address=0):
        self._referent = referent
        self._address = address

    @property
    def address(self):
        return self._address

    def get(self, storage):
        """获取存储的对象
        """
        if self._referent is None and self._address:
            self._referent = self.string_to_referent(storage.read(self._address))
        return self._referent

    def store(self, storage):
        """将对象存储进去
        """
        if self._referent is not None and not self._address:
            self.prepare_to_store(storage)
            self._address = storage.write(self.referent_to_string(self._referent))

class LogicalBase(object):
    """作为父类定义相关接口
    """
    node_ref_class = None
    value_ref_class = ValueRef

    def __init__(self, storage):
        self._storage = storage
        self._refresh_tree_ref()

    def commit(self):
        self._tree_ref.store(self._storage)
        self._storage.commit_root_address(self._tree_ref.address)

    def _refresh_tree_ref(self):
        self._tree_ref = self.node_ref_class(
            address=self._storage.get_root_address()
        )

    def get(self, key):
        if not self._storage.locked:
            self._refresh_tree_ref()
        return self._get(self._follow(self._tree_ref), key)

    def set(self, key, value):
        print(key + ":" + str(self._storage.locked))
        if self._storage.lock():
            self._refresh_tree_ref()
        self._tree_ref = self._insert(
            self._follow(self._tree_ref), key, self.value_ref_class(value))

    def pop(self, key):
        if self._storage.lock():
            self._refresh_tree_ref()
        self._tree_ref = self._delete(
            self._follow(self._tree_ref), key)

    def _follow(self, ref):
        return ref.get(self._storage)

    def __len__(self):
        if not self._storage.locked:
            self._refresh_tree_ref()
        root = self._follow(self._tree_ref)
        if root:
            return root.length
        else:
            return 0