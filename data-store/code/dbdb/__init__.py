import os

from dbdb.interface import DBDB

# 指定能被其它模块引用的函数、类等
__all__ = ['DBDB', 'connect']

def connect(dbname):
    '''连接数据库，其实就是打开本地文件
    '''
    try:
        f = open(dbname, 'r+b')
    except IOError:
        fd = os.open(dbname, os.O_RDWR | os.O_CREAT)
        f = os.fdopen(fd, 'r+b')
    return DBDB(f)