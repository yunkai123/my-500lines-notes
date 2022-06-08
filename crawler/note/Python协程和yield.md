# Python 协程和 yield

参考文档 

https://www.jianshu.com/p/9dd355ab4e5d
https://www.cnblogs.com/gqtcgq/p/8126124.html
https://blog.csdn.net/soonfly/article/details/78361819

## yield

yield 英文意为产出、让步。对于 Python 生成器中的 `yield` 来说，这两个含义都成立。`yield` 语句会产出一个值，提供给 `next(...)` 的调用方；此外，还会作出让步，暂停执行生成器，让调用方继续工作，直到需要使用另一个值时再调用 `next()`。调用方会从生成器中拉取值。

### 先看个例子

先看一个例子：

```py
def add(alist):
    for i in alist:
        yield i + 1
```

在 `for` 循环中调用它：

```py
alist = [ 3, 4, 5, 6]
for n in add(alist):
    print(n)
```

可以看到打印结果：

```
4
5
6
7
```

### 生成器

假如某个函数中包含了 `yield`，这意味着这个函数已经是一个生成器（`Generator`），它的执行和普通的函数有很多不同。

比如下面的生成器示例：

```py
def h():
    print('study yield')
    yield 5
    print('go on')

h()
```

可以看到，调用 `h()` 之后，`print` 语句并没有执行！这就是`yield`。

### yield工作原理

yield是一个表达。

```py
m = yield 10
```

表达式(`yield 5`)的返回值将赋值给 `m`，所以，`m = 10` 肯定是错的。

那么如何获取 `yield 10` 的返回值呢？需要用到 `send(msg)`。

揭晓 `yield` 的工作原理，需要配合 `next()` 函数。上面的 `h()` 被调用后并没有执行，因为它有 `yield` 表达式，通过 `next()` 可以恢复生成器执行，直到下一个 `yield`。


```py
def h():
    print('study yield')
    yield 5
    print('go on')

a = h()
b = next(a)
print(b)
b = next(a)
print(b)
```
执行结果：

```
study yield
5
go on!
Traceback (most recent call last):
  File "d:\MyStudy\python\MyProject\code\test2.py", line 17, in <module>
    b = next(a)
StopIteration
```

`next()` 被调用后，`h()` 开始执行，直到遇到 `yield 5`，因此打印出：study yield。

当我们再次调用 `next()` 时，会继续执行，直到找到下一个 `yield`。由于后面没有 `yield` 了，因此会拋出异常。

### send(msg) 与 next()

`next()` 和 `send()` 在一定意义上作用是相似的。二者的区别是：`send()` 可以传递 `yield` 的值，`next()`只能传递 `None`。

所以 `next()` 和 `send(None)` 作用是一样的。

```py
def h():
    print('study yield')
    m = yield 5
    print(m)
    d = yield 10
    print(d)

a = h()
next(a)
b = a.send("hahaha")
```

执行结果为:

```
study yield
hahaha
```

**注意**: 生成器刚启动时(第一次调用)，请使用 `next()` 语句或是 `send(None)`，不能直接发送一个非 `None`的值，否则会报 `TypeError`，因为没有 `yield` 语句来接收这个值。

`send(msg)` 和 `next()` 的返回值是 `yield` 表达式的参数。

### 中断生成器

上面的例子中，当没有可执行程序的时候，会抛出一个StopIteration, 开发过程中，中断Generator是一个非常灵活的技巧

 - throw：通过抛出一个GeneratorExit异常来终止Generator。
 - close：close的作用和throw是一样的。


## 协程

使用 yield 关键字中的 `send(msg)`、`throw(...)`和`close()`等方法，即可以将生成器作为协程使用。


### 协程的基本行为

协程可以身处四个状态中的一个。

- GEN_CREATED：等待开始执行；

- GEN_RUNNING：解释器正在执行（只有在多线程应用中才能看到这个状态）；

- GEN_SUSPENDED：在 yield 表达式处暂停；

- GEN_CLOSED：执行结束。

当前状态可以使用 `inspect.getgeneratorstate(...)` 函数确定。

看个例子：

```py
from inspect import getgeneratorstate
def h(a):
    print("start: a = ", a)
    b = yield a
    print("received: b = ", b)
    c = yield a
    print("received: c = ", c)

m = h(14)
print(getgeneratorstate(m))
next(m)
print(getgeneratorstate(m))
```

结果为：

```
GEN_CREATED
start: a =  14
GEN_SUSPENDED
```

最先调用 `next(m)` 函数这一步通常称为“预激”（prime）协程（即，让协程向前执行到第一个 `yield` 表达式，准备好作为活跃的协程使用）。


关键的一点是，协程在 `yield` 关键字所在的位置暂停执行。在赋值语句中，`=` 右边的代码在赋值之前执行。因此，对于 `b = yield a` 这行代码来说，等到客户端代码再激活协程时才会设定 `b` 的值。

在看一个计算移动平均值的协程的例子：

```py
def averager():
    total = 0.0
    count = 0
    average = None
    while True:
        term = yield average
        total += term
        count += 1
        average = total/count

m = averager()
next(m) # 激活
print(m.send(10))
print(m.send(20))
print(m.send(40))
```

结果为：

```
10.0
15.0
23.333333333333332
```

这个无限循环表明，只要调用方不断把值发给这个协程，它就会一直接收值，然后生成结果。仅当调用方在协程上调用 `close()` 方法，或者没有对协程的引用而被垃圾回收程序回收时，这个协程才会终止。

### 预激协程的装饰器

如果不预激，那么协程没什么用。为了简化协程的用法，有时会使用一个预激装饰器。下面就是一个预激装饰器的例子：

```py
from functools import wraps

def coroutine(func):
    @wraps(func)
    def primer(*args,**kwargs):
        gen = func(*args,**kwargs)
        next(gen)
        return gen
    return primer 

@coroutine
def averager2():
    total = 0.0
    count = 0
    average = None
    while True:
        term = yield average
        total += term
        count += 1
        average = total/count 
```

注意，使用 yield from 语法调用协程时，会自动预激。

## yield from

yield from 是 Python3.3 后新加的语言结构。在生成器 `gen` 中使用 `yield from subgen()` 时，`subgen` 会获得控制权，把产出的值传给 `gen` 的调用方，即调用方可以直接控制 `subgen`。与此同时，`gen` 会阻塞，等待 `subgen` 终止。

yield from 可用于简化 for 循环中的 yield 表达式。例如下面两个函数的效果是一样的。

```py
def h1():
    for c in 'AB':
        yield c
    for i in range(1, 3):
        yield i

def h2():
    yield from 'AB'
    yield from range(1, 3)
```

`yield from iterable` 本质上等于 `for item in iterable: yield item`。

EP 380 使用了一些 `yield from` 使用的专门术语：

- 委派生成器：包含 `yield from <iterable>` 表达式的生成器函数；

- 子生成器：从 `yield from` 表达式中 `<iterable>` 部分获取的生成器；

- 调用方：调用委派生成器的客户端代码。

在 Python3.5 中引入 `async` 和 `await`， 作为 `asyncio.coroutine/yield from` 的完美替身。当然，从 Python 设计的角度来说，`async`/`await` 让协程表面上独立于生成器而存在，将细节都隐藏于`asyncio` 模块之下，语法更清晰明了。
