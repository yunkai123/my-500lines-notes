# 简易 Web 服务器

## 作者

Greg Wilson 是 Software Carpentry（一个为科学家和工程师开设的计算技能速成班）的创始人。他在工业界和学术界工作了 30 年，著有几本关于计算的书籍，包括 2008 年的 Jolt 奖得主《Beautiful Code》和《The Architecture of Open Source Applications》的前两卷。Greg 于 1993 年获得爱丁堡大学计算机科学博士学位。

## 引言

在过去的二十年里，网络以无数的方式改变了社会，但它的核心却几乎没有改变。大多数系统仍然遵循25年前 Tim Berners-Lee 制定的规则。特别是，大多数 web 服务器仍然以相同的方式处理着相同类型的消息。

本文将探讨它们是如何做到这一点的。同时，还将探讨开发人员如何添加新功能而不重写软件系统。

## 背景

网络上几乎每个程序都运行在一系列称为因特网协议（IP）的通信标准上。传输控制协议（TCP/IP）是这个家族中的一员，它使计算机之间的通信看起来就像读写文件一样。

使用 IP 的程序通过套接字进行通信。每个套接字都是点对点通信通道的一端，就像电话是电话通讯的一端一样。套接字由标识特定计算机的 IP 地址和该计算机上的端口号组成。IP 地址由四个8位数字组成，例如174.136.14.108；域名系统（DNS）将这些数字与符号名称匹配，如 aosabook.org 网站，这对人类来说更容易记住。

端口号是 0 - 65535 范围内的一个数字，它唯一地标识主机上的套接字。（如果 IP 地址比作公司的电话号码，则端口号类则类似分机号。）端口 0 - 1023 保留给操作系统使用；其余端口任何人都可以使用。

超文本传输协议（HTTP）描述了程序通过 IP 交换数据的一种方式。HTTP 设计的很简单：客户机通过套接字连接发送一个请求，指定它想要什么，服务器发送一些数据作为响应（如下图）。数据可以从磁盘上的文件复制，也可以由程序动态生成，或者两者混合。

![](/web-server/markdown/img/http-cycle.png)

关于 HTTP 请求最重要的是它只由文本组成：任何程序都可以对其创建或解析。但是，为了被正确解析，该文本必须包含下图所示的部分。

![](/web-server/markdown/img/http-request.png)

HTTP 方法大部分是 GET（获取信息）或 POST（提交表单数据或上传文件）。URL 指定客户端需要什么；它通常是指向磁盘上文件的路径，例如 /research/experiments.html，但是（这是关键部分）完全由服务器决定如何处理它。HTTP 版本通常是 HTTP/1.0 或 HTTP/1.1；两者之间的区别对我们来说并不重要。

HTTP 首部是键/值对，如下所示：

```
Accept: text/html
Accept-Language: en, fr
If-Modified-Since: 16-May-2005
```

与哈希表中的键不同，HTTP 首部中的键可以出现任意次数。这使请求更加的灵活，比如指定它愿意接受多种类型的内容。

最后，请求的主体是与请求相关联的任何数据，在通过 web 表单提交数据、上传文件等时使用。首部的末尾和正文开头之间必须有一个空白行，以指示首部的结尾。

首部中，`Content-Length` 告诉服务器请求主体中预期读取的字节数。

HTTP 响应的格式和 HTTP 请求类似：

![](/web-server/markdown/img/http-response.png)

版本、首部和主体具有相同的格式和含义。状态码是一个数字，表示在处理请求时发生了什么：200表示“一切正常”，404表示“未找到”，其他代码也有各自的含义。状态短语以易读的形式重复该信息，如“OK”或“not found”。

在本部分我们主要了解关于 HTTP 的另外两方面。

第一个是它是无状态的：每个请求都是独立处理的，服务器不记得两个请求之间的任何内容。如果应用程序想要跟踪用户的身份等信息，它必须自己实现。

通常的实现方法是使用 cookie，cookie 是服务器发送给客户端的一个短字符串，然后由客户端返回到服务器。当用户执行某个功能，需要在多个请求之间保存状态时，服务器会创建一个新的 cookie，将其存储在数据库中，并将其发送到浏览器。每次浏览器返回 cookie 时，服务器都会使用它来查找有关用户行为的信息。

第二方面是 URL 可以添加参数以提供更多的信息。例如，如果我们使用搜索引擎，我们必须指定我们的搜索词。我们可以将这些添加到 URL 的路径中，但是更加合适的方式是向 URL 添加参数。我们通过在 URL后面添加“?”和以“&”分隔的“key=value”对。例如，URL `http://www.google.ca?q=Python` 要求 Google 搜索与 Python 相关的页面：键是字母“q”，值是“Python”。较长的查询 `http://www.google.ca/search?q=Python&amp;client=Firefox` 告诉 Google 我们正在使用 Firefox，诸如此类。我们可以传递我们想要的任何参数，不过，使用哪些参数以及如何解释这些参数完全取决于运行在 Web 站点上的应用程序。

当然，如果“?”和“&”是特殊字符，必须有一种转义它们的方法，就像必须有一种方法将双引号字符放入由双引号分隔的字符串中一样。URL 编码标准使用“%”后跟2位代码表示特殊字符，并将空格替换为“+”字符。因此，要在 Google 上搜索“grade = A+”（带空格），我们要使用 URL `http://www.google.ca/search?q=grade+%3D+A%2B`。

打开套接字、构造 HTTP 请求和解析响应繁琐而无趣，因此大多数人使用库来完成大部分工作。Python 附带了一个名为 urllib2 的库（因为它是早期 urllib 库的替代品），但是它暴漏了许多大多数人不想关心的管道。Requests 库是 urllib2 更易于使用的替代选择。下面是一个使用它从 AOSA book 站点下载页面的示例：

```py
import requests
response = requests.get('http://aosabook.org/en/500L/web-server/testpage.html')
print 'status code:', response.status_code
print 'content length:', response.headers['content-length']
print response.text
status code: 200
content length: 61
<html>
  <body>
    <p>Test page.</p>
  </body>
</html>
```

`request.get` 向服务器发送 HTTP GET 请求，返回一个包含响应的对象。该对象的 `status_code` 是响应的状态码；`content_length` 是响应数据中的字节数，`text` 是实际数据（在本例中，它是一个 HTML 页面）。

## 你好，Web

我们现在准备编写第一个简单的 Web 服务器。基本思路很简单：

1. 等待用户连接到我们的服务器并发送过来一个 HTTP 请求；
2. 解析该请求；
3. 弄清楚它在请求什么；
4. 获取数据（或动态生成）；
5. 将数据格式化为 HTML；
6. 返回数据。

步骤1、2、6 在不同的应用程序中是相同的，因此 Python 标准库有一个名为 http.server 的模块，它为我们完成这些操作。我们只需完成步骤3-5，这是下面的小程序中要做的：

```py
import http.server

#-------------------------------------------------------------------------------

class RequestHandler(http.server.BaseHTTPRequestHandler):
    '''通过返回固定页面来处理HTTP请求'''

    # 返回页面
    Page = '''<html>\
    <body>
    <p>Hello, Web!</p>
    </body>
    </html>
    '''

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.send_header("Content-Length", str(len(self.Page)))
        self.end_headers()
        self.wfile.write(bytes(self.Page, 'utf-8'))

#-------------------------------------------------------------------------------

if __name__ == '__main__':
    serverAddress = ('', 8080)
    server = http.server.HTTPServer(serverAddress, RequestHandler)
    server.serve_forever()

```

库中的 `BaseHTTPRequestHandler` 类负责解析传入的 HTTP 请求并判断它包含什么方法。如果方法是 GET，则类将调用名为 `do_GET` 的方法。我们的类 `RequestHandler` 重写这个方法来动态生成一个简单的页面：文本存储在类级别的变量 `Page` 中，我们在发送给客户端 200 的响应码、首部 `Content-Type` 字段告诉客户端将我们的数据解释为 HTML，以及页面的长度后将其发送回客户端。（`end_headers` 方法调用插入空行以分隔首部和页面本身。）

然而 `RequestHandler` 并不是全部：我们仍然需要最后三行代码来真正启动服务器。第一行使用元组定义服务器的地址：空字符串表示“在当前主机上运行”，8080是端口。然后使用该地址和请求处理程序类的名称作为参数创建 `http.server.HTTPServer` 的实例，然后请求它一直运行（这意味着一直运行到我们用 Ctrl-C 杀死它为止）。

如果我们从命令行运行此程序，它不会显示任何内容：

```
$ python server.py
```

如果我们在浏览器中访问 http://localhost:8080 ，我们可以在浏览器中看到：

```
Hello, web!
```

同时在 shell 中看到：

```
127.0.0.1 - - [24/Feb/2014 10:26:28] "GET / HTTP/1.1" 200 -
127.0.0.1 - - [24/Feb/2014 10:26:28] "GET /favicon.ico HTTP/1.1" 200 -
```

第一行很简单：因为我们没有请求特定的文件，所以我们的浏览器输入“/”（服务器文件的根目录）。出现第二行是因为浏览器会自动发送第二个对名为 /favicon.ico 图像文件的请求，如果存在，它将在地址栏中显示为图标。

## 展示值

让我们修改 Web 服务器以展示 HTTP 请求中的值。（在调试时，我们会经常这样做，所以我们不妨进行一些练习。）为了保持代码的整洁，我们将把创建页面与发送页面分开：

```py
class RequestHandler(http.server.BaseHTTPRequestHandler):

    # ...page template...

    def do_GET(self):
        page = self.create_page()
        self.send_page(page)

    def create_page(self):
        # ...fill in...

    def send_page(self, page):
        # ...fill in...
```
`send_page` 比之前的内容多了很多:

```py
    def send_page(self, page):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.send_header("Content-Length", str(len(self.Page)))
        self.end_headers()
        self.wfile.write(bytes(self.Page, 'utf-8'))
```

我们要显示的页面模板只是一个字符串，其中包含一个带有一些格式占位符的HTML表格：

```py
    Page = '''\
    <html>
    <body>
    <table>
    <tr>  <td>Header</td>         <td>Value</td>          </tr>
    <tr>  <td>Date and time</td>  <td>{date_time}</td>    </tr>
    <tr>  <td>Client host</td>    <td>{client_host}</td>  </tr>
    <tr>  <td>Client port</td>    <td>{client_port}s</td> </tr>
    <tr>  <td>Command</td>        <td>{command}</td>      </tr>
    <tr>  <td>Path</td>           <td>{path}</td>         </tr>
    </table>
    </body>
    </html>
'''
```

填充表格的方法如下：

```py
    def create_page(self):
        values = {
            'date_time'   : self.date_time_string(),
            'client_host' : self.client_address[0],
            'client_port' : self.client_address[1],
            'command'     : self.command,
            'path'        : self.path
        }
        page = self.Page.format(**values)
        return page
```

程序的主体没有改变：和以前一样，它创建了一个 `HTTPServer` 类的实例，并将地址和这个请求处理程序作为参数，然后永远为请求提供服务。如果我们运行它并从浏览器发送请求 `http://localhost:8000/something.html`，我们将得到：

```
  Date and time  Mon, 24 Feb 2014 17:17:12 GMT
  Client host    127.0.0.1
  Client port    54548
  Command        GET
  Path           /something.html
```

注意，我们没有得到 404 错误，即使 something.html 页面并不存在。这是因为 Web 服务器只是一个程序，当它收到一个请求时，它可以做任何它想做的事情：返回前一个请求中提到的文件，提供一个随机选择的 Wikipedia 页面，或者我们编程时让它做的任何事情。

## 提供静态页面

显而易见的下一步是从磁盘开始提供页面，而不是动态生成页面。我们将从重写 do_GET 开始：

```py
    def do_GET(self):
        try:
            # 检查清楚需求
            full_path = os.getcwd() + self.path

            # 如果不存在
            if not os.path.exists(full_path):
                raise ServerException("'{0} not found".format(self.path))

            # 如果是文件
            elif os.path.isfile(full_path):
                self.handle_file(full_path)

            # 其它无法处理
            else:
                raise ServerException("unkown object '{0}'".format(self.path))
        # 处理异常
        except Exception as msg:
            self.handle_error(msg)
```

这个方法假设允许访问 Web 服务器下的任何目录（ 通过 `os.getcwd`）。它将其与 URL 中提供的路径相结合（库会自动将其放入 `self.path`，并始终以前导“/”开头），以获取用户所需文件的路径。

如果路径不存在或者它不是一个文件，则该方法通过引发并捕获异常来报告错误。另一方面，如果路径与文件匹配，则调用名为 `handle_file` 的辅助方法来读取并返回内容。此方法只读取文件并使用现有的 `send_content` 将其发送回客户端：

```py
    def handle_file(self, full_path):
        try:
            with open(full_path, 'rb') as reader:
                content = reader.read()
            self.send_content(content)
        except IOError as msg:
            msg = "'{0}' cannot be read: {1}".format(self.path, msg)
            self.handle_error(msg)
```

请注意，我们以二进制模式打开文件，即“rb”中的“b”，这样 Python 就不会试图通过改变看起来像 Windows 行尾的字节序列来“帮助”我们。还请注意，在实际应用中，在提供服务时将整个文件读入内存不是一个好主意，因为文件可能是几 GB 的视频数据。处理这种情况不在本文范围之内。

为了完成这个类，我们需要编写错误处理方法和错误报告页面的模板：

```py
    Error_Page = """\
        <html>
        <body>
        <h1>Error accessing {path}</h1>
        <p>{msg}</p>
        </body>
        </html>
        """

    def handle_error(self, msg):
        content = self.Error_Page.format(path=self.path, msg=msg).encode('utf-8')
        self.send_content(content)
```

这个程序当我们不仔细看的时候感觉有效，但问题是，即使请求的页面不存在，它也总是返回200的状态码。是的，在这种情况下发送回的页面包含错误消息，但是由于浏览器并不认识英语，因此不知道请求实际上失败。为了明确这一点，我们需要修改 `handle_error` 和 `send_content` 如下：

```py
    # 处理错误对象
    def handle_error(self, msg):
        content = self.Error_Page.format(path=self.path, msg=msg).encode('utf-8')
        self.send_content(content, 404)

    # 发送的内容
    def send_content(self, content, status=200):
        self.send_response(status)
        self.send_header("Content-type", "text/html")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)
```

请注意，当找不到文件时，我们不会引发 `ServerException`，而是生成一个错误页。`ServerException` 意味着服务器代码中有一个内部错误，也就是说，我们出错了。另一方面，`handle_error` 创建的错误页面会在用户出错时出现，例如，向我们发送了一个不存在的文件的URL。[^handleerror]

[^handleerror]:在本文中，我们将多次使用 `handle_error`，包括一些状态码 404 不合适的情况。当你继续阅读时，请尝试考虑如何扩展此程序，以便在每种情况下都可以轻松地提供响应状态码。

## 列表目录

下一步，我们可以教 Web 服务器在 URL 中的路径是目录而不是文件时显示目录内容的列表。我们甚至可以更进一步，让它在目录中查找 index.html 文件来显示，并且仅在该文件不存在时显示目录的内容。

但是最好不要将这些规则构建到 `do_GET` 中，因为生成的方法将与控制特殊行为的 `if` 语句混在了一起。正确的解决方案是退后一步来解决一般问题，即弄清楚如何处理 URL。 这是 `do_GET` 方法的重写：

```py
    def do_GET(self):
        try:
            self.full_path = os.getcwd() + self.path
            print(self.full_path)

            for case in self.Cases:
                if case.test(self):
                    case.act(self)
                    break
        # 处理异常
        except Exception as msg:
            self.handle_error(msg)
```

第一步是相同的：找出被请求的完整路径。不过，在那之后，代码看起来就完全不同了。这个版本不是一堆内联测试，而是循环遍历存储在列表中的一组 case。每个 case 都是一个有两个方法的对象：test，它告诉我们是否能够处理请求；act，它实际上对请求进行操作。一旦找到正确的情况，我们就让它处理请求并跳出循环。

这三个 case 类重现了我们前面服务器的行为：

```py
class case_no_file(object):
    '''文件或目录不存在'''
    def test(self, handler):
        return not os.path.exists(handler.full_path)

    def act(self, handler):
        raise ServerException("'{0}' not found".format(handler.path))

class case_existing_file(object):
    '''文件存在'''

    def test(self, handler):
        return os.path.isfile(handler.full_path)

    def act(self, handler):
        handler.handle_file(handler.full_path)
class case_always_fail(object):
    '''工作的基础场景'''
    def test(self, handler):
        return True
    
    def act(self, handler):
        raise ServerException("Unkown object '{0}'".format(handler.path))
```

下面是我们如何在 `RequestHandler` 类的顶部构造案例处理程序列表：

```py
class RequestHandler(http.server.BaseHTTPRequestHandler):
    '''
    如果请求的路径映射到一个文件，则使用该文件服务。
    如果出现任何错误，将构造一个错误页。
    '''

    Cases = [case_no_file(),
             case_existing_file(),
             case_always_fail()]

    ...everything else as before...
```

现在，从表面上看，这使我们的服务器变得更加复杂，而不是更少：文件从 74 行增加到 99 行，并且在没有任何新功能的情况下增加了一个额外的层级。当我们回到本章节开始的任务并尝试教我们的服务器提供 index.html： 如果目录下有这个页面，则返回该页面；如果没有，则显示该目录的文件列表。前者的处理程序为：

```py
class case_directory_index_file(object):
    '''处理包含 index.html 的目录'''
    def index_path(self, handler):
        return os.path.join(handler.full_path, 'index.html')

    def test(self, handler):
        return os.path.isdir(handler.full_path) and \
            os.path.isfile(self.index_path(handler))

    def act(self, handler):
        handler.handle_file(self.index_path(handler))
```

这里，辅助方法 `index_path` 构造指向 `index.html` 文件的路径；将其放入案例处理程序可防止 `RequestHandler` 中出现混乱。`test` 方法检查路径是否是包含 `index.html` 的目录，`act` 方法请求主请求处理程序为该页面提供服务。

对 `RequestHandler` 的唯一更改是将一个 `case_directory_index_file` 对象添加到我们的“案例”列表中：

```py
    Cases = [case_no_file(),
             case_existing_file(),
             case_directory_index_file(),
             case_always_fail()]
```

如果目录不包含 index.html 页呢？`test` 和上面未执行策略性插入的 `test` 一样，但是 `act` 方法呢？它应该做什么？

```py
class case_directory_no_index_file(object):
    '''处理没有 index.html 页面的目录'''
    def index_path(self, handler):
        return os.path.join(handler.full_path, 'index.html')

    def test(self, handler):
        return os.path.isdir(handler.full_path) and \
            not os.path.isfile(self.index_path(handler))
    
    def act(self, handler):
        ???
```

看来我们陷入了困境。从逻辑上讲，`act` 方法应该创建并返回目录列表，但是我们现有的代码不允许这样做：`RequestHandler.do_GET` 调用 `act`，但不处理它的返回值。现在，让我们向 `RequestHandler` 添加一个方法来生成一个目录列表，并从case handler的 `act` 中调用它：

```py
class case_directory_no_index_file(object):
    '''处理没有 index.html 页面的目录'''

    # ...index_path and test as above...

    def act(self, handler):
        handler.list_dir(handler.full_path)


class RequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):

    # ...all the other code...

    # How to display a directory listing.
    Listing_Page = '''\
        <html>
        <body>
        <ul>
        {0}
        </ul>
        </body>
        </html>
        '''

    def list_dir(self, full_path):
        try:
            entries = os.listdir(full_path)
            bullets = ['<li>{0}</li>'.format(e) for e in  entries if not e.startswith('.')]
            page = self.Listing_Page.format('\n'.join(bullets)).encode('utf-8')
            self.send_content(page)
        except OSError as msg:
            msg = "'{0}' cannot be listed: {1}".format(self.path, msg)
            self.handle_error(msg)
```

## CGI 协议

当然，大多数人不会为了添加新功能而编辑 Web 服务器的源代码。为了避免它们不得不这样做，服务器一直支持一种称为公共网关接口（CGI）的机制，该机制为 Web 服务器运行外部程序以满足请求提供了一种标准方法。

例如，我们想在服务器上显示一个 HTML 页面。我们只需几行代码就可以在独立程序中执行此操作：

```py
from datetime import datetime
print '''\
<html>
<body>
<p>Generated {0}</p>
</body>
</html>'''.format(datetime.now())
```

为了让 Web 服务器为我们运行此程序，我们添加了以下案例处理程序：

```py
class case_cgi_file(object):
    '''可以运行的文件'''

    def test(self, handler):
        return os.path.isfile(handler.full_path) and \
            handler.full_path.endswith('.py')

    def act(self, handler):
        handler.run_cgi(handler.full_path)
```

`test` 方法很简单：文件路径是否以 .py 结尾？如果是这样，`RequestHandler` 将运行该程序。

```py
    def run_cgi(self, full_path):
        cmd = "python " + full_path
        child_stdout = os.popen(cmd)
        data = child_stdout.read()
        child_stdout.close()
        self.send_content(data.encode('utf-8'))
```

这是非常不安全的：如果有人知道我们服务器上 Python 文件的路径，我们就让他们运行它，而不必担心它可以访问哪些数据，它是否可能包含一个无限循环或其他东西。

抛开这些，核心思想很简单：

1. 在子进程中运行程序。
2. 捕获子进程发送到标准输出的任何内容。
3. 把它发送回提出请求的客户机。

完整的 CGI 协议比这个更丰富，特别是它允许 URL 中带有参数，服务器将这些参数传递给正在运行的程序，但是这些细节不会影响系统的整体架构。

这又一次变得相当纠结。`RequestHandler`最初有一个方法 `handle_file`，用于处理内容。我们现在添加了两个特殊情况，分别是`list_dir` 和 `run_cgi`。这三种方法并不真正属于它们所处的位置，因为它们主要被其他人使用。

解决方法很简单：为我们所有的案例处理程序创建一个父类，如果（并且仅当）其他方法被两个或多个处理程序共享时，将它们移动到该类中。完成后，`RequestHandler` 类如下所示：

```py
class RequestHandler(http.server.BaseHTTPRequestHandler):
    '''
    如果请求的路径映射到一个文件，则使用该文件服务。
    如果出现任何错误，将构造一个错误页。
    '''

    Cases = [case_no_file(),
        case_cgi_file(),
        case_existing_file(),
        case_directory_index_file(),
        case_directory_no_index_file(),
        case_always_fail()]

    # 展示错误的页面
    Error_Page = """\
        <html>
        <body>
        <h1>Error accessing {path}</h1>
        <p>{msg}</p>
        </body>
        </html>
    """

    # 分类处理请求
    def do_GET(self):
        try:
            self.full_path = os.getcwd() + self.path

            for case in self.Cases:
                if case.test(self):
                    case.act(self)
                    break
        # 处理异常
        except Exception as msg:
            self.handle_error(msg)

    # 处理错误对象
    def handle_error(self, msg):
        content = self.Error_Page.format(path=self.path, msg=msg).encode('utf-8')
        self.send_content(content, 404)

    # 发送的内容
    def send_content(self, content, status=200):
        self.send_response(status)
        self.send_header("Content-type", "text/html")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)
```

我们的案例处理程序的父类是：

```py
class base_case(object):
    '''case handler 的父类'''

    def handle_file(self, handler, full_path):
        try:
            with open(full_path, 'rb') as reader:
                content = reader.read()
            handler.send_content(content)
        except IOError as msg:
            msg = "'{0}' cannot be read: {1}".format(self.path, msg)
            handler.handle_error(msg)

    def index_path(self, handler):
        return os.path.join(handler.full_path, 'index.html')

    def test(self, handler):
        assert False, "Not implemented."

    def act(self, handler):
        assert False, 'Not implemented.'
```

现有文件的处理程序（只是随机选取一个示例）是：

```py
class case_existing_file(base_case):
    '''文件存在'''

    def test(self, handler):
        return os.path.isfile(handler.full_path)

    def act(self, handler):
        self.handle_file(handler, handler.full_path)
```

## 结论

原始代码与重构版本之间的差异反映了两个重要的思想。第一种方法是将类视为相关服务的集合。`RequestHandler` 和 `base_case` 不做决定或采取行动；它们提供了其他类可以用来做这些事情的工具。

第二个是可扩展性：人们可以通过编写一个外部 CGI 程序或添加一个 case  handler 类来向我们的 Web 服务器添加新功能。后者确实需要对 `RequestHandler` 进行一行更改（在Cases列表中插入case处理程序），但是我们可以通过让 Web 服务器读取配置文件并从中加载处理程序类来消除这种情况。在这两种情况下，它们都可以忽略最低级的细节，就像 `BaseHTTPRequestHandler` 类的作者允许我们忽略处理套接字连接和解析 HTTP 请求的细节一样。

这些想法通常是有用的；看看你是否能找到在你自己的项目中使用它们的方法。