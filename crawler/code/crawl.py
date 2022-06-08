"""一个简单的网络爬虫 -- 主驱动程序"""

import argparse
import asyncio
import logging
import sys

import crawling
import reporting

# 命令参数

ARGS = argparse.ArgumentParser(description="Web Crawler")
# 是否使用 iocp IO模型
ARGS.add_argument(
    '--iocp', action='store_true', dest='iocp',
    default=False, help='Use IOCP event loop (Windows only)'
)
# 是否使用 select IO模型
ARGS.add_argument(
    '--select', action='store_true', dest='select',
    default=False, help='Use Select event loop instead of default'
)
# 根 URL 集合
ARGS.add_argument(
    'roots', nargs='*',
    default=[], help='Root URL (may be repeated)'
)
# 最大重定向次数
ARGS.add_argument(
    '--max_redirect', action='store', type=int, metavar='N',
    default=10, help='Limit redirection chains (for 301, 302 etc.)'
)
# 最大重试次数
ARGS.add_argument(
    '--max_tries', action='store', type=int, metavar='N',
    default=4, help='Limit reties on network errors'
)
# 最大任务数
ARGS.add_argument(
    '--max_tasks', action='store', type=int, metavar='N',
    default=100, help='Limit concurrent connections'
)
# 排除的 URL
ARGS.add_argument(
    '--exclude', action='store', metavar='REGEX',
    help='Exclude matching URLs'
)
# 启用严格 URL 匹配
ARGS.add_argument(
    '--strict', action='store_true',
    default=True, help='Strict host matching(default)' 
)
# 启用宽松 URL 匹配
ARGS.add_argument(
    '--lenient', action='store_false', dest='strict',
    default=False, help="Lenient host matching"
)
# 根据v的个数确定日志级别，比如 -vvv 就是3
ARGS.add_argument(
    '-v', '--verbose', action='count', dest='level',
    default=3, help='Verbose logging (repeat for more verbose)'
)
# 仅记录错误日志
ARGS.add_argument(
    '-q', '--quit', action='store_const', const=0, dest='level',
    default=2, help='Only log errors'
)
# 自行添加了一个参数，用来将报告写入文件
ARGS.add_argument(
    '--file', default=None, help='report file (default print on console)'
)

def fix_url(url):
    """为 URL 添加 http:// 前缀"""
    if '://' not in url:
        url = 'http://' + url
    return url

def main():
    """主函数
    解析参数，启动事件循环，运行爬虫，打印报告
    """
    args = ARGS.parse_args()
    if not args.roots:
        print('Use --help for command Line help')
        return
    # 日志配置
    levels = (logging.ERROR, logging.WARN, logging.INFO, logging.DEBUG)
    root_logger= logging.getLogger()
    root_logger.setLevel(levels[min(args.level, len(levels) - 1)]) 
    handler = logging.FileHandler('crawl.log', 'w', 'utf-8') 
    handler.setFormatter(logging.Formatter('%(asctime)s - %(filename)s[line:%(lineno)d] - %(levelname)s: %(message)s')) 
    root_logger.addHandler(handler)
    
    if args.iocp: # 使用 iocp 模型
        from asyncio.windows_events import ProactorEventLoop
        loop = ProactorEventLoop
        asyncio.set_event_loop(loop)
    elif args.select: # 使用 select 模型
        loop = asyncio.SelectorEventLoop()
        asyncio.set_event_loop(loop)
    else: # 默认模型
        loop = asyncio.get_event_loop()

    roots = {fix_url(root) for root in args.roots}

    crawler = crawling.Crawler(
        roots,
        exclude=args.exclude,
        strict=args.strict,
        max_redirect=args.max_redirect,
        max_tries=args.max_tries,
        max_tasks=args.max_tasks
    )

    try:
        loop.run_until_complete(crawler.crawl())
    except KeyboardInterrupt:
        sys.stderr.flush()
        print('\nInterrupted\n')
    finally:
        f = open(args.file, 'w+') if args.file else None
        reporting.report(crawler, file=f)
        if f:
            f.close()

        # 关闭资源
        loop.stop()
        loop.run_forever()
        loop.close()

if __name__ == '__main__':
    main()