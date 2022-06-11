import csv
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import numpy as np
from numpy import matrix
from numpy import power
from collections import namedtuple
import math
import random
import os
import json

"""
本类做了一些神经网络的初步训练，以预测绘制
基于数据矩阵和数据标签中的数据集的数字。然后就可以用来
通过使用数据数组调用 train() 来进一步训练网络或预测
调用 predict() 可以得到什么数字。
定义神经网络的权重可以保存到一个文件，NN_FILE_PATH，
在初始化时重新加载。
"""

class OCRNeuralNetwork:
    LEARNING_RATE = 0.1
    WIDTH_IN_PIXEL = 20
    NN_FILE_PATH = 'nn.json'

    def __init__(self, num_hidden_nodes, data_matrix, data_labels, training_indices, use_file=True):
        self.sigmoid = np.vectorize(self._sigmoid_scalar)
        self.sigmoid_prime = np.vectorize(self._sigmoid_prime_scalar)
        self._use_file = use_file
        self.data_matrix = data_matrix
        self.data_labels = data_labels

        if (not os.path.isfile(OCRNeuralNetwork.NN_FILE_PATH) or not use_file):
            # 第一步：初始化权重为较小的数值
            self.theta1 = self._rand_initialize_weights(400, num_hidden_nodes)
            self.theta2 = self._rand_initialize_weights(num_hidden_nodes, 10)
            self.input_layer_bias = self._rand_initialize_weights(1, num_hidden_nodes)
            self.hidden_layer_bias = self._rand_initialize_weights(1, 10)

            # 使用示例数据训练
            TrainData = namedtuple('TrainData', ['y0', 'label'])
            self.train([TrainData(self.data_matrix[i], int(self.data_labels[i])) for i in training_indices])
            self.save()
        else:
            self._load()

    def _rand_initialize_weights(self, size_in, size_out):
        """生成一组 -0.06 到 0.06 之间的权重"""
        return [((x * 0.12) - 0.06) for x in np.random.rand(size_out, size_in)]

    # sigmoid激活函数，在标量上操作
    def _sigmoid_scalar(self, z):
        return 1 /(1 + math.e ** -z)

    def _sigmoid_prime_scalar(self, z):
        return self.sigmoid(z) * (1 - self.sigmoid(z))

    def _draw(self, sample):
        pixelArray = [sample[j : j + self.WIDTH_IN_PIXEL] for j in range(0, len(sample), self.WIDTH_IN_PIXEL)]
        plt.imshow(zip(*pixelArray), cmap=cm.Greys_r, interpolation="nearest")
        plt.show()

    def train(self, training_data_array):
        for data in training_data_array:
            # 第二步：向前传播
            # python3 好像只能用data.y0 不能使用data['y0']
            y1 = np.dot(np.mat(self.theta1), np.mat(data.y0).T)

            sum1 = y1 + np.mat(self.input_layer_bias)
            y1 = self.sigmoid(sum1)

            y2 = np.dot(np.array(self.theta2), y1)
            y2 = np.add(y2, self.hidden_layer_bias) # 添加偏差
            y2 = self.sigmoid(y2)

            # 第三步：向后传播
            actual_vals = [0] * 10 # 实际值是一个python列表，便于初始化，后来被转换成np矩阵（向下2行）。
            actual_vals[data.label] = 1
            output_errors = np.mat(actual_vals).T - np.mat(y2)
            hidden_errors = np.multiply(np.dot(np.mat(self.theta2).T, output_errors), self.sigmoid_prime(sum1))

            # 第四步：更新权重
            self.theta1 += self.LEARNING_RATE * np.dot(np.mat(hidden_errors), np.mat(data.y0))
            self.theta2 += self.LEARNING_RATE * np.dot(np.mat(output_errors), np.mat(y1).T)
            self.hidden_layer_bias += self.LEARNING_RATE * output_errors
            self.input_layer_bias += self.LEARNING_RATE * hidden_errors

    def predict(self, test):
        y1 = np.dot(np.mat(self.theta1), np.mat(test).T)
        y1 = y1 + np.mat(self.input_layer_bias)
        y1 = self.sigmoid(y1)

        y2 = np.dot(np.array(self.theta2), y1)
        y2 = np.add(y2, self.hidden_layer_bias)
        y2 = self.sigmoid(y2)

        results = y2.T.tolist()[0]
        return results.index(max(results))

    def save(self):
        if not self._use_file:
            return

        json_neural_network = {
            "theta1": [np_mat.tolist()[0] for np_mat in self.theta1],
            "theta2": [np_mat.tolist()[0] for np_mat in self.theta2],
            "b1": self.input_layer_bias[0].tolist()[0],
            "b2": self.hidden_layer_bias[0].tolist()[0]
        }

        with open(OCRNeuralNetwork.NN_FILE_PATH, 'w') as nnFile:
            json.dump(json_neural_network, nnFile)

    def _load(self):
        if not self._use_file:
            return
        
        with open(OCRNeuralNetwork.NN_FILE_PATH) as nnFile:
            nn = json.load(nnFile)
        self.theta1 = [np.array(li) for li in nn['theta1']]
        self.theta2 = [np.array(li) for li in nn['theta2']]
        self.input_layer_bias = [np.array(nn['b1'][0])]
        self.hidden_layer_bias = [np.array(nn['b2'][0])]

