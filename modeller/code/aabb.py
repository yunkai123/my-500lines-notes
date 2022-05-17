from OpenGL.GL import glCallList, glMatrixMode, glPolygonMode, glPopMatrix, glPushMatrix, glTranslated, \
                      GL_FILL, GL_FRONT_AND_BACK, GL_LINE, GL_MODELVIEW

from primitive import G_OBJ_CUBE
import numpy
import math

EPSILON = 0.000001


class AABB(object):

    def __init__(self, center, size):
        """ 轴对齐的边界框。
        这是一个与模型坐标空间的XYZ轴对齐的框。
        它用于光线的碰撞检测，用来选择光线。
        它还可以用于节点之间的基本碰撞检测。"""
        self.center = numpy.array(center)
        self.size = numpy.array(size)

    def scale(self, scale):
        self.size = scale

    def ray_hit(self, origin, direction, modelmatrix):
        """ 返回Ture <=> 光线击中 AABB
            参数：origin, direction -> 描述光线
                 modelmatrix -> 要从光线坐标空间转换到 AABB 坐标空间的矩阵"""
        aabb_min = self.center - self.size
        aabb_max = self.center + self.size
        tmin = 0.0
        tmax = 100000.0
        obb_pos_worldspace = numpy.array([modelmatrix[0, 3], modelmatrix[1, 3], modelmatrix[2, 3]])
        delta = (obb_pos_worldspace - origin)

        # 测试两个垂直于OBB x轴的平面的交点
        xaxis = numpy.array((modelmatrix[0, 0], modelmatrix[0, 1], modelmatrix[0, 2]))

        e = numpy.dot(xaxis, delta)
        f = numpy.dot(direction, xaxis)
        if math.fabs(f) > 0.0 + EPSILON:
            t1 = (e + aabb_min[0]) / f
            t2 = (e + aabb_max[0]) / f
            if t1 > t2:
                t1, t2 = t2, t1
            if t2 < tmax:
                tmax = t2
            if t1 > tmin:
                tmin = t1
            if tmax < tmin:
                return (False, 0)
        else:
            if(-e + aabb_min[0] > 0.0 + EPSILON) or (-e + aabb_max[0] < 0.0 - EPSILON):
                return False, 0

        # y 轴相交
        yaxis = numpy.array((modelmatrix[1, 0], modelmatrix[1, 1], modelmatrix[1, 2]))
        e = numpy.dot(yaxis, delta)
        f = numpy.dot(direction, yaxis)
        if math.fabs(f) > 0.0 + EPSILON:
            t1 = (e + aabb_min[1]) / f
            t2 = (e + aabb_max[1]) / f
            if t1 > t2:
                t1, t2 = t2, t1
            if t2 < tmax:
                tmax = t2
            if t1 > tmin:
                tmin = t1
            if tmax < tmin:
                return (False, 0)
        else:
            if(-e + aabb_min[0] > 0.0 + EPSILON) or (-e + aabb_max[0] < 0.0 - EPSILON):
                return False, 0

        # z 轴相交
        zaxis = numpy.array((modelmatrix[2, 0], modelmatrix[2, 1], modelmatrix[2, 2]))
        e = numpy.dot(zaxis, delta)
        f = numpy.dot(direction, zaxis)
        if math.fabs(f) > 0.0 + EPSILON:
            t1 = (e + aabb_min[2]) / f
            t2 = (e + aabb_max[2]) / f
            if t1 > t2:
                t1, t2 = t2, t1
            if t2 < tmax:
                tmax = t2
            if t1 > tmin:
                tmin = t1
            if tmax < tmin:
                return (False, 0)
        else:
            if(-e + aabb_min[0] > 0.0 + EPSILON) or (-e + aabb_max[0] < 0.0 - EPSILON):
                return False, 0
        
        return True, tmin

    def render(self):
        """渲染 AABB，这对于调试非常有用"""
        glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glTranslated(self.center[0], self.center[1], self.center[2])
        glCallList(G_OBJ_CUBE)
        glPopMatrix()
        glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)

                             