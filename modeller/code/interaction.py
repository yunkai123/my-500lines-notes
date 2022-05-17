from collections import defaultdict
from OpenGL.GLUT import glutGet, glutKeyboardFunc, glutMotionFunc, glutMouseFunc, glutPassiveMotionFunc, \
                        glutPostRedisplay, glutSpecialFunc
from OpenGL.GLUT import GLUT_LEFT_BUTTON, GLUT_RIGHT_BUTTON, GLUT_MIDDLE_BUTTON, \
                        GLUT_WINDOW_HEIGHT, GLUT_WINDOW_WIDTH, \
                        GLUT_DOWN, GLUT_KEY_UP, GLUT_KEY_DOWN, GLUT_KEY_LEFT, GLUT_KEY_RIGHT
import trackball

class Interaction(object):
    """ 处理用户交互 """

    def __init__(self):
        # 当前是否按下鼠标按钮
        self.pressed = None
        # 相机的当前位置
        self.translation = [0, 0, 0, 0]
        # 计算旋转的轨迹球
        self.trackball = trackball.Trackball(theta = -25, distance=15)
        # 当前鼠标位置
        self.mouse_loc = None
        # 简单回调机制
        self.callbacks = defaultdict(list)

        self.register()

    def register(self):
        """ 使用 gult 注册回调 """
        glutMouseFunc(self.handle_mouse_button)
        glutMotionFunc(self.handle_mouse_move)
        glutKeyboardFunc(self.handle_keystroke)
        glutSpecialFunc(self.handle_keystroke)

    def register_callback(self, name, func):
        """为某个事件注册回调"""
        self.callbacks[name].append(func)

    def trigger(self, name, *args, **kwargs):
        """调用回调，转发参数"""
        for func in self.callbacks[name]:
            func(*args, **kwargs)

    def translate(self, x, y, z):
        """ 平移相机 """
        self.translation[0] += x
        self.translation[1] += y
        self.translation[2] += z

    def handle_mouse_button(self, button, mode, x, y):
        """ 按下或者释放鼠标时调用 """
        xSize, ySize = glutGet(GLUT_WINDOW_WIDTH), glutGet(GLUT_WINDOW_HEIGHT)
        y = ySize - y # 因为 OpenGL 已经反转，反转y坐标
        self.mouse_loc = (x, y)

        if mode == GLUT_DOWN:
            self.pressed = button
            if button == GLUT_RIGHT_BUTTON:
                pass
            elif button == GLUT_LEFT_BUTTON:
                self.trigger('pick', x, y)
            elif button == 3: # 向上滚动
                self.translate(0, 0, 1.0)
            elif button == 4: # 向下滚动
                self.translate(0, 0, -1.0)
        else: # 释放鼠标
            self.pressed = None
        glutPostRedisplay()

    def handle_mouse_move(self, x, screen_y):
        """ 鼠标移动时调用 """
        xSize, ySize = glutGet(GLUT_WINDOW_WIDTH), glutGet(GLUT_WINDOW_HEIGHT)
        y = ySize - screen_y # 因为 OpenGL 已经反转，反转y坐标
        if self.pressed is not None:
            dx = x - self.mouse_loc[0]
            dy = y - self.mouse_loc[1]
            if self.pressed == GLUT_RIGHT_BUTTON and self.trackball is not None:
                # 忽略更新的相机位置，因为我们希望始终围绕原点旋转
                self.trackball.drag_to(self.mouse_loc[0], self.mouse_loc[1], dx, dy)
            elif self.pressed == GLUT_LEFT_BUTTON:
                self.trigger('move', x, y)
            elif self.pressed == GLUT_MIDDLE_BUTTON:
                self.translate(dx / 60.0, dy / 60.0, 0)
            else:
                pass
            glutPostRedisplay()
        self.mouse_loc = (x, y)

    def handle_keystroke(self, key, x, screen_y):
        """ 用户通过键盘输入时调用 """
        xSize, ySize = glutGet(GLUT_WINDOW_WIDTH), glutGet(GLUT_WINDOW_HEIGHT)
        y = ySize - screen_y
        if key == b's': # 这里注意 Python3 中 str 是 unicode，需要加 b 表示 byte
            self.trigger('place', 'sphere', x, y)
        elif key == b'c':
            self.trigger('place', 'cube', x, y)
        elif key == b'f':
            self.trigger('place', 'figure', x, y)
        elif key == GLUT_KEY_UP:
            self.trigger('scale', up=True)
        elif key == GLUT_KEY_DOWN:
            self.trigger('scale', up=False)
        elif key == GLUT_KEY_LEFT:
            self.trigger('rotate_color', forward=True)
        elif key == GLUT_KEY_RIGHT:
            self.trigger('rotate_color', forward=False)
        glutPostRedisplay()
