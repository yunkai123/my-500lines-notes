"""一个简单的网络爬虫 -- 实现爬取逻辑的类

这里将 @asyncio.coroutine 和 yield from替换成了 async 和 await
"""

import asyncio
import cgi
from collections import namedtuple
import logging
import re
import time
import urllib.parse

try:
    # Python 3.4
    from asyncio import JoinableQueue as Queue
except ImportError:
    # Python 3.5+
    from asyncio import Queue

import aiohttp

LOGGER = logging.getLogger(__name__)

def lenient_host(host):
    parts = host.split('.')[-2:]
    return ''.join(parts)

def is_redirect(response):
    return response.status in (300, 301, 302, 303, 307)

FetchStatistic = namedtuple('FetchStatistic',
    [
        'url',
        'next_url',
        'status',
        'exception',
        'size',
        'content_type',
        'encoding',
        'num_urls',
        'num_new_urls'
    ])

class Crawler:
    """爬取 URL 集合
    本类管理了两个 URL 集合： urls 和 done，urls 是观测到的 URL 的集合，
    done 是 FetchStatistic 列表
    """
    def __init__(self, roots, exclude=None, strict=True,
        max_redirect=10, max_tries=4, max_tasks=10, *, loop=None):
        if loop:
            asyncio.set_event_loop(loop)
        self.loop = loop or asyncio.get_event_loop()
        self.roots = roots
        self.exclude = exclude
        self.strict = strict
        self.max_redirect = max_redirect
        self.max_tries = max_tries
        self.max_tasks = max_tasks
        self.q = Queue()
        self.seen_urls = set()
        self.done = []
        self.root_domains = set()
        for root in roots:
            parts = urllib.parse.urlparse(root)
            host = parts.hostname
            if not host:
                continue
            if re.match(r'\A[\d\.]*\Z', host):
                self.root_domains.add(host)
            else:
                host = host.lower()
                if self.strict:
                    self.root_domains.add(host)
                else:
                    self.root_domains.add(lenient_host(host))
        for root in roots:
            self.add_url(root)
        self.t0 = time.time()
        self.t1 = None

    def host_okay(self, host):
        """检查一个主机是否要被爬取"""
        # 转为小写
        host = host.lower()
        # 如果在根域中
        if host in self.root_domains:
            return True
        # 如果是 IP
        if re.match(r'\A[\d\.]*\Z', host):
            return False
        if self.strict:
            return self._host_okay_strictish(host)
        else:
            return self._host_okay_lenient(host)

    def _host_okay_strictish(self, host):
        """ 校验一个主机是否应该爬取，严格版本
        检查和初始的 `www.` 组件是否相等
        """
        # 没有`www.`则加上，有则去掉？这块不太明白
        host = host[4:] if host.startswith('www.') else 'www.' + host
        return host in self.root_domains

    def _host_okay_lenient(self, host):
        """校验一个主机是否应该爬取，宽松版本
        仅比较最后两个组件部分
        """
        return lenient_host(host) in self.root_domains

    def record_statistic(self, fetch_statistic):
        """ 记录已完成或者已失败的 URL 的 FetchStatistic """
        self.done.append(fetch_statistic)

    async def parse_links(self, response):
        """ 返回FetchStatistic和链接列表 """
        links = set()
        content_type = None
        encoding = None
        body = await response.read()

        # 仅分析响应成功的报文
        if response.status == 200:
            content_type = response.headers.get('content-type')
            pdict = {}

            if content_type:
                content_type, pdict = cgi.parse_header(content_type)
            
            # 获取编码
            encoding = pdict.get('charset', 'utf-8')
            if content_type in ('text/html', 'application/xml'):
                text = await response.text()

                # 从报文中解析 URL
                urls = set(re.findall(r'''(?i)href=["']([^\s"'<>]+)''',
                    text))

                if urls:
                    LOGGER.info('got %r distinct urls from %r', 
                        len(urls), response.url)

                for url in urls:
                    # 从相对地址的片段中创建出绝对 URL 地址 
                    normalized = urllib.parse.urljoin(str(response.url), url)
                    # 分离 URL 中的片段
                    defragmented, frag = urllib.parse.urldefrag(normalized)
                    if self.url_allowed(defragmented):
                        links.add(defragmented)

        stat = FetchStatistic(
            url=str(response.url),
            next_url=None,
            status=response.status,
            exception=None,
            size=len(body),
            content_type=content_type,
            encoding=encoding,
            num_urls=len(links),
            num_new_urls=len(links - self.seen_urls)
        )

        return stat, links

    async def fetch(self, url, max_redirect):
        """抓取一个 URL """
        tries = 0
        exception = None
        async with aiohttp.ClientSession() as session:
            while tries < self.max_tries:
                try:
                    async with session.get(url, allow_redirects=False) as response:
                        # 如果需要重定向
                        if is_redirect(response):
                            location = response.headers['location']
                            next_url = urllib.parse.urljoin(url, location)
                            self.record_statistic(FetchStatistic(
                                url=url,
                                next_url=next_url,
                                status=response.status,
                                exception=None,
                                size=0,
                                content_type=None,
                                encoding=None,
                                num_urls=0,
                                num_new_urls=0
                            ))

                            if next_url in self.seen_urls:
                                return
                            # 允许继续重定向
                            if max_redirect > 0:
                                LOGGER.info('redirect to %r from %r', next_url, url)
                                self.add_url(next_url, max_redirect-1)
                            # 不允许继续重定向，则报错
                            else:
                                LOGGER.error('redirect limit reached for %r from %r', 
                                    next_url, url)
                        else:
                            stat, links = await self.parse_links(response)
                            self.record_statistic(stat)
                            # 将未出现的 URL 放入队列中
                            for link in links.difference(self.seen_urls):
                                self.q.put_nowait((link, self.max_redirect))
                            self.seen_urls.update(links)
                    if tries > 1:
                        LOGGER.info('try %r for %r success', tries, url)
                    break
                except aiohttp.ClientError as client_error:
                    LOGGER.info('try %r for %r raised %r', tries, url, client_error)
                    exception = client_error
                except Exception as e:
                    print(e)
                tries += 1
            else:
                # 如果到达最大尝试次数都未成功
                LOGGER.error('%r failed after %r tries', url, self.max_tries)
                self.record_statistic(FetchStatistic(
                    url=url,
                    next_url=None,
                    status=None,
                    exception=exception,
                    size=0,
                    content_type=None,
                    encoding=None,
                    num_urls=0,
                    num_new_urls=0
                ))
                return
        

    async def work(self):
        """处理队列中的项"""
        try:
            while True:
                url, max_redirect = await self.q.get()
                assert url in self.seen_urls
                await self.fetch(url, max_redirect)
                self.q.task_done()
        except asyncio.CancelledError:
            pass

    def url_allowed(self, url):
        '''检查 URL 是否允许访问'''
        # 如果 URL 在排除列表则不访问
        if self.exclude and re.search(self.exclude, url):
            return False
        parts = urllib.parse.urlparse(url)
        LOGGER.debug('url: %r', parts)
        # 检查协议
        if parts.scheme not in ('http', 'https'):
            LOGGER.debug('skipping non-http schema in %r', url)
            return False
        # 检查主机
        # host, port = urllib.parse.urlparse(parts.netloc)
        host = parts.hostname
        if not self.host_okay(host):
            LOGGER.debug('skipping non-root host in %r', url)
            return False
        return True

    def add_url(self, url, max_redirect=None):
        """ 将 URL 放到集合中，说明已经访问过，防止后续再次访问"""
        if max_redirect is None:
            max_redirect = self.max_redirect
        LOGGER.debug('add %r %r', url, max_redirect)
        self.seen_urls.add(url)
        self.q.put_nowait((url, max_redirect))

    async def crawl(self):
        """运行爬虫直到全部结束"""
        workers = [asyncio.Task(self.work()) for _ in range(self.max_tasks)]
        
        self.t0 = time.time()
        await self.q.join()
        self.t1 = time.time()
        for w in workers:
            w.cancel()




        