# 简单对象模型

## 作者

Carl Friedrich Bolz。Carl Friedrich Bolz是伦敦国王学院的研究员，对各种动态语言的实现和优化非常感兴趣。他是pypyy/RPython的核心作者之一，曾致力于Prolog、Racket、Smalltalk、PHP 和 Ruby 的实现。他的 Twitter 是 @cfbolz。

## 引言

面向对象编程是现在使用的主要编程范式之一，许多编程语言对面向对象提供了支持。虽然表面上看，不同的面向对象编程语言提供的机制非常相似，但细节可能会大相径庭。大多数语言的共同点是拥有对象和继承机制。然而，类不是每种语言都支持的特性。例如，在 Self 或 JavaScript 等基于原型的语言中，类的概念并不存在，对象直接从彼此继承。

了解不同对象模型之间的差异是一件很有趣的事情。它们常常揭示不同语言之间的相似性。将一种新语言的模型放到其他语言模型的上下文中，既能快速理解新模型，又能感受到编程语言的设计空间。

本文探讨了一系列非常简单的对象模型的实现。我们将从简单的实例和类以及在实例上调用方法的能力开始。这是早期 OO 语言（如 Simula 67 和 Smalltalk）中建立的经典面向对象范例。然后逐步扩展这个模型，接下来的两个小节探索不同语言的设计思路，最后一小节讲解如何提高对象模型的效率。我们最终的模型不是任何一门真实语言的模型，而是简化的 Python 对象模型。

本文介绍的对象模型将用 Python 实现。这些代码可以在 Python2.7 和 3.4 上运行。为了更好地理解对象模型的行为和设计，本文还将介绍对象模型的测试。测试代码可以使用 py.test 或者 nose 运行。

现实中很少选择 Python 作为实现语言。一个“真实”的 VM 通常以 C/C++ 等底层语言实现并且需要重视工程细节以提高效率。然而，选择简单的实现语言可以让我们更容易关注实际的行为差异，而不是过分注重细节。

## 基于方法的模型

我们将首先介绍的对象模型是 Smalltalk 的一个极简化的版本。Smalltalk 是 20 世纪 70 年代由 Xerox PARC 的 Alan Kay 小组设计的一种面向对象编程语言，它普及了面向对象编程，是当今编程语言中许多特性的来源。Smalltalk 语言的设计宗旨之一就是“万物皆对象”。如今，和 Smalltalk 最接近的继承者是 Ruby，它的语法更像 C 语言，但保留了 Smalltalk 的大部分对象模型。

本节中的对象模型将具有类和实例，能够将属性读写到对象中，能够调用对象上的方法，能够使一个类成为另一个类的子类。一开始，类将是完全普通的对象，它们本身可以具有属性和方法。

注释：在本文中，我将使用“实例”一词来表示“一个对象（而不是类）”。

一个好的方法是编写一个测试来指定要实现的行为应该是什么。本文中介绍的所有测试将由两部分组成。首先，一些常规 Python 代码使用 Python 对象模型高级特性定义了一些类。然后，使用我们将在本章中实现的对象模型而不是普通的 Python 类进行相应的测试。

使用普通 Python 类和使用我们的对象模型之间的映射将在测试中手动完成。例如，在Python中使用 `obj.attribute`，在我们的对象模型中，我们将使用方法 `obj.read_attr("attribute")`。在实际的语言实现中，这种映射将由语言的解释器或编译器完成。

本文中的进一步简化是，我们没有对实现对象模型的代码和用于编写对象中使用的方法的代码进行明显区分。在实际的系统中，这两部分通常是用不同的编程语言实现的。

让我们从读写对象字段的简单测试开始。

```py
def test_read_write_field():
    # Python 代码
    class A(object):
        pass
    obj = A()
    obj.a = 1
    assert obj.a == 1

    obj.b = 5
    assert obj.a == 1
    assert obj.b == 5

    obj.a = 2
    assert obj.a == 2
    assert obj.b == 5

    # Object model
    A = Class(name='A', base_class='OBJECT', fields={}, metaclass=TYPE)
    obj = Instance(A)
    obj.write_attr("a", 1)
    assert obj.read_attr("a") == 1

    obj.write_attr("b", 5)
    assert obj.read_attr("a") == 1
    assert obj.read_attr("b") == 5

    obj.write_attr("a", 2)
    assert obj.read_attr("a") == 2
    assert obj.read_attr("b") == 5
```

该测试使用了我们必须实现的三个东西。类 `Class` 和 `Instance` 分别表示对象模型的类和实例。类有两个特殊的实例：`OBJECT` 和 `TYPE`。`OBJECT` 对应于 Python 中的 `object`，是继承层次结构的最终基类。`TYPE` 对应于 Python 中的 `type`，是类的类型。

为了对 `Class` 和 `Instance` 的实例执行操作，它们通过从实现了一系列方法的共享基类 `Base` 中继承来实现共享接口：

```py
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

MISSING = object()
```

`Base` 类实现对象类的存储，并使用一个字典保存对象字段的值。现在我们需要实现 `Class` 和 `Instance`。`Instance` 的构造函数将类实例化，并将`fields` 和 `dict` 初始化为空字典。也就是说，`Instance` 只是一个围绕 `Base` 的简单子类，不添加任何额外的功能。

`Class` 的构造函数接受的参数为类的名称、基类、类的字典和元类。对于类，字段由对象模型的使用者传递到构造函数中。类构造函数还接受一个基类，到目前为止，测试不需要它，但我们将在下一节中使用它。

```py
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
```

因为类也是一种对象，所以它们（间接地）从 `Base` 继承。因此，类需要是另一个类的实例：它的元类。

现在我们的第一个测试快通过了。唯一缺少的是基类 `TYPE` 和 `OBJECT` 的定义，它们都是 `Class` 的实例。对于这些，我们将不使用 Smalltalk 模型，它的元类系统太复杂。相反，我们将使用在ObjVlisp[^ObjVlisp]中引入的模型，Python采用了这个模型。

[^ObjVlisp]: P. Cointe, “Metaclasses are first class: The ObjVlisp Model,” SIGPLAN Not, vol. 22, no. 12, pp. 156–162, 1987。

在 ObjVlisp 模型中，`OBJECT` 和 `TYPE` 是紧密相连的。`OBJECT` 是所有类的基类，这意味着它没有基类。`TYPE` 是 `OBJECT` 的子类。默认情况下，每个类都是 `TYPE` 的实例。特别是，`TYPE` 和 `OBJECT` 都是 `TYPE` 的实例。但是，程序员也可以集成 `TYPE` 以生成新的元类：

```py
# 像在Python（ObjVLisp模型）中那样设置基本层次结构
# 最终的基类是OBJECT
OBJECT = Class(name="object", base_class=None, fields={}, metaclass=None)
# TYPE 是 OBJECT 的子类
TYPE = Class(name="type", base_class=OBJECT, fields={}, metaclass=None)
# TYPE 是它自己的实例
TYPE.cls = TYPE
# OBJECT 是 TYPE 的实例
OBJECT.cls = TYPE
```

要定义新的元类，只需继承 `TYPE` 就足够了。但是，在本文的其余部分中，我们不会这样做；我们将始终使用 `TYPE` 作为每个类的元类。

![](/objmodel/markdown/img/inheritance.png)

现在第一个测试通过了。第二个测试校验读写属性对类也有效。写起来很容易，很快就通过了测试。

```py
def test_read_write_field_class():
    # class 也是对象
    # Python 代码
    class A(object):
        pass
    A.a = 1
    assert A.a == 1
    A.a = 6
    assert A.a == 6

    A = Class(name='A', base_class=OBJECT, fields={"a": 1}, metaclass=TYPE)
    assert A.read_attr("a") == 1
    A.write_attr("a", 5)
    assert A.read_attr("a") == 5
```

### isinstance 校验

到目前为止，我们还没有利用对象有类这一事实。下一个测试将测试 `isinstance`：

```py
def test_isinstance():
    # Python 代码
    class A(object):
        pass
    class B(A):
        pass
    b = B()
    assert isinstance(b, B)
    assert isinstance(b, A)
    assert isinstance(b, object)
    assert not isinstance(b, type)

    # Object model 代码
    A = Class(name="A", base_class=OBJECT, fields={}, metaclass=TYPE)
    B = Class(name="B", base_class=A, fields={}, metaclass=TYPE)
    b = Instance(B)
    assert b.isinstance(B)
    assert b.isinstance(A)
    assert b.isinstance(OBJECT)
    assert not b.isinstance(TYPE)
```

要检查对象 `obj` 是否是某个类 `cls` 的实例，只需检查 `cls` 是 `obj` 类的超类还是类本身就足够了。要检查一个类是否是另一个类的超类，需要遍历该类的超类链。当且仅当另一个类在这个链中被找到时，它就是一个超类。类的超类链（包括类本身）称为该类的“方法解析顺序”。它可以很容易地递归计算：

```py
class Class(Base):
    ...

    def method_resolution_order(self):
        """计算类的方法解析顺序"""
        if self.base_class is None:
            return [self]
        else:
            return [self] + self.base_class.method_resolution_order()

    def issubclass(self, cls):
        """是否是cls的子类"""
        return cls in self.method_resolution_order()
```

还用这段代码，测试就可以通过。

### 调用方法

这个对象模型的初始版本还缺少调用对象方法的能力。在本部分，我们将实现一个简单的单继承模型。

```py
def test_callmethod_simple():
    # Python code
    class A(object):
        def f(self):
            return self.x + 1
    obj = A()
    obj.x = 1
    assert obj.f() == 2

    class B(A):
        pass
    obj = B()
    obj.x = 1
    assert obj.f() == 2 # works on subclass too

    # Object model code
    def f_A(self):
        return self.read_attr("x") + 1
    A = Class(name="A", base_class=OBJECT, fields={"f": f_A}, metaclass=TYPE)
    obj = Instance(A)
    obj.write_attr("x", 1)
    assert obj.callmethod("f") == 2

    B = Class(name="B", base_class=A, fields={}, metaclass=TYPE)
    obj = Instance(B)
    obj.write_attr("x", 2)
    assert obj.callmethod("f") == 3
```

为了找到传递给对象的方法的正确实现，我们遍历对象类的方法解析顺序。按方法解析顺序在其中一个类的字典中找到的第一个方法被调用：

```py
class Class(Base):
    ...

    def _read_from_class(self, methname):
        for cls in self.method_resolution_order():
            if methname in cls._fields:
                return cls._fields[methname]
        return MISSING
```

与 `Base` 实现的 `callmethod` 代码放到一起，就可以通过测试。

为了确保带参数的方法也能正常工作，并且重写的方法可以被正确执行，我们可以使用下面稍微复杂一点的测试，它已经通过测试：

```py
def test_callmethod_subclassing_and_arguments():
    # Python code
    class A(object):
        def g(self, arg):
            return self.x + arg
    obj = A()
    obj.x = 1
    assert obj.g(4) == 5

    class B(A):
        def g(self, arg):
            return self.x + arg * 2
    obj = B()
    obj.x = 4
    assert obj.g(4) == 12

    # Object model code
    def g_A(self, arg):
        return self.read_attr("x") + arg
    A = Class(name="A", base_class=OBJECT, fields={"g": g_A}, metaclass=TYPE)
    obj = Instance(A)
    obj.write_attr("x", 1)
    assert obj.callmethod("g", 4) == 5

    def g_B(self, arg):
        return self.read_attr("x") + arg * 2
    B = Class(name="B", base_class=A, fields={"g": g_B}, metaclass=TYPE)
    obj = Instance(B)
    obj.write_attr("x", 4)
    assert obj.callmethod("g", 4) == 12
```

## 基于属性的模型

现在我们的对象模型的最简单版本已经可以工作了，我们可以对它进行修改。本节将介绍基于方法的模型和基于属性的模型之间的区别。这是 Smalltalk、Ruby 和 JavaScript 3种语言与 Python、Lua 这2种语言之间的核心区别之一。

基于方法的模型将方法调用作为程序执行的基本方式：

```py
result = obj.f(arg1, arg2)
```

基于属性的模型将方法调用分为两个步骤：查找属性和调用结果：

```py
method = obj.f
result = method(arg1, arg2)
```

二者的不同可以在下面的测试中显示：

```py
def test_bound_method():
    # Python code
    class A(object):
        def f(self, a):
            return self.x + a + 1
    obj = A()
    obj.x = 2
    m = obj.f
    assert m(4) == 7

    class B(A):
        pass
    obj = B()
    obj.x = 1
    m = obj.f
    assert m(10) == 12 # works on subclass too

    # Object model code
    def f_A(self, a):
        return self.read_attr("x") + a + 1
    A = Class(name="A", base_class=OBJECT, fields={"f": f_A}, metaclass=TYPE)
    obj = Instance(A)
    obj.write_attr("x", 2)
    m = obj.read_attr("f")
    assert m(4) == 7

    B = Class(name="B", base_class=A, fields={}, metaclass=TYPE)
    obj = Instance(B)
    obj.write_attr("x", 1)
    m = obj.read_attr("f")
    assert m(10) == 12
```

虽然与方法调用的测试设置部分相同，但方法被调用的方式不同。首先，在对象上查找具有方法名称的属性。这个查找操作的结果是一个*绑定方法*，一个既封装对象又封装类中的函数的对象。接下来，使用调用操作[^attributenote]调用绑定方法。

[^attributenote]:似乎基于属性的模型在概念上更复杂，因为它需要方法查找和调用。在实践中，调用是通过查找并调用一个特殊的属性 `__call__` 来定义的，因此概念的简单性得以恢复。不过，这一点在本文中不会实现。）

为了实现这种行为，我们需要改变 `Base.read_attr` 实现。如果在字典中找不到属性，则在类中查找它。如果在类中找到它，并且属性是可调用的，则需要将其转换为绑定方法。为了模拟绑定方法，我们只需使用闭包。除了改变 `Base.read_attr` 我们也可以改变 `Base.callmethod` 使用新方法调用方法以确保所有测试仍然通过。

```py
class Base(object):
    ...
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
        raise AttributeError(fieldname)

    def callmethod(self, methname, *args):
        """在对象上使用参数 `args` 调用方法 `methname`"""
        meth = self.cls._read_from_class(methname)
        return meth(self, *args)

def _is_bindable(meth):
    return callable(meth)

def _make_boundmethod(meth, self):
    def bound(*args):
        return meth(self, *args)
    return bound
```

其余的代码不需要再做更改。

## 元对象(Meta-Object )协议

除了由程序直接调用的常规方法外，许多动态语言还支持特殊方法。这些方法不是直接调用而是通过对象系统调用。在 Python 中，这些特殊方法的名称通常以两个下划线开头和结尾；例如 `__init__`。这些特殊的方法可以重写基元操作并提供自定义行为。因此，它们是告诉对象模型机器如何做某些事情的钩子。Python 的对象模型有许多特殊的方法。

元对象协议由 Smalltalk 引入，但在通用 Lisp 的对象系统（如CLOS）中使用得更多。这也是元对象协议（meta-object protocol），特殊方法的集合，这个名字的由来[^kiczales]。

[^kiczales]: G. Kiczales, J. des Rivieres, D. G. Bobrow, The Art of the Metaobject Protocol. Cambridge, Mass: The MIT Press, 1991。

在本文中，我们将向对象模型添加三个这样的元钩子。 它们用于微调读取和写入属性时发生的确切情况。我们将首先添加的特殊方法是 `__getattr__` 和 `__setattr__`，它们和Python的同名方法行为相似。

### 自定义读写和属性

当通过常规方式找不到正在查找的属性时，即属性既不在实例上，也不在类上，对象模型将调用`__getattr__`方法 。 它将被查找属性的名称作为参数。和 `__getattr__` 特殊方法类似的是早期 Smalltalk[^smalltalk] 系统名称为 `dosNotUnderstand:` 的一部分。

[^smalltalk]: A. Goldberg, Smalltalk-80: The Language and its Implementation. Addison-Wesley, 1983, page 61。

`__setattr__` 的情况有些不同，由于设置属性总是会创建属性，因此设置属性时始终会调用 `__setattr__`。为了确保 `__setattr__` 方法始终存在，`OBJECT` 类定义了 `__setattr__`。该基本实现仅执行设置属性到目前为止所做的事情，即将属性写入对象的字典中。这使用户定义的 `__setattr__` 可以在某些情况下委派给 `OBJECT .__ setattr__`。

这两种特殊方法的测试如下：

```py
def test_getattr():
    # Python code
    class A(object):
        def __getattr__(self, name):
            if name == "fahrenheit":
                return self.celsius * 9. / 5. + 32
            raise AttributeError(name)

        def __setattr__(self, name, value):
            if name == "fahrenheit":
                self.celsius = (value - 32) * 5. / 9.
            else:
                # call the base implementation
                object.__setattr__(self, name, value)
    obj = A()
    obj.celsius = 30
    assert obj.fahrenheit == 86 # test __getattr__
    obj.celsius = 40
    assert obj.fahrenheit == 104

    obj.fahrenheit = 86 # test __setattr__
    assert obj.celsius == 30
    assert obj.fahrenheit == 86

    # Object model code
    def __getattr__(self, name):
        if name == "fahrenheit":
            return self.read_attr("celsius") * 9. / 5. + 32
        raise AttributeError(name)
    def __setattr__(self, name, value):
        if name == "fahrenheit":
            self.write_attr("celsius", (value - 32) * 5. / 9.)
        else:
            # call the base implementation
            OBJECT.read_attr("__setattr__")(self, name, value)

    A = Class(name="A", base_class=OBJECT,
              fields={"__getattr__": __getattr__, "__setattr__": __setattr__},
              metaclass=TYPE)
    obj = Instance(A)
    obj.write_attr("celsius", 30)
    assert obj.read_attr("fahrenheit") == 86 # test __getattr__
    obj.write_attr("celsius", 40)
    assert obj.read_attr("fahrenheit") == 104
    obj.write_attr("fahrenheit", 86) # test __setattr__
    assert obj.read_attr("celsius") == 30
    assert obj.read_attr("fahrenheit") == 86
```

要通过这些测试，需要更改 `Base.read_attr` 和 `Base.write_attr` 方法：

```py
class Base(object):
    ...

    def read_attr(self, fieldname):
        """ read field 'fieldname' out of the object """
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
        """ write field 'fieldname' into the object """
        meth = self.cls._read_from_class("__setattr__")
        return meth(self, fieldname, value)
```

更改读取属性的过程，使用字段名作为参数调用 `__getattr__` 方法，如果方法不存在引发一个错误。 请注意，仅在类上查找 `__getattr__`（以及Python中的所有特殊方法），而不是递归调用 `self.read_attr("__getattr__")`。 这是因为如果未在对象上定义`__getattr__`，则后者将导致 `read_attr` 无限递归。

属性的写入将完全延迟到 `__setattr__` 方法。要实现这一点，`OBJECT` 需要有一个调用默认行为的 `__setattr__` 方法，如下所示：

```py
def OBJECT__setattr__(self, fieldname, value):
    self._write_dict(fieldname, value)
OBJECT = Class("object", None, {"__setattr__": OBJECT__setattr__}, None)
```

`OBJECT__setattr__` 的行为类似于前面 `write_attr`的行为。 经过这些修改，新的测试通过了。

### 描述符协议

上面的测试提供了不同温标之间的自动转换，但写起来很麻烦，因为属性名需要在 `__getattr__` 和 `__setattr__`方法中显式检查。为了解决这个问题，在 Python 中引入了*描述符协议(descriptor protocol )*。

当在正在读取属性的对象上调用 `__getattr__` 和 `__setattr__` 时，描述符协议对从对象获取属性的结果调用一个特殊方法。它可以看作是将方法绑定到对象的泛化，实际上，将方法绑定到对象就是使用描述符协议完成的。除了绑定方法外，Python 中描述符协议最重要的使用场景是`staticmethod`、`classmethod` 和 `property` 的实现。

在本小节中，我们将介绍处理绑定对象的描述符协议的子集。这是通过使用特殊方法 `__get__` 完成的，并通过示例测试进行了最好的解释：

```py
def test_get():
    # Python code
    class FahrenheitGetter(object):
        def __get__(self, inst, cls):
            return inst.celsius * 9. / 5. + 32

    class A(object):
        fahrenheit = FahrenheitGetter()
    obj = A()
    obj.celsius = 30
    assert obj.fahrenheit == 86

    # Object model code
    class FahrenheitGetter(object):
        def __get__(self, inst, cls):
            return inst.read_attr("celsius") * 9. / 5. + 32

    A = Class(name="A", base_class=OBJECT,
              fields={"fahrenheit": FahrenheitGetter()},
              metaclass=TYPE)
    obj = Instance(A)
    obj.write_attr("celsius", 30)
    assert obj.read_attr("fahrenheit") == 86
```

在 `obj` 类中查找之后，在 `FahrenheitGetter` 实例上调用 `__get__` 方法。`__get__` 的参数是查找完成的实例[^secondarg]。

[^secondarg]:在 Python 中，第二个参数是找到该属性的类，不过我们在这里将忽略它。

实现这种行为很容易。我们只需更改 `_is_bindable` 和 `_make_boundmethod`：

```py
def _is_bindable(meth):
    return hasattr(meth, "__get__")

def _make_boundmethod(meth, self):
    return meth.__get__(self, None)
```

测试通过了。前面关于绑定方法的测试也仍然通过，因为 Python 的函数有一个返回绑定方法对象的 `__get__` 方法。

实际上，描述符协议要复杂得多。它还支持 `__set__` 在每个属性中重写设置属性的含义。另外，当前的实现方式也进行了简化。请注意，`_make_boundmethod` 在实现级别上调用方法 `__get__`，而不是使用 `meth.read_attr("__get__")`。 这是必需的，因为我们的对象模型借用了 Python 的函数和方法，而不是使用对象模型来表示它们。 一个更完整的对象模型将解决这个问题。

## 实例优化

对象模型的前三个变体与行为变化有关，在最后一节中，我们将研究一种没有任何行为影响的优化。这种优化称为*映射（maps）*，是 Self 编程语言[^self]在 VM 中首创。它仍然是最重要的对象模型优化之一：它在 PyPy 和所有现代 JavaScript VM 中都使用，例如 V8（这种优化称为隐藏类）。

[^self]: C. Chambers, D. Ungar, and E. Lee, “An efficient implementation of SELF, a dynamically-typed object-oriented language based on prototypes,” in OOPSLA, 1989, vol. 24。

优化从以下观察开始：在到目前为止实现的对象模型中，所有实例都使用一个完整的字典来存储它们的属性。字典是使用哈希映射实现的，它需要大量内存。此外，同一类实例的字典通常也具有相同的键。例如，给定一个类 `Point`，它所有实例字典的键都可能是“`x`”和“`y`”。

映射优化利用了这一事实。它有效地将每个实例的字典分为两部分。存储键（映射）的部分，可以在具有相同属性名称集的所有实例之间共享这些键。然后，实例仅将对共享映射的引用和属性值存储在列表中（列表中的内存比字典紧凑得多）。该映射将属性名称到索引的映射存储到该列表中。

对这种行为的简单测试如下：

```py
def test_maps():
    # white box test inspecting the implementation
    Point = Class(name="Point", base_class=OBJECT, fields={}, metaclass=TYPE)
    p1 = Instance(Point)
    p1.write_attr("x", 1)
    p1.write_attr("y", 2)
    assert p1.storage == [1, 2]
    assert p1.map.attrs == {"x": 0, "y": 1}

    p2 = Instance(Point)
    p2.write_attr("x", 5)
    p2.write_attr("y", 6)
    assert p1.map is p2.map
    assert p2.storage == [5, 6]

    p1.write_attr("x", -1)
    p1.write_attr("y", -2)
    assert p1.map is p2.map
    assert p1.storage == [-1, -2]

    p3 = Instance(Point)
    p3.write_attr("x", 100)
    p3.write_attr("z", -343)
    assert p3.map is not p1.map
    assert p3.map.attrs == {"x": 0, "z": 1}
```

注意，这是一个不同于我们以前写的测试风格。以前所有的测试都是通过公开的接口测试类的行为。该测试通过读取内部属性并将其与预定义值进行比较来检查实例类的实现细节。因此，这个测试可以称为白盒测试。

`p1` 映射的 `attrs` 属性将实例的布局描述为具有两个属性`"x"` 和 `"y"`，这两个属性存储在 `p1` 的`storage` 的0和1处。制作第二个实例 `p2` 并以相同顺序添加相同的属性将使它最终具有相同的映射。另一方面，如果添加了其他属性，则当然不能共享映射。

`Map` 类如下所示：

```py
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
```

Map类有两个方法，`get_index` 和 `next_map`。前者用于在对象的存储中查找属性名称的索引。后者将新属性添加到对象时使用。在这种情况下，对象需要使用 `next_map` 计算的另一个映射。 该方法使用 `next_maps` 字典来缓存已经创建的映射。这样，具有相同布局的对象最终也将使用相同的 `Map` 对象。

![](/objmodel/markdown/img/maptransition.png)

使用映射的 `Instance` 实现如下所示：

```py
class Instance(Base):
    """Instance of a user-defined class. """

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
```

类现在将 `None` 作为字段字典传递给 `Base`，因为`Instance` 将以另一种方式存储字典的内容。因此，它需要重写 `_read_dict` 和 `_write_dict` 方法。在实际的实现中，我们将重构 `Base`，使它不再负责存储字段字典，但是现在将实例存储为`None`，这已经足够了。

一个新创建的实例从使用 `EMPTY_MAP` 开始，它没有属性且存储为空。为了实现 `_read_dict`，实例的映射被要求提供属性名的索引。然后返回存储列表的相应条目。

写入字段字典有两种情况。一方面，可以更改现有属性的值。这可以通过简单地更改相应索引处的存储来完成。另一方面，如果该属性尚不存在，则需要使用 `next_map` 方法进行映射转换。新属性的值将附加到存储列表中。

该优化实现了什么？在存在许多具有相同布局的实例的常见情况下，它可以优化内存的使用。这不是一个通用的优化方法：创建具有完全不同属性集的实例的代码将比我们仅使用字典时具有更大的内存占用。

这是优化动态语言时的一个常见问题。通常不可能在所有情况下找到更快或使用更少内存的优化。在实践中，所选择的优化应用于语言的典型使用方式，同时可能会使使用极端动态特性的程序的行为变得更糟。

映射的另一个有趣的方面是，虽然在这里它们只针对内存使用进行优化，但是在使用实时（just-in-time，JIT）编译器的实际vm中，它们还可以提高程序的性能。为此，JIT使用映射将属性查找以固定偏移量编译到对象存储中的查找，从而完全消除所有字典查找[^lookups]。

[^lookups]:工作原理超出了本章的范围。我在几年前写的一篇论文中试图给出一个合理可读的解释。它使用的对象模型基本上是本章的一个变体：C. F. Bolz, A. Cuni, M. Fijałkowski, M. Leuschel, S. Pedroni, and A. Rigo, “Runtime feedback in a meta-tracing JIT for efficient dynamic languages,” in Proceedings of the 6th Workshop on Implementation, Compilation, Optimization of Object-Oriented Languages, Programs and Systems, New York, NY, USA, 2011, pp. 9:1–9:8。

## 潜在扩展

很容易扩展我们的对象模型，并用各种语言设计选项进行实验。以下是一些可能性：

- 最简单的事情就是添加更多的特殊方法。一些简单而有趣的添加的是 `__init__` `__getattribute__` 和 ` __set__`。

- 该模型可以很容易地扩展以支持多重继承。为此，每个类都会得到基类的列表。然后 `Class.method_resolution_order` 方法需要更改以支持查找方法。一个简单的方法决定顺序可以使用深度优先搜索以删除重复来进行计算。一个更复杂但更好的算法是 C3 算法，它在菱形多重继承层次的基础上增加了更好的处理能力，并拒绝了不敏感的继承模式。

- 一个更彻底的改变是转换到原型模型，这涉及到去除类和实例之间的区别。

## 结论

面向对象编程语言设计的一个核心是其对象模型的细节。编写小对象模型原型是一种简单有趣的方法，可以帮助我们更好地理解现有语言的内部工作方式，并深入了解面向对象语言的设计空间。使用对象模型是一种很好的方法，可以试验不同的语言设计思想，而不必担心语言实现中更枯燥的部分，例如解析和执行代码。

这样的对象模型在实践中也很有用，而不仅仅是作为实验的载体。它们可以嵌入到其他语言中并从其他语言中使用。这种方法的例子很常见：用C编写的 GObject 对象模型，在 GLib 和其他 Gnome 库中使用；或者 JavaScript 中的各种类系统实现。