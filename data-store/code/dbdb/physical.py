# 本部分从一个对文件对象的简单封装开始，
# 目的是提供一个 write() 的对象地址和一
# 个超级块。但在我编写的时候，我意识到用
# 户并不想处理写块的长度（Pickle也不会
# 帮你处理），所以模块将文件对象抽象到它
# 简化的 Key/Value 中。简化是因为你不能
# 选择 key，并且它不会释放空间。

import os
import struct
import dbdb.locks as locks

import portalocker

class Storage(object):
    SUPERBLOCK_SIZE = 4096 # 块大小
    INTEGER_FORMAT = "!Q" # 整型格式，"!’代表网络字节序（Big-Endian），Q代表8位unsigned long long
    INTEGER_LENGTH = 8  # 整型长度

    def __init__(self, f):
        self._f = f
        self.locked = False
        self._ensure_superblock()

    def _ensure_superblock(self):
        """确保文件长度是整块
        """
        self.lock()
        self._seek_end()
        end_address = self._f.tell() # 文件指针当前位置，即文件长度
        if end_address < self.SUPERBLOCK_SIZE:
            self._f.write(b'\x00' * (self.SUPERBLOCK_SIZE - end_address))
        self.unlock()

    def lock(self):
        """对数据库加锁
        """
        if not self.locked:
            locks.lock(self._f, locks.LOCK_EX)
            self.locked = True
            return True
        else:
            return False

    def unlock(self):
        """对数据库解锁
        """
        if self.locked:
            self._f.flush()           
            locks.unlock(self._f)  
            print("unlock")             
            self.locked = False

    def _seek_end(self):
        """文件指针移动到末尾
        """
        self._f.seek(0, os.SEEK_END)

    def _seek_superblock(self):
        """文件指针移动到开头
        """
        self._f.seek(0)

    def _bytes_to_integer(self, integer_bytes):
        """字节转整型
        """
        return struct.unpack(self.INTEGER_FORMAT, integer_bytes)[0]

    def _integer_to_bytes(self, integer):
        """整型转字节
        """
        return struct.pack(self.INTEGER_FORMAT, integer)

    def _read_integer(self):
        """读取一个整型
        """
        return self._bytes_to_integer(self._f.read(self.INTEGER_LENGTH))

    def _write_integer(self, integer):
        """写入一个整型
        """
        self.lock()
        self._f.write(self._integer_to_bytes(integer))

    def write(self, data):
        """写入数据
        """
        self.lock()
        self._seek_end()
        object_address = self._f.tell()
        self._write_integer(len(data))
        self._f.write(data)
        return object_address

    def read(self, address):
        """读取数据
        """
        self._f.seek(address)
        length = self._read_integer()
        data = self._f.read(length)
        return data

    def commit_root_address(self, root_address):
        """更新root的地址
        """
        self.lock()
        self._f.flush()
        self._seek_superblock()
        self._write_integer(root_address)
        self._f.flush()
        self.unlock()

    def get_root_address(self):
        """获取root的地址
        """
        self._seek_superblock()
        root_address = self._read_integer()
        return root_address

    def close(self):
        """关闭数据库
        """
        self.unlock()
        self._f.close()

    @property
    def closed(self):
        """是否关闭
        """
        return self._f.closed
        