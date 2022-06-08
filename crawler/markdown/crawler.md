# 使用异步IO协程的网络爬虫

参考中文翻译： https://linux.cn/article-8265-1.html

## 作者介绍

A. Jesse Jiryu Davis 和 Guido van Rossum。 

A. Jesse Jiryu Davis 是纽约 MongoDB 的工程师。他编写了异步 MongoDB Python 驱动程序 Motor，也是 MongoDB C 驱动程序的开发领袖和 PyMongo 团队成员。 他也为 asyncio 和 Tornado 做了贡献，他在 http://emptysqua.re 上写作。

Guido van Rossum 是主流编程语言 Python 的创造者，Python 社区称他为 BDFL （仁慈的终生大独裁者）——这是一个来自 Monty Python 短剧的称号。他的主页是 http://www.python.org/~guido/ 。

## 介绍

经典的计算机科学强调尽可能快地完成计算的高效算法。但是很多网络程序的时间并不是消耗在计算上，而是消耗在保持许多慢速或不经常发生的事件的连接上。这些程序暴露出一个新的挑战：如何高效的等待大量网络事件。一个现代的解决方案是使用异步 I/O。

本文我们将实现一个简单的网络爬虫。这个爬虫只是一个原型式的异步应用，因为它等待大量的响应而只做少量的计算。一次爬的网页越多，它就能越快的完成任务。如果它为每个动态的请求启动一个线程的话，随着并发请求数量的增加，它会在耗尽套接字之前，耗尽内存或者线程相关的资源。它通过使用异步 I/O 避免了这个问题。

我们将分三个阶段展示这个例子。首先，我们会实现一个事件循环并用这个事件循环和回调来勾画出一只网络爬虫。它很有效，但是把它扩展成更复杂的问题会导致无法管理的混乱代码。然后，我们会展示 Python 的协程不仅有效而且可扩展，我们将用 Python 的生成器函数实现一个简单的协程。在第三阶段，我们将使用 Python 标准库“asyncio”中功能完整的协程，并通过异步队列完成这个网络爬虫。

## 任务

网络爬虫寻找并下载一个网站上的所有网页，也许还会把它们存档，为它们建立索引。从根 URL 开始，它获取每个网页，解析出没有遇到过的链接加到队列中。当网页中不再包含未见过的链接并且队列为空时，它便停止运行。

我们可以通过同时下载大量的网页来加快这一过程。当爬虫发现新的链接，它使用一个单独的套接字并行的处理这个新链接，解析响应，添加新链接到队列。当并发很大时可能会导致性能下降，所以我们会限制并发的数量，将那些未处理的链接保留在队列中，直到当前进行的任务完成。

## 传统方式

怎么使一个爬虫并发？传统的做法是创建一个线程池，每个线程使用一个套接字在一段时间内负责一个网页的下载。比如，下载 xkcd.com 网站的一个网页：

```py
def fetch(url):
    sock = socket.socket()
    sock.connect(('xkcd.com', 80))
    request = 'GET {} HTTP/1.0\r\nHost: xkcd.com\r\n\r\n'.format(url)
    sock.send(request.encode('ascii'))
    response = b''
    chunk = sock.recv(4096)
    while chunk:
        response += chunk
        chunk = sock.recv(4096)
    
    # Page is now downloaded.
    links = parse_links(response)
    q.add(links)
```

套接字操作默认是阻塞的：当一个线程调用一个类似 `connect` 和 `recv` 方法时，它会阻塞，直到操作完成。（即使是 send 也能被阻塞，比如接收端在接收外发消息时缓慢而系统的外发数据缓存已经满了的情况下）因此，为了同一时间内下载多个网页，我们需要很多线程。一个复杂的应用会通过线程池保持空闲的线程来分摊创建线程的开销。同样的做法也适用于套接字，只不过使用的是连接池。

到目前为止，使用线程的成本是昂贵的，操作系统对一个进程、一个用户、一台机器能使用的线程数量做了不同的硬性限制。在作者 Jesse 的系统中，一个 Python 线程需要 50K 的内存，开启上万个线程就会失败。如果我们扩展到上万个并发套接字，那我们会在用完套接字之前先用完线程。每个线程的开销和系统的限制是这种方式的瓶颈所在。

在 Dan Kegel 那一篇很有影响力的文章“The C10K problem”中，它提出了多线程方式在 I/O 并发上的局限性。他在开始写道，*网络服务器到了要同时处理成千上万的客户的时代了，你不这样认为么？毕竟，现在网络规模很大了。* Kegel 在 1999 年创造出“C10K”这个术语。一万个连接在今天看来还是可接受的，但是问题依然存在，只不过规模不同，本质却没有变化。回到那时候，对于 C10K 问题，每个连接启一个线程是不切实际的。现在上限提高了几个数量级。确实，我们的玩具网络爬虫使用线程也可以工作的很好。但是对于有着千万级连接的大规模应用来说，限制依然存在：它会消耗掉所有线程，即使套接字还够用。那么我们该如何解决这个问题？

## 异步

异步 I/O 框架使用非阻塞套接字在单个线程中完成并发操作。在我们的异步爬虫中，我们在发起到服务器的连接前把套接字设为非阻塞：

```py
sock = socket.socket()
sock.setblocking(False)
try:
    sock.connect(('xkcd.com', 80))
except BlockingIOError:
    pass
```

对一个非阻塞套接字即使在正常工作调用 `connect` 方法也会立即抛出异常。这个异常复现了底层 C 语言函数令人厌烦的行为，它把 `errno` 设置为 `EINPROGRESS`，告诉你操作已经开始。

现在我们的爬虫需要一种知道连接何时建立的方法，这样它才能发送 HTTP 请求。我们可以简单地使用循环来重试：

```py
request = 'GET {} HTTP/1.0\r\nHost: xkcd.com\r\n\r\n'.format(url)
encoded = request.encode('ascii')

while True:
    try:
        sock.send(encoded)
        break  # Done.
    except OSError as e:
        pass

print('sent')
```

这种方法不仅消耗 CPU，也不能有效的等待多个套接字。在远古时代，BSD Unix 的解决方法是 `select`，这是一个 C 函数，它在一个或一组非阻塞套接字上等待事件发生。现在，互联网应用大量连接的需求，导致 `select` 被 `poll` 所代替，在 BSD 上的实现是 `kqueue`，在 Linux 上是 `epoll`。它们的 API 和 `select` 相似，但在大数量的连接中也能有较好的性能。

Python 3.4 的 `DefaultSelector` 会使用你系统上最好的 `select` 类函数。要注册一个网络 I/O 事件的提醒，我们会创建一个非阻塞套接字，并使用默认 `selector` 注册它。

```py
from selectors import DefaultSelector, EVENT_WRITE

selector = DefaultSelector()

sock = socket.socket()
sock.setblocking(False)
try:
    sock.connect(('xkcd.com', 80))
except BlockingIOError:
    pass

def connected():
    selector.unregister(sock.fileno())
    print('connected!')

selector.register(sock.fileno(), EVENT_WRITE, connected)
```

我们不理会这个伪造的错误，调用 `selector.register`，传递套接字文件描述符和一个表示我们想要监听什么事件的常量表达式。为了当连接建立时收到提醒，我们使用 `EVENT_WRITE`：它表示什么时候这个套接字可写。我们还传递了一个 Python 函数 `connected`，当对应事件发生时被调用。这样的函数被称为回调。

在一个循环中，`selector` 接收到 I/O 通知时我们处理它们。

```py
def loop():
    while True:
        events = selector.select()
        for event_key, event_mask in events:
            callback = event_key.data
            callback()
```

`connected` 回调函数被保存在 `event_key.data` 中，一旦这个非阻塞套接字建立连接，它就会被取出来执行。

不像我们前面那个不停的循环，这里的 `select` 调用会暂停，等待下一个 I/O 事件，接着执行等待这些事件的回调函数。没有完成的操作会保持挂起，直到进到下一个事件循环时执行。

到目前为止我们展现了什么？我们展示了如何开始一个 I/O 操作和当操作准备好时调用回调函数。异步框架，建立在非阻塞套接字和事件循环两个功能之上，可以在单线程中执行并发操作

我们这里达成了“并发”，但不是传统意义上的“并行”。也就是说，我们构建了一个可以进行重叠 I/O 的微型系统，它可以在其它操作还在进行的时候就开始一个新的操作。它实际上并没有利用多核来并行执行计算。这个系统是用于解决 I/O 密集 I/O-bound 问题的，而不是解决 CPU 密集 CPU-bound 问题的。[^14]

[^14]:Python 的全局解释器锁禁止在一个进程中以任何方式并行执行 Python 代码。在 Python 中并行化 CPU 密集的算法需要多个进程，或者将该代码移植为 C 语言并行版本。但是这是另外一个话题了。

所以，我们的事件循环在并发 I/O 上效率很高，因为它并不用为每个连接分配线程资源。但是在我们开始前，我们需要纠正一个常见的误解：异步比多线程*快*。通常并不是这样的，事实上，在 Python 中，在处理少量非常活跃的连接时，像我们这样的事件循环是慢于多线程的。在运行时环境中是没有全局解释器锁的，在同样的负载下线程会执行的更好。异步 I/O 真正适用于事件很少、有许多缓慢或睡眠的连接的应用程序。[^11]

[^11]:Jesse 在“什么是异步，它如何工作，什么时候该用它？(What Is Async, How Does It Work, And When Should I Use It?)”（在pyvideo.org 中你可以看到这篇文章）一文中指出了异步所适用和不适用的场景。Mike Bayer 在“异步 Python 和数据库”（地址为 http://techspot.zzzeek.org/2015/02/15/asynchronous-python-and-databases/ ）一文中比较了不同负载情况下异步 I/O 和多线程的不同。

## 使用回调编程

用我们刚刚建立的异步框架，怎么才能完成一个网络爬虫？即使是一个简单的网页下载程序也是很难写的。

首先，我们有一个尚未获取的 URL 集合，和一个已经解析过的 URL 集合。

```py
urls_todo = set(['/'])
seen_urls = set(['/'])
```

`seen_urls` 集合包括 `urls_todo` 和已经完成的 URL。两组都用根 URL “/” 初始化。

获取一个网页需要一系列的回调。在套接字连接建立时会触发 `connected` 回调，它向服务器发送一个 GET 请求。但是它要等待响应，所以它会注册另一个回调函数；当该回调被调用，如果它仍然不能读取到完整的请求，就会再一次注册回调，如此反复。

让我们把这些回调放在一个 `Fetcher` 对象中，它需要一个 URL，一个套接字，还需要一个地方保存返回的字节：

```py
class Fetcher:
    def __init__(self, url):
        self.response = b''  # Empty array of bytes.
        self.url = url
        self.sock = None
```

我们从 `Fetcher.fetch` 开始：

```py
    # Method on Fetcher class.
    def fetch(self):
        self.sock = socket.socket()
        self.sock.setblocking(False)
        try:
            self.sock.connect(('xkcd.com', 80))
        except BlockingIOError:
            pass
            
        # Register next callback.
        selector.register(self.sock.fileno(),
                          EVENT_WRITE,
                          self.connected)
```

`fetch` 方法从连接一个套接字开始。但是要注意这个方法在连接建立前就返回了。它必须将控制返回到事件循环中等待连接建立。为了理解为什么要这样做，假设我们程序的整体结构如下：

```py
# Begin fetching http://xkcd.com/353/
fetcher = Fetcher('/353/')
fetcher.fetch()

while True:
    events = selector.select()
    for event_key, event_mask in events:
        callback = event_key.data
        callback(event_key, event_mask)
```

当调用 `select` 函数后，所有的事件通知才会在事件循环中处理，所以 `fetch` 必须把控制权交给事件循环，这样我们的程序才能知道什么时候连接已建立，接着循环调用 `connected` 回调，它已经在上面的 `fetch` 方法中注册过。

这里是 `connected` 方法的实现：

```py
    # Method on Fetcher class.
    def connected(self, key, mask):
        print('connected!')
        selector.unregister(key.fd)
        request = 'GET {} HTTP/1.0\r\nHost: xkcd.com\r\n\r\n'.format(self.url)
        self.sock.send(request.encode('ascii'))
        
        # Register the next callback.
        selector.register(key.fd,
                          EVENT_READ,
                          self.read_response)
```

这个方法发送一个 GET 请求。一个真正的应用会检查 `send` 的返回值，以防所有的信息没能一次发送出去。但是我们的请求很小，应用也不复杂。它只是简单的调用 `send`，然后等待响应。当然，它必须注册另一个回调并把控制权交给事件循环。接下来也是最后一个回调函数 `read_response`，它处理服务器的响应：

```py
    # Method on Fetcher class.
    def read_response(self, key, mask):
        global stopped

        chunk = self.sock.recv(4096)  # 4k chunk size.
        if chunk:
            self.response += chunk
        else:
            selector.unregister(key.fd)  # Done reading.
            links = self.parse_links()
            
            # Python set-logic:
            for link in links.difference(seen_urls):
                urls_todo.add(link)
                Fetcher(link).fetch()  # <- New Fetcher.

            seen_urls.update(links)
            urls_todo.remove(self.url)
            if not urls_todo:
                stopped = True
```

这个回调在每次 `selector` 发现套接字可读时被调用，可读有两种情况：套接字接收到数据或它被关闭。

这个回调函数从套接字读取 4K 数据。如果不到 4k，那么有多少读多少。如果比 4K 多，`chunk` 中只包 4K 数据并且这个套接字保持可读，这样在事件循环的下一个周期，会再次回到这个回调函数。当响应完成时，服务器关闭这个套接字，`chunk` 为空。

这里没有展示 `parse_links` 方法，它返回一个 URL 集合。我们为每个新的 URL 启动一个 `fetcher`，没有并发上限。注意使用异步回调方式编程的一个好处：我们不需要为共享数据加锁，比如我们往 `seen_urls` 增加新链接时。这是一种非抢占式的多任务，它不会在我们代码中的任意一个地方被打断。

我们增加了一个全局变量 `stopped`，用它来控制这个循环：

```py
stopped = False

def loop():
    while not stopped:
        events = selector.select()
        for event_key, event_mask in events:
            callback = event_key.data
            callback()
```

一旦所有的网页被下载下来，`fetcher `停止这个全局事件循环，程序退出。

这个例子让异步编程的一个问题暴露了出来：意大利面式的混乱代码。我们需要某种方式来表达一系列的计算和 I/O 操作，并且能够调度多个这样的系列操作让它们并发的执行。但是，没有线程你不能把这一系列操作写在一个函数中：当函数开始一个 I/O 操作，它明确的把未来所需的状态保存下来，然后返回。你需要考虑如何写这个状态保存的代码。

让我们来解释下这到底是什么意思。先来看一下在线程中使用通常的阻塞套接字来获取一个网页时是多么简单。

```py
# Blocking version.
def fetch(url):
    sock = socket.socket()
    sock.connect(('xkcd.com', 80))
    request = 'GET {} HTTP/1.0\r\nHost: xkcd.com\r\n\r\n'.format(url)
    sock.send(request.encode('ascii'))
    response = b''
    chunk = sock.recv(4096)
    while chunk:
        response += chunk
        chunk = sock.recv(4096)
    
    # Page is now downloaded.
    links = parse_links(response)
    q.add(links)
```

在一个套接字操作和下一个操作之间这个函数到底记住了什么状态？它有一个套接字，一个 URL 和一个可增长的 `response`。运行在线程中的函数使用编程语言的基本功能来在栈中的局部变量保存这些临时状态。这样的函数也有一个“continuation”——它会在 I/O 结束后执行这些代码。运行时环境通过线程的指令指针来记住这个 continuation。你不必考虑怎么在 I/O 操作后恢复局部变量和这个 continuation，语言本身的特性帮你解决。

但是用一个基于回调的异步框架时，这些语言特性不再能提供帮助。当等待 I/O 操作时，一个函数必须明确的保存它的状态，因为它会在 I/O 操作完成之前返回并清除栈帧。在我们基于回调的例子中，我们把 `sock` 和 `response` 作为 `Fetcher` 实例 `self` 的属性来存储从而替代局部变量。它通过注册 `connected` 和 `read_response` 回调来保存 continuation 作为指令指针的替代。随着应用程序功能的增加，我们需要手动保存的回调的复杂性也会增加。如此繁复的记账式工作会让编码人员感到头痛。

更糟糕的是，当我们的回调函数在运行到链中的下一个回调之前抛出异常会发生什么？假设我们没有写好 `parse_links` 方法，它在解析 HTML 时抛出异常：

```
Traceback (most recent call last):
  File "loop-with-callbacks.py", line 111, in <module>
    loop()
  File "loop-with-callbacks.py", line 106, in loop
    callback(event_key, event_mask)
  File "loop-with-callbacks.py", line 51, in read_response
    links = self.parse_links()
  File "loop-with-callbacks.py", line 67, in parse_links
    raise Exception('parse error')
Exception: parse error
```

这个堆栈回溯只能显示出事件循环调用了一个回调。我们不知道是什么导致了这个错误。这条链的两边都被破坏：不知道从哪来也不知到哪去。这种丢失上下文的现象被称为“堆栈撕裂(stack ripping)”，经常会导致无法分析原因。它还会阻止我们为回调链设置异常处理，即那种用“try / except”块封装函数调用及其调用树。[^7]

[^7]:对于这个问题的更复杂的解决方案，参见 http://www.tornadoweb.org/en/stable/stack_context.html 。

所以，除了关于多线程和异步哪个更高效的长期争议之外，还有一个关于这两者之间的争论：谁更容易出错。如果在同步上出现错误，线程更容易受到数据竞争的影响，而回调因为"堆栈撕裂"问题而非常难于调试。

## 协程

我们前面承诺过，我们可以写出既有回调方式的高效，也有多线程代码的简洁的异步代码。这个结合是通过一种称为“协程（coroutine）”的模式来实现的。使用 Python3.4 标准库 `asyncio` 和 `aiohttp` 包，在协程中可以直接获取一个网页[^10]:

[^10]:`@asyncio.coroutine` 修饰符并非魔法方法。事实上，如果它修饰的是一个生成器函数，并且没有设置 PYTHONASYNCIODEBUG 环境变量的话，这个修饰符基本上没啥用。它只是为了框架的其它部分方便，设置了一个属性 `_is_coroutine` 而已。也可以直接使用 `asyncio` 和裸生成器，而不使用 `@asyncio.coroutine` 修饰符。

```py
    @asyncio.coroutine
    def fetch(self, url):
        response = yield from self.session.get(url)
        body = yield from response.read()
```

它也是可扩展的。与每个线程 50k 内存和操作系统对线程的严格限制相比，一个 Python 协程在 Jesse 的系统中只需要 3k 内存。Python 可以轻松启动上千个协程。

协程的概念可以追溯到计算机科学早期，它很简单：一个可以暂停和恢复的子过程。线程是被操作系统控制的抢占式多任务，而协程协同执行多个任务，它们自己选择什么时候暂停以及下一步去执行哪个协程。

协程有很多实现，即使在 Python 中也有几种。Python 3.4 标准库 asyncio 中的协程是建立在生成器、 Future 类和“yield from”语句之上的。从 Python 3.5 开始，协程变成了语言本身的特性（“PEP 492 Coroutines with async and await syntax” 中描述了 Python 3.5 内置的协程）。然而，理解 Python 3.4 中这个通过语言原有功能实现的协程，是我们处理 Python 3.5 中原生协程的基础。

要解释 Python 3.4 中基于生成器的协程，我们需要深入了解生成器以及它们是如何在 `asyncio` 中用作协程的。我们解释了基于生成器的协程之后，就会在我们的异步网络爬虫中使用它们。

## Python 生成器如何工作

在理解生成器之前，你需要知道普通的 Python 函数是怎么工作的。通常，当一个函数调用一个子过程，这个被调用函数获得控制权，直到它返回或者有异常发生，才把控制权交给调用者：

```py
>>> def foo():
...     bar()
...
>>> def bar():
...     pass
```

标准的 Python 解释器是用 C 语言写的。一个 Python 函数被调用所对应的 C 函数是 `PyEval_EvalFrameEx`。它获得一个 Python 栈帧结构并在这个栈帧的上下文中执行 Python 字节码。这里是 `foo` 函数的字节码：

```py
>>> import dis
>>> dis.dis(foo)
  2           0 LOAD_GLOBAL              0 (bar)
              3 CALL_FUNCTION            0 (0 positional, 0 keyword pair)
              6 POP_TOP
              7 LOAD_CONST               0 (None)
             10 RETURN_VALUE
```

`foo` 函数在它的栈中加载 `bar` 函数并调用它，然后把 `bar` 的返回值从栈中弹出，加载 `None` 值到堆栈并返回。

当 `PyEval_EvalFrameEx` 遇到 `CALL_FUNCTION` 字节码时，它会创建一个新的栈帧，并用这个栈帧递归的调用 `PyEval_EvalFrameEx` 来执行 `bar` 函数。

非常重要的一点是，Python 的栈帧在堆内存中分配！Python 解释器是一个标准的 C 程序，所以它的栈帧是正常的栈帧。但是 Python 的栈帧是在堆中处理。这意味着 Python 栈帧在函数调用结束后依然可以存在。我们在 `bar` 函数中保存当前的栈帧，交互式的看看这种现象：

```py
>>> import inspect
>>> frame = None
>>> def foo():
...     bar()
...
>>> def bar():
...     global frame
...     frame = inspect.currentframe()
...
>>> foo()
>>> # The frame was executing the code for 'bar'.
>>> frame.f_code.co_name
'bar'
>>> # Its back pointer refers to the frame for 'foo'.
>>> caller_frame = frame.f_back
>>> caller_frame.f_code.co_name
'foo'
```

![](/crawler/markdown/img/function-calls.png)

现在该说 Python 生成器了，它使用同样构件——代码对象和栈帧——去完成一个不可思议的任务。

这是一个生成器函数：

```py
>>> def gen_fn():
...     result = yield 1
...     print('result of yield: {}'.format(result))
...     result2 = yield 2
...     print('result of 2nd yield: {}'.format(result2))
...     return 'done'
...     
```

在 Python 把 `gen_fn` 编译成字节码的过程中，一旦它看到 `yield` 语句就知道这是一个生成器函数而不是普通的函数。它就会设置一个标志来记住这个事实：

```py
>>> # The generator flag is bit position 5.
>>> generator_bit = 1 << 5
>>> bool(gen_fn.__code__.co_flags & generator_bit)
True
```

当你调用一个生成器函数，Python 看到这个标志，就不会实际运行它而是创建一个生成器：

```py
>>> gen = gen_fn()
>>> type(gen)
<class 'generator'>
```

Python 生成器封装了一个栈帧和函数体代码的引用：

```py
>>> gen.gi_code.co_name
'gen_fn'
```

所有来自对 `gen_fn` 调用的生成器指向同一段代码，但都有各自的栈帧。这些栈帧不在任何实际的栈中，而是在堆空间中等待被使用：

![](/crawler/markdown/img/generator.png)

栈帧中有一个指向“最后执行指令”的指针。初始化为 -1，意味着生成器没开始运行：

```py
>>> gen.gi_frame.f_lasti
-1
```

当我们调用 `send` 时，生成器一直运行到第一个 `yield` 语句处停止，并且 `send` 返回 1，这是 `gen` 传递给 `yield` 表达式的值。

```py
>>> gen.send(None)
1
```

现在，生成器的指令指针是 3，所编译的Python 字节码一共有 56 个字节：

```py
>>> gen.gi_frame.f_lasti
3
>>> len(gen.gi_code.co_code)
56
```

这个生成器可以在任何时候、任何函数中恢复运行，因为它的栈帧并不在真正的栈中，而是堆中。在调用链中它的位置也是不固定的，它不必遵循普通函数先进后出的顺序。它像云一样自由。

我们可以传递一个值 `hello` 给生成器，它会成为 `yield` 语句的结果，并且生成器会继续运行到第二个 `yield` 语句处。

```py
>>> gen.send('hello')
result of yield: hello
2
```

现在栈帧中包含局部变量 `result`：

```py
>>> gen.gi_frame.f_locals
{'result': 'hello'}
```

其它从 `gen_fn` 创建的生成器有着它自己的栈帧和局部变量。

当我们再一次调用 `send`，生成器继续从第二个 `yield` 开始运行，以抛出一个特殊的 `StopIteration` 异常为结束。

```py
>>> gen.send('goodbye')
result of 2nd yield: goodbye
Traceback (most recent call last):
  File "<input>", line 1, in <module>
StopIteration: done
```

这个异常有一个值 "done"，它就是生成器的返回值。

## 使用生成器构建协程

所以生成器可以暂停，可以给它一个值让它恢复，并且它还有一个返回值。这些特性看起来很适合去建立一个不使用那种乱糟糟的意面似的回调异步编程模型。我们想创造一个这样的“协程”：一个在程序中可以和其他过程合作调度的过程。我们的协程将会是标准库 `asyncio` 中协程的一个简化版本，和 `asyncio` 中一样，我们将使用生成器，future 和 “yield from” 语句。

首先，我们需要一种方法去代表协程所需要等待的 future 结果。一个精简版本是：

```py
class Future:
    def __init__(self):
        self.result = None
        self._callbacks = []

    def add_done_callback(self, fn):
        self._callbacks.append(fn)

    def set_result(self, result):
        self.result = result
        for fn in self._callbacks:
            fn(self)
```

一个 future 初始化为“未解决的”，它通过调用 `set_result` 来“解决”。[^12]

[^12]: 这个 future 缺少很多东西，比如说，当这个 future 解决后，生成 `yield` 的协程应该马上恢复而不是暂停，但是在我们的代码中却没有这样做。参见 asyncio 的 Future 类以了解其完整实现。

让我们用 future 和协程来改写我们的 fetcher。我们之前用回调写的 `fetch` 如下：

```py
class Fetcher:
    def fetch(self):
        self.sock = socket.socket()
        self.sock.setblocking(False)
        try:
            self.sock.connect(('xkcd.com', 80))
        except BlockingIOError:
            pass
        selector.register(self.sock.fileno(),
                          EVENT_WRITE,
                          self.connected)

    def connected(self, key, mask):
        print('connected!')
        # And so on....
```

`fetch` 方法开始连接一个套接字，然后注册 `connected` 回调函数，它会在套接字建立连接后调用。现在我们使用协程把这两步合并：

```py
    def fetch(self):
        sock = socket.socket()
        sock.setblocking(False)
        try:
            sock.connect(('xkcd.com', 80))
        except BlockingIOError:
            pass

        f = Future()

        def on_connected():
            f.set_result(None)

        selector.register(sock.fileno(),
                          EVENT_WRITE,
                          on_connected)
        yield f
        selector.unregister(sock.fileno())
        print('connected!')
```

现在，`fetch` 是一个生成器函数，而不是普通函数，因为它有一个 `yield` 语句。我们创建一个未解决的 future，然后 `yield` 它，暂停 `fetch` 直到套接字连接建立。内联函数 `on_connected` 解决这个 future。

但是当 future 被解决，谁来恢复这个生成器？我们需要一个协程驱动器。让我们称它为 “task”:

```py
class Task:
    def __init__(self, coro):
        self.coro = coro
        f = Future()
        f.set_result(None)
        self.step(f)

    def step(self, future):
        try:
            next_future = self.coro.send(future.result)
        except StopIteration:
            return

        next_future.add_done_callback(self.step)

# Begin fetching http://xkcd.com/353/
fetcher = Fetcher('/353/')
Task(fetcher.fetch())

loop()
```

task 通过传递一个 `None` 值给 `fetch` 来启动它。`fetch` 运行到它 yield 出一个 future，这个 future 被作为 `next_future` 而捕获。当套接字连接建立，事件循环运行回调函数 `on_connected`，这里 future 被解决，`step` 被调用，`fetch` 恢复运行。

## 用 `yield from` 重构协程

一旦套接字连接建立，我们就可以发送 HTTP GET 请求，然后读取服务器响应。不再需要哪些分散在各处的回调函数，我们把它们放在同一个生成器函数中：

```py
 def fetch(self):
        # ... connection logic from above, then:
        sock.send(request.encode('ascii'))

        while True:
            f = Future()

            def on_readable():
                f.set_result(sock.recv(4096))

            selector.register(sock.fileno(),
                              EVENT_READ,
                              on_readable)
            chunk = yield f
            selector.unregister(sock.fileno())
            if chunk:
                self.response += chunk
            else:
                # Done reading.
                break
```

从套接字中读取所有信息的代码看起来很通用。我们如何把它从 fetch 中提取成一个子过程？现在该 Python 3 热捧的 `yield from` 登场了。它能让一个生成器委派另一个生成器。

要了解如何操作，让我们先回到原来那个简单的生成器例子：

```py
>>> def gen_fn():
...     result = yield 1
...     print('result of yield: {}'.format(result))
...     result2 = yield 2
...     print('result of 2nd yield: {}'.format(result2))
...     return 'done'
...  
```

为了从其他生成器调用这个生成器，我们使用 `yield from` 委派它:

```py
>>> # Generator function:
>>> def caller_fn():
...     gen = gen_fn()
...     rv = yield from gen
...     print('return value of yield-from: {}'
...           .format(rv))
...
>>> # Make a generator from the
>>> # generator function.
>>> caller = caller_fn()
```

这个 `caller` 生成器的行为的和它委派的生成器 `gen` 表现的完全一致：

```py
>>> caller.send(None)
1
>>> caller.gi_frame.f_lasti
15
>>> caller.send('hello')
result of yield: hello
2
>>> caller.gi_frame.f_lasti  # Hasn't advanced.
15
>>> caller.send('goodbye')
result of 2nd yield: goodbye
return value of yield-from: done
Traceback (most recent call last):
  File "<input>", line 1, in <module>
StopIteration
```

当 `caller` 自 `gen` 生成（yield），`caller` 就不再前进。注意到 `caller` 的指令指针保持15不变，就是 `yield from` 的地方，即使内部的生成器 `gen` 从一个 `yield` 语句运行到下一个 `yield`，它始终不变。[^13] 从 `caller` 外部来看，我们无法分辨 yield 出的值是来自 `caller` 还是它委派的生成器。而从 `gen` 内部来看，我们也不能分辨传给它的值是来自 `caller` 还是 `caller` 的外面。`yield from` 语句是一个光滑的管道，值通过它进出 `gen`，一直到 `gen` 结束。

[^13]: 事实上，这就是“yield from”在 CPython 中工作的具体方式。函数会在执行每个语句之前提升其指令指针。但是在外部生成器执行“yield from”后，它会将其指令指针减一，以保持其固定在“yield form”语句上。然后其生成其 `caller`。这个循环不断重复，直到内部生成器抛出 `StopIteration`，这里指向外部生成器最终允许它自己进行到下一条指令的地方。）

协程可以用 `yield from` 把工作委派给子协程，并接收子协程的返回值。注意到上面的 `caller` 打印出“return value of yield-from: done”。当 `gen` 完成后，它的返回值成为 `caller` 中 `yield from` 语句的值。

```py
    rv = yield from gen
```

前面我们批评过基于回调的异步编程模式，其中最大的不满是关于 “堆栈撕裂”：当一个回调抛出异常，它的堆栈回溯通常是毫无用处的。它只显示出事件循环运行了它，而没有说为什么。那么协程怎么样？

```py
>>> def gen_fn():
...     raise Exception('my error')
>>> caller = caller_fn()
>>> caller.send(None)
Traceback (most recent call last):
  File "<input>", line 1, in <module>
  File "<input>", line 3, in caller_fn
  File "<input>", line 2, in gen_fn
Exception: my error
```

这还是非常有用的，当异常抛出时，堆栈回溯显示出 `caller_fn` 委派了 `gen_fn`。更令人欣慰的是，我们可以在一个异常处理器中封装这个调用到一个子过程中，像正常函数一样：

```py
>>> def gen_fn():
...     yield 1
...     raise Exception('uh oh')
...
>>> def caller_fn():
...     try:
...         yield from gen_fn()
...     except Exception as exc:
...         print('caught {}'.format(exc))
...
>>> caller = caller_fn()
>>> caller.send(None)
1
>>> caller.send('hello')
caught uh oh
```

所以我们可以像提取常规子过程一样提取子协程。让我们从 `fetcher` 中提取一些有用的子协程。我们先写一个可以读一块数据的协程 `read`：

```py
def read(sock):
    f = Future()

    def on_readable():
        f.set_result(sock.recv(4096))

    selector.register(sock.fileno(), EVENT_READ, on_readable)
    chunk = yield f  # Read one chunk.
    selector.unregister(sock.fileno())
    return chunk
```

在 read 的基础上创建 `read_all` 协程读取整个信息：

```py
def read_all(sock):
    response = []
    # Read whole response.
    chunk = yield from read(sock)
    while chunk:
        response.append(chunk)
        chunk = yield from read(sock)

    return b''.join(response)
```

如果你换个角度看，抛开 `yield form` 语句的话，它们就像在做阻塞 I/O 的普通函数一样。但是事实上，`read` 和 `read_all` 都是协程。`yield from read` 暂停 `read_all` 直到 I/O 操作完成。当 `read_all` 暂停时，`asyncio` 的事件循环正在做其它的工作并等待其他的 I/O 操作。`read` 在下次循环中当事件就绪，完成 I/O 操作时，`read_all` 恢复运行。

在栈的根部，`fetch` 调用了 `read_all`：

```py
class Fetcher:
    def fetch(self):
		 # ... connection logic from above, then:
        sock.send(request.encode('ascii'))
        self.response = yield from read_all(sock)
```

神奇的是，`Task` 类不需要做任何改变，它像以前一样驱动外部的 `fetch` 协程：

```py
Task(fetcher.fetch())
loop()
```

当 `read` yield 一个 future 时，`task` 从 yield from 管道中接收它，就像这个 future 直接从 fetch yield 一样。当循环解决一个 future 时，task 把它的结果送给 fetch，通过管道，read 接受到这个值，这完全就像 task 直接驱动 read 一样:

![](/crawler/markdown/img/yield-from.png)

为了完善我们的协程实现，我们再做点打磨：当等待一个 future 时，我们的代码使用 `yield`；而当委派一个子协程时，使用 `yield from`。不管是不是协程，我们总是使用 `yield from` 会更精炼一些。协程并不需要关心它在等待的东西是什么类型。

我们从在 Python 的生成器和迭代器的高度相似中获得了好处，对于调用者而言，使用生成器和迭代器可以同样获得好处。所以，我们可以通过特殊的实现方式来使我们的 Future 类迭代：

```py
    # Method on Future class.
    def __iter__(self):
        # Tell Task to resume me here.
        yield self
        return self.result
```

future 的 `__iter__` 方法是一个 yield 它自身的一个协程。当我们将代码替换如下时：

```py
# f is a Future.
yield f
```

以及：

```py
# f is a Future.
yield from f
```

结果是一样的！驱动 Task 从它的调用 `send` 中接收 future，并当 future 解决后，它发送新的结果给该协程。

在每个地方都使用 `yield from` 的好处是什么？为什么比用 `yield` 等待 future 并用 `yield from` 委派子协程更好？之所以更好的原因是，一个方法可以自由地改变其实现而不影响到其调用者：它可以是*解析*一个值并返回 future 的普通方法，也可以是包含 `yield from` 语句并返回一个值的协程。无论是哪种情况，调用者仅需要 `yield from` 该方法以等待结果就行。

亲爱的读者，我们已经完成了对 asyncio 协程探索。我们深入观察了生成器的机制，实现了简单的 future 和 task。我们概述了协程如何两全其美：比线程高效、比回调清晰的并发 I/O。当然真正的 asyncio 比我们这个简化版本要复杂的多。真正的框架需要解决零拷贝 I/0、公平调度、异常处理和其他大量特性。

使用 asyncio 编写协程代码比你现在看到的要简单的多。在前面的代码中，我们从基本原理去实现协程，所以你看到了回调，task 和 future，甚至非阻塞套接字和 `select` 调用。但是当用 asyncio 编写应用，这些都不会出现在你的代码中。像我们承诺的那样，你可以轻松下载一个网页：

```py
    @asyncio.coroutine
    def fetch(self, url):
        response = yield from self.session.get(url)
        body = yield from response.read()
```

经过令人满意的探索，我们回到最初的任务：使用 asyncio 编写一个网络爬虫。

## 配合工作的协程

我们首先描述了我们希望爬虫如何工作，现在是时候用异步 IO 的协程实现它了。

我们的爬虫会获取第一页，解析它的链接，并把它添加到队列中。在这之后它散布到整个网站并发地获取页面。为了限制客户端和服务器上的负载，我们希望设置 Worker 的最大数量。每当 Worker 完成获取页面时，都应立即从队列中拉出下一个链接。当没有足够多的页面需要爬取的时候，一些 Worker 就会停止。但是当一个 Worker 爬取了一个由足够多新链接的页面的时候，队列迅速增加，停止着的 Worker 都唤醒并开始工作。最后，我们的程序一旦完成工作就必须退出。

想象一下，如果 Worker 是线程，我们如何表达爬虫算法？哦我们可以使用 Python 标准库中的同步队列。每次将一项放入队列，队列增加它的“任务”的计数，Worker 线程没完成一项都会调用 `task_done`。主线程阻塞在 `Queue.join` 直到队列中的每一项都调用了 `task_done`，然后退出。

协程和异步 IO 队列使用了相同的模式！首先我们导入它：

```py
try:
    from asyncio import JoinableQueue as Queue
except ImportError:
    # In Python 3.5, asyncio.JoinableQueue is
    # merged into Queue.
    from asyncio import Queue
```

我们在爬虫类中收集 Worker 的共享状态，在它的 `crawl` 方法中编写主要逻辑。我们从一个协程开始爬取，运行异步 IO 事件直到爬取完成。

```py
loop = asyncio.get_event_loop()

crawler = crawling.Crawler('http://xkcd.com',
                           max_redirect=10)

loop.run_until_complete(crawler.crawl())
```

爬虫函数开始是有2个参数：根 URL 和表示获取 URL 时可以重定向的次数 `max_redirect`。它将 `(URL, max_redirect)` 对放到队列中（至于原因请关注后面）

```py
class Crawler:
    def __init__(self, root_url, max_redirect):
        self.max_tasks = 10
        self.max_redirect = max_redirect
        self.q = Queue()
        self.seen_urls = set()
        
        # aiohttp's ClientSession does connection pooling and
        # HTTP keep-alives for us.
        self.session = aiohttp.ClientSession(loop=loop)
        
        # Put (URL, max_redirect) in the queue.
        self.q.put((root_url, self.max_redirect))
```

现在队列中未完成的任务数是1，返回主脚本，我们启动事件循环和 crawl 方法：

```py
loop.run_until_complete(crawler.crawl())
```

爬虫协程让 Worker 开始工作，它像一个主线程：它会阻塞直到所有任务完成，而 Worker 运行在后台。

```py
    @asyncio.coroutine
    def crawl(self):
        """Run the crawler until all work is done."""
        workers = [asyncio.Task(self.work())
                   for _ in range(self.max_tasks)]

        # When all work is done, exit.
        yield from self.q.join()
        for w in workers:
            w.cancel()
```

如果 Worker 是线程，我们可能不希望立即启动它们。为了避免在确定线程是必须的之前创建昂贵的线程，线程池中的线程通常会按需增加。但是协程很便宜，因此我们只需要在开始时创建允许的最大数量即可。

我们如何关闭爬虫也值得关注。当挂起的future被解决后，Worker 任务处于活动状态但是已经暂停：他们等待更多的 URL 但是已经没有。因此主协程会在退出前将其取消。否则，当 Python 解释器关闭并调用所有对象的析构函数时，活动任务会报出异常：

```py
ERROR:asyncio:Task was destroyed but it is pending!
```

如何取消运作？生成器具有一个我们尚未展示的功能。你可以从外部将异常抛出到生成器中：

```py
>>> gen = gen_fn()
>>> gen.send(None)  # Start the generator as usual.
1
>>> gen.throw(Exception('error'))
Traceback (most recent call last):
  File "<input>", line 3, in <module>
  File "<input>", line 2, in gen_fn
Exception: error
```

生成器通过抛出异常来恢复，但是现在引发了异常。如果生成器的调用堆栈中没有代码捕获到该异常，则异常会冒泡到顶部。因此，要取消任务的协同程序：

```py
    # Method of Task class.
    def cancel(self):
        self.coro.throw(CancelledError)
```

无论生成器在哪个 `yield from` 语句暂停，它都会恢复并抛出一个异常，我们通过 task 的 `step` 方法处理取消：

```py
    # Method of Task class.
    def step(self, future):
        try:
            next_future = self.coro.send(future.result)
        except CancelledError:
            self.cancelled = True
            return
        except StopIteration:
            return

        next_future.add_done_callback(self.step)
```

现在任务已经直到它被取消，因此当它销毁时不会再抛出异常。

一旦爬虫取消了 Worker 程序，便会退出，事件循环看到协程完成（稍后展示如何发现）也会退出：

```py
loop.run_until_complete(crawler.crawl())
```

`crawl` 方法包含所有主协程要做的事情。Worker 协程负责从队列中获取 URL，根据 URL 抓取页面并解析他们获取新的链接。每个 Worker 独立运行工作协程：

```py
    @asyncio.coroutine
    def work(self):
        while True:
            url, max_redirect = yield from self.q.get()

            # Download page and add new links to self.q.
            yield from self.fetch(url, max_redirect)
            self.q.task_done()
```

Python 看到此代码包含 `yield from` 语句，并将其编译为生成器函数。因此在 `craw` 函数，当主协程调用 `self.work` 10次时，它就不再执行此方法：它仅创建十个生成器对象并对代码引用。它将每个都包装在 Task 中。Task 接收生成器 yield 的 future，并通过在 future 被解决时的结果上调用 `send` 驱动生成器。因为生成器有自己的栈帧，所以它们使用单独的局部变量和指令指针独立运行。

Worker 通过队列进行协调，它通过如下代码等待新 URL ：

```py
    url, max_redirect = yield from self.q.get()
```

队列的 get 方法本身就是一个协程，它暂停直到有程序将一个项放进队列，然后继续并返回这个项。

顺便说一句，这是工作者被主协程爬虫取消的时候暂停的地方。从协程的角度看，当 yield from 引发了 `CancelledError` 时它在循环中的最后行程就结束了。

当一个 Worker 抓取了页面后它解析其中的链接并将新链接放到队列，然后调用 `task_done` 来减少计数器。最终，Worker 抓取到的页面上的 URL 已经全部被抓取了，队列中也没有任何工作了。此时 Worker 对 `task_done` 的调用将计数器减为0。然后等待队列的 `join` 方法的 `crawl` 取消暂停并结束。

我们前面说过要解释为什么队列中的项是成对的，像：

```py
# URL to fetch, and the number of redirects left.
('http://xkcd.com/353', 10)
```

新的 URL 有10次重定向次数。提取此特定 URL 导致重定向到一个带有斜杠的新地址。我们减少剩余的重定向次数并将下一个地址放到队列：

```py
# URL with a trailing slash. Nine redirects left.
('http://xkcd.com/353/', 9)
```

默认情况下我们使用的 aiohttp 包会遵循重定向并提供最终的响应。但是我们让它不要处理爬虫中的重定向，因此它可以合并指向相同地址的重定向路径：如果我们已经见过此 URL，则它位于 `self.seen_urls` 中，并且我们已经从另一个入口点开始使用此路径：

![](/crawler/markdown/img/redirects.png)

爬虫抓取到“foo”然后发现它重定向到“baz”，所以它添加“baz”到队列和 seen_urls 中。如果它获取的下一个页面是“bar”，它也重定向到“baz”，那么获取程序不会再次将“baz”加到队列，如果响应式页面而不是重定向，则获取程序解析它获取链接并将新链接放到队列中。

```py
    @asyncio.coroutine
    def fetch(self, url, max_redirect):
        # Handle redirects ourselves.
        response = yield from self.session.get(
            url, allow_redirects=False)

        try:
            if is_redirect(response):
                if max_redirect > 0:
                    next_url = response.headers['location']
                    if next_url in self.seen_urls:
                        # We have been down this path before.
                        return
    
                    # Remember we have seen this URL.
                    self.seen_urls.add(next_url)
                    
                    # Follow the redirect. One less redirect remains.
                    self.q.put_nowait((next_url, max_redirect - 1))
    	     else:
    	         links = yield from self.parse_links(response)
    	         # Python set-logic:
    	         for link in links.difference(self.seen_urls):
                    self.q.put_nowait((link, self.max_redirect))
                self.seen_urls.update(links)
        finally:
            # Return connection to pool.
            yield from response.release()
```

如果这是多线程代码，则在竞争条件下会变得很糟糕。例如，Worker 程序检查链接是否在 `seen_urls` 中，如果不是，则将其放入队列并将其添加到`seen_urls`。 如果这个过程在两个操作之间被中断，则另一个 Worke r程序可能会从不同的页面解析相同的链接，观察到它不在 `seen_urls` 中，并将其添加到队列中。现在，同一链接在队列中出现两次，从而导致重复的工作和错误的统计信息。

然而，协程仅收到 `yield from` 语句的干扰。这是一个使协程代码比多线程代码更不容易出现竞争的关键区别：多线程代码必须通过获取锁来显式地进入关键部分，否则将被中断。 默认情况下，Python 协程是不可中断的，只有在显式使用 `yield` 时才让出控制权。

我们不再像基于回调的程序那样需要一个 fetcher 类。这个类是缺少回调的变通方法：在等待I/O时，它们需要一些地方来存储状态，因为它们的局部变量不会在调用之间保留。但是，获取协程可以像常规函数一样将其状态存储在局部变量中，因此不再需要这个类。

当 `fetch` 完成处理服务器响应后，它将返回到调用方并开始工作。`work` 方法在队列上调用 `task_done` 然后从队列上获取可以提取的下一个 URL。

当 `fetch` 将新链接放入队列时它会增加未完成任务的数量，并使等待 `q.join` 的主协程暂停。然而，如果已经没有未出现过的新链接并且它是队列中的最后一个 URL，则当 `work` 调用 `task_done` 时，未完成任务的数量将降至零。 该事件将使 `join` 方法继续并使主协程运行完成。

协调工作者和主协程的队列代码如下：

```py
class Queue:
    def __init__(self):
        self._join_future = Future()
        self._unfinished_tasks = 0
        # ... other initialization ...
    
    def put_nowait(self, item):
        self._unfinished_tasks += 1
        # ... store the item ...

    def task_done(self):
        self._unfinished_tasks -= 1
        if self._unfinished_tasks == 0:
            self._join_future.set_result(None)

    @asyncio.coroutine
    def join(self):
        if self._unfinished_tasks > 0:
            yield from self._join_future
```

主协程 `crawl` 从 `join` 方法 `yield from`。所以当最后一个 Worker 将未完成任务的计数降为零，它给 `crawl` 发送信号来恢复和结束。

文章快结束了，我们的程序从对 `crawl` 的调用开始：

```py
class EventLoop:
    def run_until_complete(self, coro):
        """Run until the coroutine is done."""
        task = Task(coro)
        task.add_done_callback(stop_callback)
        try:
            self.run_forever()
        except StopError:
            pass

class StopError(BaseException):
    """Raised to stop the event loop."""

def stop_callback(future):
    raise StopError
```

任务完成后，它会引发 `StopError` 异常，循环将其用作信号，代表它已到达正常完成状态。

但那是什么？task 有叫做 `add_done_callback` 的方法放到最后，你可能认为 task 类似 future，你的直觉是对的，我们展示前面隐藏的 `Task` 类的细节：任务 task 就是 future 。

```py
class Task(Future):
    """A coroutine wrapped in a Future."""
```

通常，future 可以通过其他方法调用 `set_result` 来解决。但是 task 会在协程结束的时候自行解决。从我们之前对 Python 生成器的探索中可以知道，当生成器返回时，它会抛出特殊的 `StopIteration` 异常：

```py
    # Method of class Task.
    def step(self, future):
        try:
            next_future = self.coro.send(future.result)
        except CancelledError:
            self.cancelled = True
            return
        except StopIteration as exc:

            # Task resolves itself with coro's return
            # value.
            self.set_result(exc.value)
            return

        next_future.add_done_callback(self.step)
```

因此，当事件循环调用 `task.add_done_callback(stop_callback)`时，它准备被 task 停止。下面是 `run_until_complete`：

```py
    # Method of event loop.
    def run_until_complete(self, coro):
        task = Task(coro)
        task.add_done_callback(stop_callback)
        try:
            self.run_forever()
        except StopError:
            pass
```

当 task 捕获 `StopIteration` 并自行解决时，回调从循环内引发`StopError`。循环停止，调用堆栈退回到 `run_until_complete`。 我们的程序结束了。

## 结论

现代程序越来越受到 I/O 的限制而不是 CPU。对于此类程序，Python 线程是最坏的选择：全局解释器锁阻止它们实际并行执行计算，而抢占式切换使它们易于出现竞争。异步通常是正确的模式。但是随着基于回调的异步代码的增长，它往往会变得混乱不堪。协程是一个整洁的选择。它们自然地包含在子程序中，并具有健全的异常处理和堆栈跟踪功能。

如果我们换个角度不考虑 `yield from` 语句的好处，一个协程看起来像执行传统阻塞 I/O 的线程。我们甚至可以让协程和多线程编程的经典模式协同工作。无需重新创造。相比回调，协程对于习惯使用多线程的程序员是个不错的选择。

但是当我们专注到 `yield from` 语句的好处时，我们看到协程进行了标记当它放弃控制并允许其它程序运行的时候。与线程不同，协程会显示我们的代码可以在何处中断、不可以在何处中断。Glyph Lefkowitz 在他的启发性的短文“ Unyielding”中写道，“线程使本地推理变得困难，而本地推理可能是软件开发中最重要的事情。”但是，yield 使“通过检查程序本身而不是整个系统来了解程序的行为”成为可能。

本章是在 Python 和异步技术的复兴中撰写的。你刚刚学会的基于生成器的协程，已于2014年3月在Python 3.4的“异步”模块中发布。2015年9月，包含语言本身内置的协程的 Python 3.5发布。这些原生协程以新语法“ async def”声明，而不是 “yield from”，它们使用新的 “await”关键字委派给协程或等待 Future。

尽管技术取得了进步，但核心思想仍然存在。Python的新本地协程在语法上与生成器不同，但工作方式非常相似。实际上，他们将在 Python 解释器中共享一个实现。Task、Future和事件循环将继续在异步中发挥作用。

既然你已经了解了异步协程的工作原理，就可以忘记其中的细节。机器都被放到精巧的接口后面。掌握了基础知识后就可以在现在异步环境中有效的进行编码。



