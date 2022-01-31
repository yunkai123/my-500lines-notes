MISSING = object()

class Base(object):
    """所有对象模型类都要继承的基类"""

    def __init__(self, cls, fields):
        """每个对象都有一个类"""
        self.cls = cls
        self._fields = fields

    def read_attr(self, fieldname):
        """从对象中读取`filedname`字段"""
        result = self._read_dict(fieldname)
        if result is not MISSING:
            return result
        result = self.cls._read_from_class(fieldname)
        if _is_bindable(result):
            return _make_boundmethod(result, self)
        if result is not MISSING:
            return result
        meth = self.cls._read_from_class("__getattr__")
        if meth is not MISSING:
            return meth(self, fieldname)
        raise AttributeError(fieldname)

    def write_attr(self, fieldname, value):
        """将字段`fieldname`写入对象"""
        meth = self.cls._read_from_class("__setattr__")
        return meth(self, fieldname, value)

    def isinstance(self, cls):
        """如果对象是类的实例则返回True"""
        return self.cls.issubclass(cls)

    def callmethod(self, methname, *args):
        """在对象上使用参数 `args` 调用方法 `methname`"""
        meth = self.read_attr(methname)
        return meth(*args)

    def _read_dict(self, fieldname):
        """从对象字典中读取字段 `fieldname`"""
        return self._fields.get(fieldname, MISSING)

    def _write_dict(self, fieldname, value):
        """将一个字段 `fieldname` 写入到对象字典中"""
        self._fields[fieldname] = value

def _is_bindable(meth):
    return hasattr(meth, "__get__")

def _make_boundmethod(meth, self):
    return meth.__get__(self, None)

def OBJECT__setattr__(self, fieldname, value):
    self._write_dict(fieldname, value)

class Map(object):
    def __init__(self, attrs):
        self.attrs = attrs
        self.next_maps = {}

    def get_index(self, fieldname):
        return self.attrs.get(fieldname, -1)

    def next_map(self, fieldname):
        assert fieldname not in self.attrs
        if fieldname in self.next_maps:
            return self.next_maps[fieldname]
        attrs = self.attrs.copy()
        attrs[fieldname] = len(attrs)
        result = self.next_maps[fieldname] = Map(attrs)
        return result

EMPTY_MAP = Map({})

class Instance(Base):
    """用户定义类的实例"""

    def __init__(self, cls):
        assert isinstance(cls, Class)
        Base.__init__(self, cls, None)
        self.map = EMPTY_MAP
        self.storage = []

    def _read_dict(self, fieldname):
        index = self.map.get_index(fieldname)
        if index == -1:
            return MISSING
        return self.storage[index]

    def _write_dict(self, fieldname, value):
        index = self.map.get_index(fieldname)
        if index != -1:
            self.storage[index] = value
        else:
            new_map = self.map.next_map(fieldname)
            self.storage.append(value)
            self.map = new_map

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
OBJECT = Class(name="object", base_class=None, 
                fields={"__setattr__": OBJECT__setattr__},
                metaclass=None)
# TYPE 是 OBJECT 的子类
TYPE = Class(name="type", base_class=OBJECT, fields={}, metaclass=None)
# TYPE 是它自己的实例
TYPE.cls = TYPE
# OBJECT 是 TYPE 的实例
OBJECT.cls = TYPE


