""" 简陋的小爬虫，演示了手工制作的事件循环和协同路由。

首先读取 loop-with-callbacks.py。此示例建立在该示例的基础上
并使用生成器进行回调。
"""

from selectors import *
import socket
import re
import urllib.parse
import time

# 原项目地址改成了HTTPS，这里使用baidu代替
HOST = "www.baidu.com"
PORT = 80

class Future:
    def __init__(self):
        self.result = None
        self._callbacks = []

    def result(self):
        return self.result

    def add_done_callback(self, fn):
        self._callbacks.append(fn)

    def set_result(self, result):
        self.result  = result
        for fn in self._callbacks:
            fn(self)

    def __iter__(self):
        yield self  # This tells Task to wait for completion.
        return self.result


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


urls_todo = set(['/'])
urls_seen = set(['/'])
concurrency_achieved = 0
selector = DefaultSelector()
stopped = False

def connect(sock, address):
    f = Future()
    sock.setblocking(False)
    try:
        sock.connect(address)
    except BlockingIOError:
        pass

    def on_connected():
        f.set_result(None)

    selector.register(sock.fileno(), EVENT_WRITE, on_connected)
    yield from f
    selector.unregister(sock.fileno())


def read(sock):
    f = Future()

    def on_readable():
        f.set_result(sock.recv(4096))

    selector.register(sock.fileno(), EVENT_READ, on_readable)
    chunk = yield from f
    selector.unregister(sock.fileno())
    return chunk

def read_all(sock):
    response = []
    chunk = yield from read(sock)
    while chunk:
        response.append(chunk)
        chunk = yield from read(sock)
        
    return  b''.join(response)

class Fetcher:
    def __init__(self, url):
        self.response = b''
        self.url = url

    def fetch(self):
        global concurrency_achieved, stopped
        concurrency_achieved = max(concurrency_achieved, len(urls_todo))

        #sock = socket.socket()
        sock = socket.socket()
        yield from connect(sock, (HOST, PORT))
        get = 'GET {} HTTP/1.0\r\nHost: {}\r\n\r\n'.format(self.url, HOST)
        sock.send(get.encode())
        self.response = yield from read_all(sock)

        self._process_response()
        urls_todo.remove(self.url)
        if not urls_todo:
            stopped = True
        print(self.url)

    def body(self):
        body = self.response.split(b'\r\n\r\n', 1)[1]
        return body.decode('utf-8')

    def _process_response(self):
        if not self.response:
            print('error: {}'.format(self.url))
            return
        if not self._is_html():
            return
        urls = set(re.findall(r'''(?i)href=["']?([^\s"'<>]+)''',
                              self.body()))

        for url in urls:
            normalized = urllib.parse.urljoin(self.url, url)
            parts = urllib.parse.urlparse(normalized)
            if parts.scheme not in ('', 'http', 'https'):
                continue
            host = parts.netloc
            if host and host.lower() not in (HOST):
                continue
            defragmented, frag = urllib.parse.urldefrag(parts.path)
            if defragmented not in urls_seen:
                urls_todo.add(defragmented)
                urls_seen.add(defragmented)
                Task(Fetcher(defragmented).fetch())

    def _is_html(self):
        head, body = self.response.split(b'\r\n\r\n', 1)
        headers = dict(h.split(': ') for h in head.decode().split('\r\n')[1:])       
        return headers.get('Content-Type', '').startswith('text/html')

start = time.time()
fetcher = Fetcher('/')
Task(fetcher.fetch())

while not stopped:
    events = selector.select()
    for event_key, event_mask in events:
        callback = event_key.data
        callback()

print('{} URLs fetched in {:.1f} seconds, achieved concurrency = {}'.format(
    len(urls_seen), time.time() - start, concurrency_achieved))
