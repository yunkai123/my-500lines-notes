import sys
import numpy
from node import Sphere, Cube, SnowFigure

class Scene(object):

    # 从相机到放置对象的默认深度
    PLACE_DEPTH = 15.0

    def __init__(self):
        # 场景中显示的节点
        self.node_list = list()
        # 跟踪当前选定的节点。
        # 操作可能取决于是否选择了某个对象
        self.selected_node = None

    def add_node(self, node):
        """ 添加一个节点到场景中 """
        self.node_list.append(node)

    def render(self):
        """ 渲染场景。此函数只需为每个节点调用render函数。"""
        for node in self.node_list:
            node.render()

    def pick(self, start, direction, mat):
        """
        执行选择
        参数：  start, direction: 描述光线
               mat: 场景当前矩阵的反转
        """
        if self.selected_node is not None:
            self.selected_node.select(False)
            self.selected_node = None

        # 跟踪最近的命中
        mindist = sys.maxsize # Python3 中改为 maxsize
        closest_node = None
        for node in self.node_list:
            hit, distance = node.pick(start, direction, mat)
            if hit and distance < mindist:
                mindist, closest_node = distance, node

        # 如果命中什么，就追踪它
        if closest_node is not None:
            closest_node.select()
            closest_node.depth = mindist
            closest_node.selected_loc = start + direction * mindist
            self.selected_node = closest_node

    def move_selected(self, start, direction, inv_modelview):
        """
        如果有选中节点，移动它

        参数：  start, direction: 描述光线
               inv_modelview: 场景当前矩阵的反转
        """
        if self.selected_node is None:
            return

        # 获取选中节点的当前深度和位置
        node = self.selected_node
        depth = node.depth
        oldloc = node.selected_loc

        # 节点的新位置与新光线的深度相同
        newloc = (start + direction * depth)

        # 使用modelview矩阵进行转换
        translation = newloc - oldloc
        pre_tran = numpy.array([translation[0], translation[1], translation[2], 0])
        translation = inv_modelview.dot(pre_tran)

        # 平移节点并追踪其位置
        node.translate(translation[0], translation[1], translation[2])
        node.selected_loc = newloc

    def place(self, shape, start, direction, inv_modelview):
        """
        放置新节点
        
        参数：  shape: 要添加的形状
               start, direction: 描述光线
               inv_modelview: 场景当前矩阵的反转
        """
        new_node = None
        if shape == 'sphere':
            new_node = Sphere()
        elif shape == 'cube':
            new_node = Cube()
        elif shape == 'figure':
            new_node = SnowFigure()

        self.add_node(new_node)

        # 将节点放置在相机空间中的光标处
        translation = (start + direction * self.PLACE_DEPTH)

        # 将 translation 转换为世界空间
        pre_tran = numpy.array([translation[0], translation[1], translation[2], 1])
        translation = inv_modelview.dot(pre_tran)

        new_node.translate(translation[0], translation[1], translation[2])

    def rotate_selected_color(self, forwards):
        """ 旋转当前选定节点的颜色 """
        if self.selected_node is None:
            return
        self.selected_node.rotate_color(forwards)

    def scale_selected(self, up):
        """ 缩放当前选择节点 """
        if self.selected_node is None:
            return
        self.selected_node.scale(up)

