from http.server import HTTPServer, BaseHTTPRequestHandler
import json
from ocr import OCRNeuralNetwork
import numpy as np

HOST_NAME = 'localhost'
PORT_NUMBER = 8000
HIDDEN_NODE_COUNT = 15

# 将数据样本和标签加载到矩阵中
data_matrix = np.loadtxt(open('data.csv', 'rb'), delimiter=',')
data_labels = np.loadtxt(open('dataLabels.csv', 'rb'))

# 从 numpy ndarrays 转换为 python 列表
data_matrix = data_matrix.tolist()
data_labels = data_labels.tolist()

# 如果一个神经网络文件不存在，使用所有5000个现有数据样本对其进行训练。
# 基于神经网络收集的 neural_network_design.py，对于隐藏节点，15是最佳数。
nn = OCRNeuralNetwork(HIDDEN_NODE_COUNT, data_matrix, data_labels, list(range(5000)))

class JSONHandler(BaseHTTPRequestHandler):
    def do_POST(s):
        response_code = 200
        response = ""
        var_len = int(s.headers.get('Content-Length'))
        content = s.rfile.read(var_len)
        payload = json.loads(content)

        if payload.get('train'):
            nn.train(payload['trainArray'])
            nn.save()
        
        elif payload.get('predict'):
            try:
                response = {"type": "test", "result": nn.predict(str(payload['image']))}
            except:
                response_code = 500
        else:
            response_code =400

        s.send_response(response_code)
        s.send_header("Content-type", "application/json")
        s.send_header("Access-Control-Allow-Origin", "*")
        s.end_headers()
        if response:
            s.wfile.write(bytes(json.dumps(response), "utf-8"))
        return

if __name__ == '__main__':
    httpd = HTTPServer((HOST_NAME, PORT_NUMBER), JSONHandler)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    else:
        print("Unexpected server exception occurred.")
    finally:
        httpd.server_close()