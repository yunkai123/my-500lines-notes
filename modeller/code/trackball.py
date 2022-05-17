__docformat__ = 'restructuredtext'
__version__ = '1.0'

import math
import OpenGL.GL as gl
from OpenGL.GL import GLfloat

# 关于向量的一些辅助函数
# -----------------------------------------------------------------------------
def _v_add(v1, v2):
    return [v1[0] + v2[0], v1[1] + v2[1], v1[2] + v2[2]]
def _v_sub(v1, v2):
    return [v1[0] - v2[0], v1[1] - v2[1], v2[2] - v2[2]]
def _v_mul(v, s):
    return [v[0] * s, v[1] * s, v[2] * s]
def _v_dot(v1, v2):
    return v1[0] * v2[0] + v1[1] * v2[1] + v1[2] * v2[2]
def _v_cross(v1, v2):
    return [(v1[1] * v2[2]) - (v1[2] * v2[1]),
            (v1[2] * v2[0]) - (v1[0] * v2[2]),
            (v1[0] * v2[1]) - (v1[1] * v2[0])]
def _v_length(v):
    return math.sqrt(_v_dot(v, v))
def _v_normalize(v):
    try:
        return _v_mul(v, 1.0 / _v_length(v))
    except ZeroDivisionError:
        return v

# 关于四元数的一些辅助函数
# -----------------------------------------------------------------------------
def _q_add(q1, q2):
    t1 = _v_mul(q1, q2[3])
    t2 = _v_mul(q2, q1[3])
    t3 = _v_cross(q2, q1)
    tf = _v_add(t1, t2)
    tf = _v_add(t3, tf)
    tf.append(q1[3] * q2[3] - _v_dot(q1, q2))
    return tf
def _q_mul(q, s):
    return [q[0] * s, q[1] * s, q[2] * s, q[3] * s]
def _q_dot(q1, q2):
    return q1[0] * q2[0] + q1[1] * q2[1] + q1[2] * q2[2] + q1[3] * q2[3]
def _q_length(q):
    return math.sqrt(_q_dot(q, q))
def _q_normalize(q):
    try:
        return _q_mul(q, 1.0 / _q_length(q))
    except ZeroDivisionError:
        return q
def _q_from_axis_angle(v, phi):
    q = _v_mul(_v_normalize(v), math.sin(phi / 2.0))
    q.append(math.cos(phi / 2.0))
    return q
def _q_rotmatrix(q):
    m = [0.0] * 16
    m[0*4+0] = 1.0 - 2.0*(q[1]*q[1] + q[2]*q[2])
    m[0*4+1] = 2.0 * (q[0]*q[1] - q[2]*q[3])
    m[0*4+2] = 2.0 * (q[2]*q[0] + q[1]*q[3])
    m[0*4+3] = 0.0
    m[1*4+0] = 2.0 * (q[0]*q[1] + q[2]*q[3])
    m[1*4+1] = 1.0 - 2.0*(q[2]*q[2] + q[0]*q[0])
    m[1*4+2] = 2.0 * (q[1]*q[2] - q[0]*q[3])
    m[1*4+3] = 0.0
    m[2*4+0] = 2.0 * (q[2]*q[0] - q[1]*q[3])
    m[2*4+1] = 2.0 * (q[1]*q[2] + q[0]*q[3])
    m[2*4+2] = 1.0 - 2.0*(q[1]*q[1] + q[0]*q[0])
    m[3*4+3] = 1.0
    return m

class Trackball(object):
    """用于3D场景观看的虚拟轨迹球"""
    def __init__(self, theta=0, phi=0, zoom=1, distance=3):
        '''使用指定视图生成新轨迹球'''
        self._rotation = [0, 0, 0, 1]
        self.zoom = zoom
        self.distance = distance
        self._count = 0
        self._matrix = None
        self._RENORMCOUNT = 97
        self._TRACKBALLSIZE = 0.8
        self._set_orientation(theta, phi)
        self._x = 0.0
        self._y = 0.0

    def drag_to(self, x, y, dx, dy):
        '''将轨迹球视图从 x，y 移动到 x+dx，y+dy '''
        viewport = gl.glGetIntegerv(gl.GL_VIEWPORT)
        width, height = float(viewport[2]), float(viewport[3])
        x = (x * 2.0 - width) / width
        dx = (2. * dx) / width
        y = (y * 2.0 - height) / height
        dy = (2. * dy) / height
        q = self._rotate(x, y, dx, dy)
        self._rotation = _q_add(q, self._rotation)
        self._count += 1
        if self._count > self._RENORMCOUNT:
            self._rotation = _q_normalize(self._rotation)
            self._count = 0
        m = _q_rotmatrix(self._rotation)
        self._matrix = (GLfloat * len(m))(*m)

    def zoom_to(self, x, y, dx, dy):
        '''按因子dy缩放轨迹球'''
        viewport = gl.glGetIntegerv(gl.GL_VIEWPORT)
        height = float(viewport[3])
        self.zoom = self.zoom - 5 * dy / height
    
    def pan_to(self, x, y, dx, dy):
        '''按因子dx，dy平移轨迹球'''
        self.x += dx * 0.1
        self.y += dy * 0.1

    def push(self):
        viewport = gl.glGetIntegerv(gl.GL_VIEWPORT)
        gl.glMatrixMode(gl.GL_PROJECTION)
        gl.glPushMatrix()
        gl.glLoadIdentity ()
        aspect = viewport[2]/float(viewport[3])
        aperture = 35.0
        near = 0.1
        far = 100.0
        top = math.tan(aperture*3.14159/360.0) * near * self._zoom
        bottom = -top
        left = aspect * bottom
        right = aspect * top
        gl.glFrustum (left, right, bottom, top, near, far)
        gl.glMatrixMode (gl.GL_MODELVIEW)
        gl.glPushMatrix()
        gl.glLoadIdentity ()
        # gl.glTranslate (0.0, 0, -self._distance)
        gl.glTranslate (self._x, self._y, -self._distance)
        gl.glMultMatrixf (self._matrix)

    def pop(void):
        gl.glMatrixMode(gl.GL_MODELVIEW)
        gl.glPopMatrix()
        gl.glMatrixMode(gl.GL_PROJECTION)
        gl.glPopMatrix()

    def _get_matrix(self):
        return self._matrix
    matrix = property(_get_matrix,
                     doc='''Model view matrix transformation (read-only)''')

    def _get_zoom(self):
        return self._zoom
    def _set_zoom(self, zoom):
        self._zoom = zoom
        if self._zoom < .25: self._zoom = .25
        if self._zoom > 10: self._zoom = 10
    zoom = property(_get_zoom, _set_zoom,
                     doc='''Zoom factor''')

    def _get_distance(self):
        return self._distance
    def _set_distance(self, distance):
        self._distance = distance
        if self._distance < 1: 
            self._distance= 1
    distance = property(_get_distance, _set_distance,
                        doc='''Scene distance from point of view''')

    def _get_theta(self):
        self._theta, self._phi = self._get_orientation()
        return self._theta
    def _set_theta(self, theta):
        self._set_orientation(math.fmod(theta, 360.0),
                              math.fmod(self._phi, 360.0))
    theta = property(_get_theta, _set_theta,
                     doc='''Angle (in degrees) around the z axis''')


    def _get_phi(self):
        self._theta, self._phi = self._get_orientation()
        return self._phi
    def _set_phi(self, phi):
        self._set_orientation(math.fmod(self._theta,360.),
                              math.fmod(phi,360.0))
    phi = property(_get_phi, _set_phi,
                     doc='''Angle around x axis''')


    def _get_orientation(self):
        ''' 返回当前计算的方向 (theta,phi). ''' 

        q0,q1,q2,q3 = self._rotation
        ax = math.atan(2*(q0*q1+q2*q3)/(1-2*(q1*q1+q2*q2)))*180.0/math.pi
        az = math.atan(2*(q0*q3+q1*q2)/(1-2*(q2*q2+q3*q3)))*180.0/math.pi
        return -az,ax

    def _set_orientation(self, theta, phi):
        ''' 计算与θ和φ相对应的旋转。''' 

        self._theta = theta
        self._phi = phi
        angle = self._theta*(math.pi/180.0)
        sine = math.sin(0.5*angle)
        xrot = [1*sine, 0, 0, math.cos(0.5*angle)]
        angle = self._phi*(math.pi/180.0)
        sine = math.sin(0.5*angle)
        zrot = [0, 0, sine, math.cos(0.5*angle)]
        self._rotation = _q_add(xrot, zrot)
        m = _q_rotmatrix(self._rotation)
        self._matrix = (GLfloat*len(m))(*m)

    def _project(self, r, x, y):
        ''' 如果我们远离球体的中心，
        将x，y对投影到半径为r的球体或双曲面上
        '''

        d = math.sqrt(x*x + y*y)
        if (d < r * 0.70710678118654752440):    # 球体内
            z = math.sqrt(r*r - d*d)
        else:                                   # 在双曲线
            t = r / 1.41421356237309504880
            z = t*t / d
        return z

    def _rotate(self, x, y, dx, dy): 
        ''' 模拟轨迹球
            将这些点投射到虚拟轨迹球上，然后计算出旋转轴，它是x，y和x+dx，y+dy的叉积。
            注意：这个轨迹球是变形的，在中心是轨迹球，但离开中心后被变形成一个双曲线的旋转片。
            这个特殊的函数是在尝试了几个变体之后选择的。
        '''

        if not dx and not dy:
            return [ 0.0, 0.0, 0.0, 1.0]
        last = [x, y,       self._project(self._TRACKBALLSIZE, x, y)]
        new  = [x+dx, y+dy, self._project(self._TRACKBALLSIZE, x+dx, y+dy)]
        a = _v_cross(new, last)
        d = _v_sub(last, new)
        t = _v_length(d) / (2.0*self._TRACKBALLSIZE)
        if (t > 1.0): t = 1.0
        if (t < -1.0): t = -1.0
        phi = 2.0 * math.asin(t)
        return _q_from_axis_angle(a,phi)


    def __str__(self):
        phi = str(self.phi)
        theta = str(self.theta)
        zoom = str(self.zoom)
        return 'Trackball(phi=%s,theta=%s,zoom=%s)' % (phi,theta,zoom)

    def __repr__(self):
        phi = str(self.phi)
        theta = str(self.theta)
        zoom = str(self.zoom)
        return 'Trackball(phi=%s,theta=%s,zoom=%s)' % (phi,theta,zoom)