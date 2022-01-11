import sys, os, http.server

class ServerException(Exception):
    '''用于内部错误报告'''
    pass

class case_no_file(object):
    '''文件或目录不存在'''
    def test(self, handler):
        return not os.path.exists(handler.full_path)

    def act(self, handler):
        raise ServerException("'{0}' not found".format(handler.path))

class case_cgi_file(object):
    '''可以运行的文件'''

    def test(self, handler):
        return os.path.isfile(handler.full_path) and \
            handler.full_path.endswith('.py')

    def act(self, handler):
        handler.run_cgi(handler.full_path)

class case_existing_file(object):
    '''文件存在'''

    def test(self, handler):
        return os.path.isfile(handler.full_path)

    def act(self, handler):
        handler.handle_file(handler.full_path)

class case_directory_index_file(object):
    '''处理包含 index.html 的目录'''
    def index_path(self, handler):
        return os.path.join(handler.full_path, 'index.html')

    def test(self, handler):
        return os.path.isdir(handler.full_path) and \
            os.path.isfile(self.index_path(handler))

    def act(self, handler):
        handler.handle_file(self.index_path(handler))

class case_directory_no_index_file(object):
    '''处理没有 index.html 页面的目录'''
    def index_path(self, handler):
        return os.path.join(handler.full_path, 'index.html')

    def test(self, handler):
        return os.path.isdir(handler.full_path) and \
            not os.path.isfile(self.index_path(handler))
    
    def act(self, handler):
        handler.list_dir(handler.full_path)

class case_always_fail(object):
    '''工作的基础场景'''
    def test(self, handler):
        return True
    
    def act(self, handler):
        raise ServerException("Unkown object '{0}'".format(handler.path))

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
    # 展示目录下的列表
    Listing_Page = '''\
        <html>
        <body>
        <ul>
        {0}
        </ul>
        </body>
        </html>
        '''

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

    def handle_file(self, full_path):
        try:
            with open(full_path, 'rb') as reader:
                content = reader.read()
            self.send_content(content)
        except IOError as msg:
            msg = "'{0}' cannot be read: {1}".format(self.path, msg)
            self.handle_error(msg)

    def list_dir(self, full_path):
        try:
            entries = os.listdir(full_path)
            bullets = ['<li>{0}</li>'.format(e) for e in  entries if not e.startswith('.')]
            page = self.Listing_Page.format('\n'.join(bullets)).encode('utf-8')
            self.send_content(page)
        except OSError as msg:
            msg = "'{0}' cannot be listed: {1}".format(self.path, msg)
            self.handle_error(msg)

    def run_cgi(self, full_path):
        cmd = "python " + full_path
        child_stdout = os.popen(cmd)
        data = child_stdout.read()
        child_stdout.close()
        self.send_content(data.encode('utf-8'))

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

if __name__ == '__main__':
    serverAddress = ('', 8080)
    server = http.server.HTTPServer(serverAddress, RequestHandler)
    server.serve_forever()