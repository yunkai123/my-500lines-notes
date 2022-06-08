"""提供 Project 类，当输入改变时相关任务会重新构建"""

from contextlib import contextmanager
from collections import namedtuple
from functools import wraps
from .graphlib import Graph

_unavaliable = object()

class Project:
    """作为输入和结果的相关任务集合"""

    def __init__(self):
        self._graph = Graph()
        self._graph.sort_key = task_key
        self._cache = {}
        self._cache_on = True
        self._task_stack = []
        self._todo = set()
        self._trace = None

    def start_tracing(self):
        """开始记录此工程调用的每个任务。"""
        self.trace = []

    def stop_tracing(self, verbose=False):
        """停止记录任务调用，并以文本形式返回前面的追踪记录。

        默认情况下，追踪只显示那些被调用的任务，因为对于它们缓存中没有
        新的返回值可以使用。但如果可选参数 verbose 为 True，那么追踪
        还会包括缓存命中的任务，不需要重新调用。
        """
        text = '\n'.join('{}{} {}'.format(
                '. ' * depth,
                'calling' if not_avaliable else 'return cached',
                task
            ) for (depth, not_avaliable, task) in self._trace
            if verbose or not_avaliable)
        
        self._trace = None
        return text
    
    def _add_task_to_trace(self, task, return_value):
        """将任务添加到当前运行的任务追踪中"""
        tup = (len(self._task_stack), return_value is _unavaliable, task)
        self._trace.append(tup)

    def task(self, task_function):
        """装饰定义为任务的函数
        
        """
        @wraps(task_function)
        def wrapper(*args):
            task = Task(wrapper, args)

            if self._task_stack:
                self._graph.add_edge(task, self._task_stack[-1])

            return_value = self._get_from_cache(task)
            if self._trace is not None:
                self._add_task_to_trace(task, return_value)

            if return_value is _unavaliable:
                self._graph.clear_inputs_of(task)
                self._task_stack.append(task)
                try:
                    return_value = task_function(*args)
                finally:
                    self._task_stack.pop()
                self.set(task, return_value)
            return return_value

        return wrapper

    def _get_from_cache(self, task):
        """返回给定 task 的输出

        如果对于 task 没有当前有效的缓存值，则改为返回
        单例 _unavailable 。
        """
        if not self._cache_on:
            return _unavaliable
        if task in self._todo:
            return _unavaliable
        return self._cache.get(task, _unavaliable)

    @contextmanager
    def cache_off(self):
        """强制任务被调用的上下文管理器
        
        即使工程已经缓存了特定任务的输出重新运行上下文管理器中的
        任务会使工程重新调用任务：

            with project.cache_off():
                my_task()
        """
        original_value = self._cache_on
        self._cache_on = False
        try:
            yield
        finally:
            self._cache_on = original_value

    def set(self, task, return_value):
        """将 task 的 return_value 添加到返回值的缓存中
        
        这使我们可以将新值和任务之前返回的旧值作比较，以确定以
        task 作为输入的任务是否需要加入 to-do 列表来重新计算。
        """
        self._todo.discard(task)
        if (task not in self._cache) or (self._cache[task] != return_value):
            self._cache[task] = return_value
            self._todo.update(self._graph.immediate_consequences_of(task))

    def invalidate(self, task):
        """将 task 标记为需要在下一个 rebuild() 上重新计算。
        
        有两种方法准备调用 rebuild() 表明给定任务的缓存不再有效：一个是手动运行
        任务然后使用 set() 单方面将新值安装到我们的缓存中；另一个是调用此方法使
        task 无效并让 rebuild() 在下意运行时调用它。
        """
        self._todo.add(task)

    def rebuild(self):
        """重复重建每个过期的任务，直到所有任务都是最新的。

        如果近期没有变化，那么 todo 列表是空的，调用很快就返回。否则我们获取当前
        todo 列表中的任务以及它们的下游结果并在每一个上调用 get() 强制重新计算任
        务。

        除非任务图中有循环，否则最终会返回
        """
        while self._todo:
            tasks = self._graph.recursive_consequences_of(self._todo, True)
            for function, args in tasks:
                function(*args)

# 辅助函数

def task_key(task):
    """返回给定 task 的排序键"""
    function, args = task
    return function.__name__, args

class Task(namedtuple('Task', ('task_function', 'args'))):
    """将对任务的调用转换为任务二元组
    
    给定一个任务函数和一个参数列表，返回一个将调用封装为单个对象的任务二元组。
    Project 使用这些任务对象来进行结果追踪和缓存。

    如果 args 不可散列，引发 ValueError。
    """
    __slots__ = ()

    def __new__(cls, task_function, args):
        try:
            hash(args)
        except TypeError as e:
            raise TypeError('arguments to project tasks must be immutable'
                            ' and hashable, not the {}'.format(e))
        
        return super().__new__(cls, task_function, args)

    def __repr__(self):
        """生成一个语法式的、类似源代码的任务表示"""
        return '{}({})'.format(self.task_function.__name__,
                                ', '.join(repr(arg) for arg in self.args))









