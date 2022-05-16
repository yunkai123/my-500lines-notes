import pickle

from dbdb.logical import LogicalBase, ValueRef

class BinaryNode(object):
    """二叉树节点
    """
    @classmethod
    def from_node(cls, node, **kwargs):
        """根据旧节点生成新节点
        """
        length = node.length
        if 'left_ref' in kwargs:
            length += kwargs['left_ref'].length - node.left_ref.length
        if 'right_ref' in kwargs:
            length += kwargs['right_ref'].length - node.right_ref.length

        return cls(
            left_ref=kwargs.get('left_ref', node.left_ref),
            key=kwargs.get('key', node.key),
            value_ref=kwargs.get('value_ref', node.value_ref),
            right_ref=kwargs.get('right_ref', node.right_ref),
            length=length
        )

    def __init__(self, left_ref, key, value_ref, right_ref, length):
        self.left_ref = left_ref # 左子树引用
        self.key = key
        self.value_ref = value_ref
        self.right_ref = right_ref # 右子树引用
        self.length = length

    def store_refs(self, storage):
        """储存节点值和左右子树的引用
        """
        self.value_ref.store(storage)
        self.left_ref.store(storage)
        self.right_ref.store(storage)

class BinaryNodeRef(ValueRef):
    """节点的引用，仅包含一个地址用来节省内存
    """
    def prepare_to_store(self, storage):
        if self._referent:
            self._referent.store_refs(storage)

    @property
    def length(self):
        """节点长度
        """
        if self._referent is None and self._address:
            raise RuntimeError('Asking for BinaryNodeRef length of unloaded node')
        if self._referent:
            return self._referent.length
        else:
            return 0

    @staticmethod
    def referent_to_string(referent):
        """将节点序列化成JSON
        """
        return pickle.dumps({
            'left': referent.left_ref.address,
            'key': referent.key,
            'value': referent.value_ref.address,
            'right': referent.right_ref.address,
            'length': referent.length
        })

    @staticmethod
    def string_to_referent(string):
        """将JSON反序列化为节点对象
        """
        d = pickle.loads(string)
        return BinaryNode(
            BinaryNodeRef(address=d['left']),
            d['key'],
            ValueRef(address=d['value']),
            BinaryNodeRef(address=d['right']),
            d['length']
        )

class BinaryTree(LogicalBase):
    """二叉树
    """
    node_ref_class = BinaryNodeRef

    def _get(self, node, key):
        """在node中查找指定的key
        """
        while node is not None:
            if key < node.key:
                node = self._follow(node.left_ref)
            elif node.key < key:
                node = self._follow(node.right_ref)
            else:
                return self._follow(node.value_ref)
        raise KeyError

    def _insert(self, node, key, value_ref):
        """在node中插入指定的key
        """
        if node is None:
            new_node = BinaryNode(
                self.node_ref_class(), key, value_ref, self.node_ref_class(), 1
            )
        elif key < node.key:
            new_node = BinaryNode.from_node(
                node, left_ref=self._insert(self._follow(node.left_ref), key, value_ref)
            )
        elif node.key < key:
            new_node = BinaryNode.from_node(
                node, right_ref=self._insert(self._follow(node.right_ref), key, value_ref)
            )
        else:
            new_node = BinaryNode.from_node(node, value_ref=value_ref)
        return self.node_ref_class(referent=new_node)

    def _delete(self, node, key):
        """在node中删除指定的key
        """
        if node is None:
            raise KeyError
        elif key < node.key:
            new_node = BinaryNode.from_node(
                node, left_ref=self._delete(self._follow(node.left_ref), key)
            )
        elif node.key < key:
            new_node = BinaryNode.from_node(
                node, right_ref=self._delete(self._follow(node.right_ref), key)
            )
        else:
            left = self._follow(node.left_ref)
            right = self._follow(node.right_ref)
            if left and right:
                replacement = self._find_max(left)
                left_ref = self._delete(
                    self._follow(node.left_ref), replacement.key
                )
                new_node = BinaryNode(
                    left_ref,
                    replacement.key,
                    replacement.value_ref,
                    node.right_ref,
                    left_ref.length + node.right_ref.length + 1
                )
            elif left:
                return node.left_ref
            else:
                return node.right_ref
        return self.node_ref_class(referent=new_node)

    def _find_max(self, node):
        """ 查找最大节点
        """
        while True:
            next_node = self._follow(node.right_ref)
            if next_node is None:
                return node
            node = next_node


