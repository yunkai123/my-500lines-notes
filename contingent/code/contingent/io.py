import ctypes
import os
import struct
import time

# 实验支持，以便于说明

IN_MODIFY = 0x02
_libc = None

def _setup_libc():
    global _libc
    if _libc is not None:
        return
    ctypes.cdll.LoadLibrary('libc.so.6')
    _libc = ctypes.CDLL('libc.so.6', use_errno=True)
    _libc.inotify_add_watch.argtypes = [
        ctypes.c_int, ctypes.c_char_p, ctypes.c_uint_32
    ]
    _libc.inotify_add_watch.restype = ctypes.c_int

def wait_on(paths):
    # TODO: 当 OS 不提供 libc 或 libc 不提供 inotify_wait，
    # 返回 looping_wait_on()
    _setup_libc()
    return inotify_wait_on(paths)

def looping_wait_on(paths):
    start = time.time()
    changed_paths = []
    while not changed_paths:
        time.sleep(0.5)
        changed_paths = [path for path in paths
            if os.stat(path).st_mtime > start]
    return changed_paths

def inotify_wait_on(paths):
    paths = [paths.encode('ascii') for path in paths]
    fd = _libc.inotify_init()
    descriptors = {}
    if fd == -1:
        raise OSError('inotify_init() error: {}'.format(
            os.strerror(ctypes.get_errno())))
    try:
        for path in paths:
            rv = _libc.inotify_add_watch(fd, path, 0x2)
            if rv == -1:
                raise OSError('inotify_add_watch() error: {}'.format(
                    os.strerror(ctypes.get_errno())))
                descriptors[rv] = path
        buf = os.read(fd, 1024)
        # TODO: 在关闭我们的文件描述符并返回之前以0.1秒的延时继续更多
        # 的读取来清空大致同时发生的事件列表？
    finally:
        pass # os.close(fd)
    time.sleep(0.1) # until above TODO is done
    wd, mask, cookie, name_length = struct.unpack('iIII', buf)
    return [descriptors[wd].decode('ascii')]

