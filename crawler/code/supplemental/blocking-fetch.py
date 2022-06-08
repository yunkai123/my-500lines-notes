import socket


# 原项目地址改成了HTTPS，这里使用baidu代替
HOST = "www.baidu.com"
PORT = 80


def threaded_method():
    sock = socket.socket()
    sock.connect((HOST, PORT))
    request = 'GET / HTTP/1.0\r\nHost: ' + HOST + '\r\n\r\n'
    sock.send(request.encode())
    response = b''

    chunk = sock.recv(4096)
    while chunk:
        response += chunk
        chunk = sock.recv(4096)


    print(response)

threaded_method()