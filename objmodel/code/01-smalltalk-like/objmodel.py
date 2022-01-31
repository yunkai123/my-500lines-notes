MISSING = object()

class Base(object):
    """所有对象模型类都要继承的基类"""

    def __init__(self, cls, fields):
        """每个对象都有一个类"""
        self.cls = cls
        self._fields = fields

    def read_attr(self, fieldname):
        """从对象中读取`filedname`字段"""
        return self._read_dict(fieldname)

    def write_attr(self, fieldname, value):
        """将字段`fieldname`写入对象"""
        self._write_dict(fieldname, value)

    def isinstance(self, cls):
        """如果对象是类的实例则返回True"""
        return self.cls.issubclass(cls)

    def callmethod(self, methname, *args):
        """在对象上使用参数 `args` 调用方法 `methname`"""
        meth = self.cls._read_from_class(methname)
        return meth(self, *args)

    def _read_dict(self, fieldname):
        """从对象字典中读取字段 `fieldname`"""
        return self._fields.get(fieldname, MISSING)

    def _write_dict(self, fieldname, value):
        """将一个字段 `fieldname` 写入到对象字典中"""
        self._fields[fieldname] = value

class Instance(Base):
    """用户定义类的实例"""

    def __init__(self, cls):
        assert isinstance(cls, Class)
        Base.__init__(self, cls, {})

class Class(Base):
    """一个用户定义的类"""

    def __init__(self, name, base_class, fields, metaclass):
        Base.__init__(self, metaclass, fields)
        self.name = name
        self.base_class = base_class

    def method_resolution_order(self):
        """计算类的方法解析顺序"""
        if self.base_class is None:
            return [self]
        else:
            return [self] + self.base_class.method_resolution_order()

    def issubclass(self, cls):
        """是否是cls的子类"""
        return cls in self.method_resolution_order()

    def _read_from_class(self, methname):
        for cls in self.method_resolution_order():
            if methname in cls._fields:
                return  cls._fields[methname]
        return MISSING

# 像在Python（ObjVLisp模型）中那样设置基本层次结构
# 最终的基类是OBJECT
OBJECT = Class(name="object", base_class=None, fields={}, metaclass=None)
# TYPE 是 OBJECT 的子类
TYPE = Class(name="type", base_class=OBJECT, fields={}, metaclass=None)
# TYPE 是它自己的实例
TYPE.cls = TYPE
# OBJECT 是 TYPE 的实例
OBJECT.cls = TYPE


