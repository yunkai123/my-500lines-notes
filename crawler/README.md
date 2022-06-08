
- 原文作者：  A. Jesse Jiryu Davis 和 Guido van Rossum
- 项目： Web 爬虫
- 需求：
  - Python 3.8+
  - aiohttp

这是一个网络爬虫。你给它一个URL，它就会抓取其中 HTML 页面中的 href 链接访问网站。

它对已爬取的页面不会做任何事情。查找链接的算法很简单———这部分很容易修改，但不是特别有趣（只需使用你最喜欢的 HTML 解析器替换正则表达式）。

本示例的重点是展示如何使用 asyncio 模块编写比较复杂的HTTP客户端应用程序，此模块最初的昵称是Tulip， 是 Python 3.4 引入的基于PEP 3156的新特性的标准库。这个示例使用一个名为“aiohttp”的异步 HTTP 客户端实现。

如下方式安装爬虫依赖：

```
    python3 -m pip install -r requirements.txt
```

为了快速高效，程序打开了多个并行连接到服务器，并将连接复用于多个请求。

示例命令行（-q 减少日志输出）：

```
    python3 crawl.py -q xkcd.com
```

使用 --help 查看所有选项。