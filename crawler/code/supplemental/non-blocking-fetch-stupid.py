import socket


sock = socket.socket()
sock.setblocking(False)
try:
    sock.connect(('www.baidu.com', 80))
except BlockingIOError:
    pass

request = 'GET / HTTP/1.0\r\nHost: www.baidu.com\r\n\r\n'
encoded = request.encode('ascii')

while True:
    try:
        sock.send(encoded)
        break
    except OSError as e:
        pass

print('sent')