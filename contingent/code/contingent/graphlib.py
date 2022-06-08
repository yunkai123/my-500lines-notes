"""任务有向图，任务之间彼此作为输入"""

from collections import defaultdict

class Graph:
    """构建任务之间关系的有向图

    任务可以由符合条件的任何哈希值标识充当 Python 字典的键，
    对于图无法确定输出顺序的任务，如果用户有优先顺序，他们可
    以设置 Graph 实例的 sort_key 属性到一个 sorted() 键函
    数中。
    """
    sort_key = None

    def __init__(self):
        self._inputs_of = defaultdict(set)
        self._consequences_of = defaultdict(set)

    def sorted(self, nodes, reverse=False):
        """尝试对 nodes 进行排序，否则以迭代顺序返回它们。

        返回任务列表但不关心它们的顺序的图方法可以使用此方法
        强制使用用户选择的顺序。此方法尝试使用图的 sort_key
        函数对给定的 nodes 进行排序。如果排序不成功，则返回
        节点的自然迭代顺序。
        """
        nodes = list(nodes) # 转换为列表
        try:
            nodes.sort(key=self.sort_key, reverse=reverse)
        except TypeError:
            pass
        return nodes

    def add_edge(self, input_task, consequence_task):
        """添加一条边：consequence_task，使用 input_task 的输出。"""
        self._consequences_of[input_task].add(consequence_task)
        self._inputs_of[consequence_task].add(input_task)

    def remove_edge(self, input_task, consequence_task):
        """移除边"""
        self._consequences_of[input_task].remove(consequence_task)
        self._inputs_of[consequence_task].remove(input_task)

    def inputs_of(self, task):
        """返回为 task 的输入的任务"""
        return self.sorted(self._inputs_of[task])

    def clear_inputs_of(self, task):
        """从前面的输入中删除指向 task 的所有边"""
        input_tasks = self._inputs_of.pop(task, {})
        for input_task in input_tasks:
            self._consequences_of[input_task].remove(task)

    def tasks(self):
        """返回所有任务"""
        return self.sorted(set(self._inputs_of).union(self._consequences_of))

    def edges(self):
        """以 (input_task, consequence_task) 元组的形式返回所有边"""
        return [(a, b) for a in self.sorted(self._consequences_of)
                        for b in self.sorted(self._consequences_of[a])]

    def immediate_consequences_of(self, task):
        """返回使用 task 作为输入的任务"""
        return self.sorted(self._consequences_of[task])

    def recursive_consequences_of(self, tasks, include=False):
        """返回给定 tasks 的拓扑排序结果

        返回可以被从给定的 tasks 到它们作为输入的任务的结果边访问的每个
        任务的有序列表。返回列表的顺序是为了使结果的所有输入都在它之前的
        列表中。这意味着按照给定的顺序浏览列表执行任务，任务应该会发现它
        们需要的输入（至少上次需要的）已经计算出来并可用。
        
        如果 include 为 True，那么 tasks 将被正确地排序为结果序列，否则
        它们会被省略。
        """
        def visit(task):
            visited.add(task)
            consequences = self._consequences_of[task]
            for consequence in self.sorted(consequences, reverse=True):
                if consequence not in visited:
                    yield from visit(consequence)
                    yield consequence

        def generate_consequences_backwards():
            for task in self.sorted(tasks, reverse=True):
                yield from visit(task)
                if include:
                    yield task
        visited = set()
        return list(generate_consequences_backwards())[::-1]






