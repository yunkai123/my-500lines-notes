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