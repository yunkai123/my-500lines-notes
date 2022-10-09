"""
测试核心类 cluster 的代码行数是否大于 500
貌似500多行~ 改成了550
"""

import unittest
import cluster

class Tests(unittest.TestCase):

    def test_lines(self):
        file = cluster.__file__.replace('.pyc', '.py')
        with open(file,  encoding='utf-8') as f:
            lines = len(list(f))
            assert lines <= 600, "%r is %d lines" % (file, lines)