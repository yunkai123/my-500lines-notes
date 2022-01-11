import sys, os, http.server

class ServerException(Exception):
    '''用于内部错误报告'''
    pass


class RequestHandler(http.server.BaseHTTPRequestHandler):
    '''
    如果请求的路径映射到一个文件，则使用该文件服务。
    如果出现任何错误，将构造一个错误页。
    '''

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
            
    def handle_file(self, full_path):
        try:
            with open(full_path, 'rb') as reader:
                content = reader.read()
            self.send_content(content)
        except IOError as msg:
            msg = "'{0}' cannot be read: {1}".format(self.path, msg)
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

if __name__ == '__main__':
    serverAddress = ('', 8080)
    server = http.server.HTTPServer(serverAddress, RequestHandler)
    server.serve_forever()