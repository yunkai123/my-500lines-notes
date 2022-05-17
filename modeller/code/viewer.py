from OpenGL.GL import glCallList, glClear, glClearColor, glColorMaterial, glCullFace, glDepthFunc, glDisable, glEnable,\
                      glFlush, glGetFloatv, glLightfv, glLoadIdentity, glMatrixMode, glMultMatrixf, glPopMatrix, \
                      glPushMatrix, glTranslated, glViewport, \
                      GL_AMBIENT_AND_DIFFUSE, GL_BACK, GL_CULL_FACE, GL_COLOR_BUFFER_BIT, GL_COLOR_MATERIAL, \
                      GL_DEPTH_BUFFER_BIT, GL_DEPTH_TEST, GL_FRONT_AND_BACK, GL_LESS, GL_LIGHT0, GL_LIGHTING, \
                      GL_MODELVIEW, GL_MODELVIEW_MATRIX, GL_POSITION, GL_PROJECTION, GL_SPOT_DIRECTION
from OpenGL.constants import GLfloat_3, GLfloat_4
from OpenGL.GLU import gluPerspective, gluUnProject
from OpenGL.GLUT import glutCreateWindow, glutDisplayFunc, glutGet, glutInit, glutInitDisplayMode, \
                        glutInitWindowSize, glutMainLoop, \
                        GLUT_SINGLE, GLUT_RGB, GLUT_WINDOW_HEIGHT, GLUT_WINDOW_WIDTH

import numpy
from numpy.linalg import norm, inv

from interaction import Interaction
from primitive import init_primitives, G_OBJ_PLANE
from node import Sphere, Cube, SnowFigure
from scene import Scene

class Viewer(object):
    def __init__(self):
        """ 初始化viewer """
        self.init_interface()
        self.init_opengl()
        self.init_scene()
        self.init_interaction()
        init_primitives()

    def init_interface(self):
        """ 初始化窗口并注册渲染函数 """
        glutInit()
        glutInitWindowSize(640, 480)
        glutCreateWindow("3D Modeller")
        glutInitDisplayMode(GLUT_SINGLE | GLUT_RGB)
        glutDisplayFunc(self.render)

    def init_opengl(self):
        """ 初始化opengl设置以渲染场景 """
        self.inverseModelView = numpy.identity(4)
        self.modelView = numpy.identity(4)

        glEnable(GL_CULL_FACE) # 根据函数glCullFace要求启用隐藏图形材料的面。
        glCullFace(GL_BACK)
        glEnable(GL_DEPTH_TEST) # 启用深度测试。
        glDepthFunc(GL_LESS)

        glEnable(GL_LIGHT0) # 启用 0 号灯（光源）
        glLightfv(GL_LIGHT0, GL_POSITION, GLfloat_4(0, 0, 1, 0))
        glLightfv(GL_LIGHT0, GL_SPOT_DIRECTION, GLfloat_3(0, 0, -1))

        glEnable(GL_COLOR_MATERIAL) # 执行后，图形（材料）将根据光线的照耀进行反射。
        glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)        
        glClearColor(0.4, 0.4, 0.4, 0.0) # 设置清除背景的颜色

    def init_scene(self):
        """ 初始化场景对象和初始场景 """
        self.scene = Scene()
        self.create_sample_scene()

    def create_sample_scene(self):
        # 创建几个示例图形
        cube_node = Cube() # 正方体
        cube_node.translate(2, 0, 2)
        cube_node.color_index = 1
        self.scene.add_node(cube_node)

        sphere_node = Sphere() # 球体
        sphere_node.translate(-2, 0, 2)
        sphere_node.color_index = 3
        self.scene.add_node(sphere_node)

        hierarchical_node = SnowFigure() # 雪人
        hierarchical_node.translate(-2, 0, -2)
        self.scene.add_node(hierarchical_node)

    def init_interaction(self):
        """ 初始化用户交互和回调 """
        self.interaction = Interaction()
        self.interaction.register_callback('pick', self.pick)
        self.interaction.register_callback('move', self.move)
        self.interaction.register_callback('place', self.place)
        self.interaction.register_callback('rotate_color', self.rotate_color)
        self.interaction.register_callback('scale', self.scale)

    def main_loop(self):
        glutMainLoop()

    def render(self):
        """ 场景的渲染过程 """
        self.init_view()

        glEnable(GL_LIGHTING)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        # 从轨迹球的当前状态加载 modelview 矩阵
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        loc = self.interaction.translation
        glTranslated(loc[0], loc[1], loc[2])
        glMultMatrixf(self.interaction.trackball.matrix)

        # 存储当前模型视图的相反视图
        currentModelView = numpy.array(glGetFloatv(GL_MODELVIEW_MATRIX))
        self.modelView = numpy.transpose(currentModelView)
        self.inverseModelView = inv(numpy.transpose(currentModelView))

        # 渲染场景。这将为场景中的每个对象调用渲染函数
        self.scene.render()

        # 绘制表格
        glDisable(GL_LIGHTING)
        glCallList(G_OBJ_PLANE)
        glPopMatrix()

        # 刷新缓冲区以便可以绘制场景
        glFlush()

    def init_view(self):
        """ 初始化投影矩阵 """
        xSize, ySize = glutGet(GLUT_WINDOW_WIDTH), glutGet(GLUT_WINDOW_HEIGHT)
        aspect_ratio = float(xSize) / float(ySize)

        # 加载投影矩阵，它永远不会变化
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()

        glViewport(0, 0, xSize, ySize)
        gluPerspective(70, aspect_ratio, 0.1, 1000.0)
        glTranslated(0, 0, -15)

    def get_ray(self, x, y):
        """ 生成一条从附近平面开始，指向x y坐标面向方向的射线
            参数 x, y：屏幕上鼠标的x，y坐标
            返回： 射线的 start, direcion 
        """
        self.init_view()
        
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()

        # 获取线上的两个点
        start = numpy.array(gluUnProject(x, y, 0.001))
        end = numpy.array(gluUnProject(x, y, 0.999))

        # 将这些点转换为射线
        direction = end - start
        direction = direction / norm(direction)

        return (start, direction)

    def pick(self, x, y):
        """ 对一个对象执行 pick 操作。选择场景中的一个对象 """
        start, direction = self.get_ray(x, y)
        self.scene.pick(start, direction, self.modelView)

    def place(self, shape, x, y):
        """ 执行place，将一个基本体放置到场景中 """
        start, direction = self.get_ray(x, y)
        self.scene.place(shape, start, direction, self.inverseModelView)

    def move(self, x, y):
        """ 执行移动命令 """
        start, direction = self.get_ray(x, y)
        self.scene.move_selected(start, direction, self.inverseModelView)

    def rotate_color(self, forward):
        """ 改变选定节点的颜色。布尔值 forward 表示改变方向。 """
        self.scene.rotate_selected_color(forward)

    def scale(self, up):
        """ 缩放选定节点，布尔值 up 表示放大"""
        self.scene.scale_selected(up)

if __name__ == '__main__':
    viewer = Viewer()
    viewer.main_loop()

