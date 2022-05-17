# 3D建模工具

## 作者

Erick Dransch，Erick 是一名软件开发人员以及 2D 和 3D 计算机图形爱好者。他从事过电子游戏、3D 特效软件和计算机辅助设计工具相关工作。他还了解很多模拟现实相关知识。他的网站是 ericktransch.com 。

## 简介

人类天生就有创造力。我们不断地设计和制造新颖、有用、有趣的东西。在现代，我们编写软件来辅助设计和创造过程。计算机辅助设计（CAD）软件允许创作者在构建物理版本之前设计建筑物、桥梁、视频游戏艺术、电影怪物、3D 可打印对象和许多其它东西。

其核心部分 CAD 工具是将三维设计抽象为可以在二维屏幕上查看和编辑的东西的方法。为了实现这一定义，CAD 工具必须提供三个基本功能。首先，它们必须有一个数据结构来表示正在设计的对象：这是计算机对用户正在构建的三维世界的理解。其次，CAD 工具必须提供一些方法，在用户界面上显示设计。用户正在设计一个三维物理对象，但计算机屏幕只有2个维度。CAD 工具必须对我们如何感知对象进行建模，并将其绘制到屏幕上，用户可以理解对象的所有3个维度。第三，CAD 工具必须提供一种与设计对象交互的方法。用户必须能够添加和修改设计，以产生所需的结果。此外，所有工具都需要一种方法来将设计保存到磁盘以及从磁盘中加载设计，以便用户能够协作、共享和保存工作。

特定领域的 CAD 工具为特定领域的特定需求提供了许多附加功能。例如，建筑 CAD 工具将提供物理模拟来测试建筑物上的气候压力，3D 打印工具将具有检查对象是否可以进行实际有效打印的功能，电气 CAD 工具将模拟电流通过铜的物理特性，电影特效套件将包含精确模拟热动力学的功能。

然而，所有的 CAD 工具必须至少包括上面讨论的三个特性：表示设计的数据结构、将其显示在屏幕上的能力以及与设计交互的方法。

考虑到这一点，让我们探索如何用 500 行 Python 代码来表示 3D 设计、将其显示在屏幕上并与之进行交互。

## 渲染指导

三维建模器中许多设计决策背后的驱动力是渲染过程。我们希望能够在我们的设计中存储和渲染复杂的对象，但我们希望渲染代码的复杂性较低。让我们检查渲染过程，并探索设计的数据结构，该数据结构允许我们使用简单的渲染逻辑存储和绘制任意复杂的对象。

### 管理接口和主循环

在开始渲染之前，我们需要进行一些设置。首先，我们需要创建一个窗口来显示我们的设计。其次，我们希望与图形驱动程序进行通信以渲染到屏幕上。我们不想直接与图形驱动程序通信，所以我们使用一个称为 OpenGL 的跨平台抽象层和一个名为 GLUT（the OpenGL Utility Toolkit）的库来管理我们的窗口。

#### 关于 OpenGL 的注意事项

OpenGL 是一个面向跨平台开发的图形应用程序编程接口。它是跨平台开发图形应用程序的标准 API。OpenGL 有两个主要变体：旧版 OpenGL 和现代 OpenGL。

OpenGL 中的渲染是基于由顶点和法线定义的多边形。例如，要渲染立方体的一侧，我们指定 4 个顶点和该边的法线。

旧版的 OpenGL 提供了一个“固定函数管道”。通过设置全局变量，程序员可以启用和禁用诸如照明、着色、面部剔除等功能的自动实现。然后 OpenGL 使用启用的功能自动渲染场景。此功能已弃用。

另一方面，现代 OpenGL 具有一个可编程的渲染管道，程序员可以在上面编写运行在专用图形硬件（GPU）上的名为“shaders”的小程序。现代 OpenGL 的可编程管道已经取代了旧版的 OpenGL。

在这个项目中，尽管旧版 OpenGL 已被弃用，我们仍然使用它。因为它提供的固定功能可以保持代码较少。它减少了所需的线性代数知识量，并简化了我们将要编写的代码。

#### 关于 GLUT

GLUT 与 OpenGL 捆绑在一起，允许我们创建操作系统窗口并注册用户界面回调。此基本功能足以满足我们的目的。如果我们想要一个功能更全的用于窗口管理和用户交互的库，我们可以考虑使用 GTK 或 Qt 这样的完整窗口工具集。

#### Viewer

为了管理 GLUT 和 OpenGL 的设置，并驱动 modeller 的其余部分，我们创建了一个名为 `Viewer` 的类。我们使用单一 `Viewer` 实例，它管理窗口的创建和渲染，并包含程序的主循环。在 `Viewer` 的初始化过程中，我们创建 GUI 窗口并初始化 OpenGL。

函数 `init_interface` 创建用于渲染建模的窗口，并指定渲染设计时要调用的函数。`init_opengl` 函数设置项目所需的 OpenGL 状态。它设置矩阵，启用背面剔除，注册灯光来照亮场景，并告诉 OpenGL 我们希望对对象进行着色。`init_scene` 函数创建 `Scene` 对象，并放置一些初始节点，以方便用户开始。稍后我们将看到更多关于 `Scene` 数据结构的信息。最后，`init_interaction` 注册用于用户交互的回调，我们将在后面讨论。

初始化 `Viewer` 后，我们调用 `glutMainLoop` 将程序执行转移到 GLUT。此函数永不返回。我们在 GLUT 事件上注册的回调将在这些事件发生时调用。

```py
class Viewer(object):
    def __init__(self):
        """ 初始化viewer. """
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

        glEnable(GL_CULL_FACE)
        glCullFace(GL_BACK)
        glEnable(GL_DEPTH_TEST)
        glDepthFunc(GL_LESS)

        glEnable(GL_LIGHT0)
        glLightfv(GL_LIGHT0, GL_POSITION, GLfloat_4(0, 0, 1, 0))
        glLightfv(GL_LIGHT0, GL_SPOT_DIRECTION, GLfloat_3(0, 0, -1))

        glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)
        glEnable(GL_COLOR_MATERIAL)
        glClearColor(0.4, 0.4, 0.4, 0.0)

    def init_scene(self):
        """ 初始化场景对象和初始场景 """
        self.scene = Scene()
        self.create_sample_scene()

    def create_sample_scene(self):
        cube_node = Cube()
        cube_node.translate(2, 0, 2)
        cube_node.color_index = 2
        self.scene.add_node(cube_node)

        sphere_node = Sphere()
        sphere_node.translate(-2, 0, 2)
        sphere_node.color_index = 3
        self.scene.add_node(sphere_node)

        hierarchical_node = SnowFigure()
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

if __name__ == "__main__":
    viewer = Viewer()
    viewer.main_loop()
```

在深入研究渲染函数之前，我们应该先讨论一下线性代数。

### 坐标空间

对于我们的场景，坐标空间是一个原点和 3 个基向量的集合，通常是$x$，$y$和$z$轴。

### 点

三维中的任何点都可以表示为距原点在$x$、$y$和$z$方向上的偏移量。点的表示与该点所在的坐标空间有关。同一点在不同的坐标空间有不同的表示。三维空间中的任何点都可以在任何三维坐标空间中表示。

### 向量

向量是一个$x$、$y$和$z$值，表示在$x$、$y$和$z$轴上两点之间的差。

### 变换矩阵

在计算机图形学中，为不同类型的点使用多个不同的坐标空间是很方便的。变换矩阵将点从一个坐标空间转换到另一个坐标空间。为了将向量$v$从一个坐标空间转换到另一个坐标空间，我们用变换矩阵 $M$: $v' = M v$ 相乘。常见的变换矩阵是平移、缩放和旋转。

### 模型、世界、视图和投影坐标空间

![](/modeller/markdown/img/newtranspipe.png)

要在屏幕上绘制项目，我们需要在几个不同的坐标空间之间进行转换。

上图的右侧[^transimage]，包括从眼睛空间（ Eye Space）到视口空间（ Viewport Space）的所有转换都将由 OpenGL 处理。

[^transimage]:感谢 Anton Gerdelan 博士的图。他的 OpenGL 教程可以在 http://antongerdelan.net/opengl/ 获取。

从眼睛空间到齐次裁剪空间(homogeneous clip space)的转换由 `gluPerspective` 处理，向标准化设备空间和视口空间的转换由 `glViewport` 处理。将这两个矩阵相乘并存储为 GL_PROJECTION 矩阵。我们不需要了解这些矩阵在项目中的工作细节和原理。

但是，图的左侧需要我们自己管理。我们定义了一个矩阵，它将模型中的点（也称为网格）从模型空间转换为世界空间，称为模型矩阵。我们还定义了视图矩阵，用于从世界空间到眼睛空间的视转换。在本项目中，我们将这两个矩阵结合起来以获得 ModelView 矩阵。

要了解有关完整图形渲染管道以及涉及的坐标空间的更多信息，请参阅《Real Time Rendering》的第 2 章，或其它的计算机图形学入门书籍。

### 使用 Viewer 渲染

`render` 函数从设置需要在渲染时完成的 OpenGL 状态开始。 它通过 `init_view` 初始化投影矩阵，并使用来自交互成员的数据和转换矩阵初始化 ModelView 矩阵，该转换矩阵将场景空间转换为世界空间。我们将在下面看到有关`Interaction` 类的更多信息。它使用 `glClear` 清除屏幕，并告诉场景渲染自身，然后渲染单位网格。

我们在渲染网格之前禁用 OpenGL 的灯光。禁用灯光后，OpenGL 将使用纯色渲染项目，而不是模拟光源。这样，网格与场景有视觉上的区别。最后，`glFlush` 向图形驱动程序发出信号，表明我们已经准备好刷新缓冲区并显示到屏幕上。

```py
    # class Viewer
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
```

### 渲染对象：场景

既然我们已经初始化了渲染管道来处理世界坐标空间中的绘图，那么我们要渲染什么呢？回想一下，我们的目标是有一个由 3D 模型组成的设计。我们需要一个数据结构来包含设计，并且我们需要使用这个数据结构来渲染设计。注意上面我们从 viewer 的渲染循环调用 `self.scene.render()`。scene 是什么？

`Scene` 类是我们用来表示设计的数据结构的接口。它抽象出数据结构的细节，并提供与设计交互所需的必要接口函数，包括渲染、添加项和操作项的函数。viewer 中有一个 `Scene` 对象。`Scene` 实例保留场景中所有项的列表，称为 `node_list`。它还可以跟踪所选项。场景中的 `render` 函数只需对 `node_list` 的每个成员调用 `render`。

```py
class Scene(object):

    # 从相机到放置对象的默认深度
    PLACE_DEPTH = 15.0

    def __init__(self):
        # 场景中显示的节点
        self.node_list = list()
        # 跟踪当前选定的节点。
        # 操作可能取决于是否有对象被选中
        self.selected_node = None

    def add_node(self, node):
        """ 添加一个节点到场景中 """
        self.node_list.append(node)

    def render(self):
        """ 渲染场景。此函数只需为每个节点调用render函数。 """
        for node in self.node_list:
            node.render()
```

### Node类

在 Scene 的 `render` 函数中，我们对 Scene 的 `node_list` 中的每个项调用 `render`。但是，该列表中是什么？我们称它们为节点。从概念上讲，节点是可以放置在场景中的任何东西。在面向对象的软件中，我们将 `Node` 编写为抽象基类。任何表示要放置在场景中的对象的类都将从 `Node` 继承。这个基类使我们可以抽象地推断场景。代码的其余部分不需要了解其显示的对象的详细信息；它只需要知道它们属于 `Node` 类即可。

每种类型的 `Node` 都定义了自己的行为，用于渲染自身和进行其他交互。`Node` 跟踪有关其自身的重要数据：变换矩阵，比例矩阵，颜色等。将节点的变换矩阵与其比例矩阵相乘即可得到从节点的模型坐标空间到世界坐标空间的变换矩阵。该 `Node` 还存储轴对齐的边界框（AABB）。 当我们在下面讨论选择时，我们将看到更多有关 AABB 的信息。

`Node`最简单的具体实现是一个图元。图元是可以添加到场景中的单个实体形状。在这个项目中，图元是 `Cube`和 `Sphere`。

```py
class Node(object):
    """ 场景元素的基类 """
    def __init__(self):
        self.color_index = random.randint(color.MIN_COLOR, color.MAX_COLOR)
        self.aabb = AABB([0.0, 0.0, 0.0], [0.5, 0.5, 0.5])
        self.translation_matrix = numpy.identity(4)
        self.scaling_matrix = numpy.identity(4)
        self.selected = False

    def render(self):
        """ 将项渲染到场景中 """
        glPushMatrix()
        glMultMatrixf(numpy.transpose(self.translation_matrix))
        glMultMatrixf(self.scaling_matrix)
        cur_color = color.COLORS[self.color_index]
        glColor3f(cur_color[0], cur_color[1], cur_color[2])
        if self.selected:  # emit light if the node is selected
            glMaterialfv(GL_FRONT, GL_EMISSION, [0.3, 0.3, 0.3])
        
        self.render_self()

        if self.selected:
            glMaterialfv(GL_FRONT, GL_EMISSION, [0.0, 0.0, 0.0])
        glPopMatrix()

    def render_self(self):
        raise NotImplementedError(
            "The Abstract Node Class doesn't define 'render_self'")

class Primitive(Node):
    def __init__(self):
        super(Primitive, self).__init__()
        self.call_list = None

    def render_self(self):
        glCallList(self.call_list)


class Sphere(Primitive):
    """ 球体 """
    def __init__(self):
        super(Sphere, self).__init__()
        self.call_list = G_OBJ_SPHERE


class Cube(Primitive):
    """ 立方体 """
    def __init__(self):
        super(Cube, self).__init__()
        self.call_list = G_OBJ_CUBE
```

渲染节点基于每个节点存储的变换矩阵。节点的变换矩阵是其缩放矩阵和平移矩阵的组合。无论节点的类型如何，渲染的第一步是将 OpenGL 的 ModelView 矩阵设置为变换矩阵，以便从模型坐标空间转换到视图坐标空间。一旦 OpenGL 矩阵更新，我们调用 `render_self` 来告诉节点进行必要的 OpenGL 调用来绘制自己。最后，我们撤消对这个特定节点的 OpenGL 状态所做的任何更改。我们使用 OpenGL 中的 `glPushMatrix` 和 `glPopMatrix` 函数来保存和恢复渲染节点前后 ModelView 矩阵的状态。请注意，节点存储其颜色、位置和比例，并在渲染之前将这些应用于 OpenGL 状态。

如果节点当前处于选中状态，则使其发光。这样，用户就可以直观地看到他们选择了哪个节点。

为了渲染图元，我们使用了 OpenGL 的调用列表功能。OpenGL 调用列表是一系列 OpenGL 调用，这些调用一次定义并绑定到单个名称下并可以使用 `glCallList(LIST_NAME)` 调度。每个图元（Sphere 和 Cube）都定义了渲染它所需的调用列表（未显示）。

例如，立方体的调用列表绘制立方体的 6 个面，中心位于原点，边正好 1 个单位长。

```py
# Pseudocode Cube definition
# Left face
((-0.5, -0.5, -0.5), (-0.5, -0.5, 0.5), (-0.5, 0.5, 0.5), (-0.5, 0.5, -0.5)),
# Back face
((-0.5, -0.5, -0.5), (-0.5, 0.5, -0.5), (0.5, 0.5, -0.5), (0.5, -0.5, -0.5)),
# Right face
((0.5, -0.5, -0.5), (0.5, 0.5, -0.5), (0.5, 0.5, 0.5), (0.5, -0.5, 0.5)),
# Front face
((-0.5, -0.5, 0.5), (0.5, -0.5, 0.5), (0.5, 0.5, 0.5), (-0.5, 0.5, 0.5)),
# Bottom face
((-0.5, -0.5, 0.5), (-0.5, -0.5, -0.5), (0.5, -0.5, -0.5), (0.5, -0.5, 0.5)),
# Top face
((-0.5, 0.5, -0.5), (-0.5, 0.5, 0.5), (0.5, 0.5, 0.5), (0.5, 0.5, -0.5))
```

对于建模应用程序来说，只使用图元是相当有限的。3D 模型通常由多个图元（或三角网格，这不在本项目的范围之内）组成。幸运的是，我们设计的 `Node` 类有助于实现由多个图元组成的 `Scene` 节点。事实上，我们可以在不增加复杂性的情况下支持任意的节点分组。

让我们考虑一个非常基本的图形：一个典型的雪人，由三个球体组成。即使图形由三个独立的图元组成，我们还是希望能够将其作为单个对象来处理。

我们创建一个名为 `HierarchicalNode` 的类，一个包含其他节点的节点类。它管理一个“孩子”列表。多层节点的`render_self` 函数只在每个子节点上调用 `render_self`。使用 `HierarchicalNode` 类，可以很容易地将图形添加到场景中。现在，定义雪人的形状就像指定组成它的形状，以及它们的相对位置和大小一样简单。

![](/modeller/markdown/img/nodes.jpg)

```py
class HierarchicalNode(Node):
    def __init__(self):
        super(HierarchicalNode, self).__init__()
        self.child_nodes = []

    def render_self(self):
        for child in self.child_nodes:
            child.render()
```

```py
class SnowFigure(HierarchicalNode):
    def __init__(self):
        super(SnowFigure, self).__init__()
        self.child_nodes = [Sphere(), Sphere(), Sphere()]
        self.child_nodes[0].translate(0, -0.6, 0) # scale 1.0
        self.child_nodes[1].translate(0, 0.1, 0)
        self.child_nodes[1].scaling_matrix = numpy.dot(
            self.scaling_matrix, scaling([0.8, 0.8, 0.8]))
        self.child_nodes[2].translate(0, 0.75, 0)
        self.child_nodes[2].scaling_matrix = numpy.dot(
            self.scaling_matrix, scaling([0.7, 0.7, 0.7]))
        for child_node in self.child_nodes:
            child_node.color_index = color.MIN_COLOR
        self.aabb = AABB([0.0, 0.0, 0.0], [0.5, 1.1, 0.5])
```

你可能注意到 `Node` 对象形成了一个树型数据结构。`render` 函数通过层次节点在树中执行深度优先遍历。当它遍历时，它保留一堆 ModelView 矩阵，用于转换到世界空间。在每一步，它将当前的 ModelView 矩阵推送到堆栈上，当它完成所有子节点的渲染时，它将矩阵从堆栈中弹出，而父节点的 ModelView 矩阵留在堆栈的顶部。

通过使 `Node` 类以这种方式可扩展，我们可以向场景中添加新的形状类型，而无需更改任何其他用于场景操作和渲染的代码。使用节点概念来抽象一个场景对象可能有许多子对象这一事实被称为“复合设计模式”。

### 用户交互

我们的 modeller 已经能够存储和显示场景，我们还需要一种与之交互的方式。我们需要促进两种类型的互动。首先，我们需要改变场景视角的能力。我们希望能够在场景周围移动眼睛或相机。其次，我们需要能够添加新的节点和修改场景中的节点。

要实现用户交互，我们需要知道用户何时按下键或移动鼠标。幸运的是，操作系统已经知道这些事件何时发生。GLUT 允许我们注册一个函数，以便在某个事件发生时调用它。我们编写了解释按键和鼠标移动的函数，并告诉 GLUT 在按下相应键时调用这些函数。一旦我们知道用户按的是哪个键，我们就需要解释输入并将预期的动作应用到场景中。

在 `Interaction` 类中可以找到监听操作系统事件并解释其含义的逻辑。我们之前编写的 `Viewer` 类拥有 `Interaction` 的单个实例。 我们将使用 GLUT 回调机制来注册当按下鼠标按钮（`glutMouseFunc`），移动鼠标（`glutMotionFunc`），按下键盘按钮（`glutKeyboardFunc`）以及按下箭头键（ `glutSpecialFunc`）时要调用的函数。 稍后我们会看到处理输入事件的函数。

```py
class Interaction(object):
    def __init__(self):
        """ 处理用户交互 """
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
```

#### 操作系统回调

为了解释用户输入，我们需要结合鼠标位置、鼠标按钮和键盘的知识。因为将用户输入解释为有意义的操作需要许多行代码，所以我们将其封装在一个独立的类中，远离主代码路径。`Interaction` 类对代码库的其余部分隐藏不相关的复杂性，并将操作系统事件转换为应用程序级事件。

```py
# Interaction 类
    def translate(self, x, y, z):
        """ 平移相机 """
        self.translation[0] += x
        self.translation[1] += y
        self.translation[2] += z

    def handle_mouse_button(self, button, mode, x, y):
        """ 按下或者释放鼠标时调用 """
        xSize, ySize = glutGet(GLUT_WINDOW_WIDTH), glutGet(GLUT_WINDOW_HEIGHT)
        y = ySize - y  # 因为 OpenGL 已经反转，反转y坐标
        self.mouse_loc = (x, y)

        if mode == GLUT_DOWN:
            self.pressed = button
            if button == GLUT_RIGHT_BUTTON:
                pass
            elif button == GLUT_LEFT_BUTTON:  # pick
                self.trigger('pick', x, y)
            elif button == 3:  # 向上滚动
                self.translate(0, 0, 1.0)
            elif button == 4:  # 向下滚动
                self.translate(0, 0, -1.0)
        else:  # 释放鼠标
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
                self.translate(dx/60.0, dy/60.0, 0)
            else:
                pass
            glutPostRedisplay()
        self.mouse_loc = (x, y)

    def handle_keystroke(self, key, x, screen_y):
        """ 用户通过键盘输入时调用 """
        xSize, ySize = glutGet(GLUT_WINDOW_WIDTH), glutGet(GLUT_WINDOW_HEIGHT)
        y = ySize - screen_y
        if key == 's':
            self.trigger('place', 'sphere', x, y)
        elif key == 'c':
            self.trigger('place', 'cube', x, y)
        elif key == GLUT_KEY_UP:
            self.trigger('scale', up=True)
        elif key == GLUT_KEY_DOWN:
            self.trigger('scale', up=False)
        elif key == GLUT_KEY_LEFT:
            self.trigger('rotate_color', forward=True)
        elif key == GLUT_KEY_RIGHT:
            self.trigger('rotate_color', forward=False)
        glutPostRedisplay()
```

#### 内部回调

在上面的代码片段中，你注意到，当交互实例解释用户操作时，它将调用 `self.trigger` 并带有描述操作类型的字符串。`Interaction` 类上的 `trigger` 函数是一个简单回调系统的一部分，我们将使用它来处理应用程序级事件。回想一下，`Viewer` 类上的 `init_interaction` 函数通过调用 `register_callback` 在交互实例上注册回调。

```py
    # Interaction 类
    def register_callback(self, name, func):
        self.callbacks[name].append(func)
```

当用户界面代码需要触发场景上的事件时，交互类调用它对该特定事件保存的所有回调：

```py
    # Interaction 类
    def trigger(self, name, *args, **kwargs):
        for func in self.callbacks[name]:
            func(*args, **kwargs)
```

这个应用程序级回调系统消除了系统其余部分了解操作系统输入的需求。每个应用程序级回调都表示应用程序中有意义的请求。`Interaction` 类充当操作系统事件和应用程序级事件之间的转换器。这意味着，如果我们决定将 modeller 移植到 GLUT 之外的另一个工具包中，我们只需要用一个类来替换`Interaction` 类，该类将新工具箱的输入转换为相同的一组有意义的应用程序级回调。

|Callback | Arguments | Purpose | 
|:--------------|:-------------------|:---------|
 |`pick` | x:number, y:number |选择鼠标指针位置处的节点。 | 
 |`move` | x:number, y:number | 将当前选定的节点移动到鼠标指针位置。 | 
 |`place` | shape:string, x:number, y:number | 在鼠标指针位置放置指定类型的形状。 | 
 |`rotate_color` | forward:boolean | 在颜色列表中向前或向后旋转当前选定节点的颜色。 |
  |`scale` | up:boolean | 根据参数缩小或放大当前选定的节点。 |

这个简单的回调系统提供了这个项目所需的所有功能。然而，在生产3D建模器中，用户界面对象通常是动态创建和销毁的。在这种情况下，我们需要一个更复杂的事件监听系统，在这个系统中，对象可以注册和取消注册事件的回调。

### 与场景交互

使用回调机制，我们可以从 `Interaction` 类接收有关用户输入事件的相关信息。我们已经准备好将这些动作应用到 `Scene` 中。

#### 移动场景

在这个项目中，我们通过变换场景来完成相机运动。换句话说，照相机位于固定位置，用户输入移动场景而不是移动照相机。相机放置在[0，0，-15]处，面向世界空间原点。（或者，我们可以更改透视矩阵以移动摄影机而不是场景。此设计决策对项目的其余部分影响很小。）在 `Viewer` 中重新查看 `render` 函数，我们看到 `Interaction`的状态在渲染 `Scene` 之前先用于转换 OpenGL 矩阵状态。与场景的交互有两种类型：旋转和平移。

#### 使用轨迹球旋转场景

我们使用轨迹球算法来完成场景的旋转。轨迹球是一个直观的界面，用于在三维中操纵场景。从概念上讲，轨迹球界面的功能就像场景位于透明球体内部一样。把一只手放在地球仪的表面并推动它使地球仪旋转。同样，单击鼠标右键并在屏幕上移动它可以旋转场景。你可以在 OpenGL Wiki 上找到更多关于轨迹球的理论。在这个项目中，我们使用作为 Glumpy 的一部分提供的轨迹球实现。

我们使用 `drag_to` 函数与轨迹球进行交互，以鼠标的当前位置作为起始位置，并将鼠标位置的更改作为参数。

```py
self.trackball.drag_to(self.mouse_loc[0], self.mouse_loc[1], dx, dy)
```

得到的旋转矩阵是在场景被渲染时 viewer 中的 `trackball.matrix` 。

#### 旁白：四元数

旋转通常选择两种方式之一来表示。第一种是围绕每个轴的旋转值；可以将其存储为浮点数的三元组。另一种常见的旋转表示法是四元数，四元数是由一个带有$x$、$y$和$z$坐标的向量和一个$w$旋转组成的元素。与单轴旋转相比，使用四元数有许多好处；特别是，它们在数值上更稳定。使用四元数可以避免像万向节锁这样的问题。四元数的缺点是它们不太直观，更难理解。

轨迹球实现通过在内部使用四元数存储场景的旋转来避免万向节锁。幸运的是，我们不需要直接处理四元数，因为轨迹球上的矩阵成员将旋转转化为矩阵。

#### 平移场景

平移场景（即滑动场景）比旋转场景简单得多。场景转换由鼠标滚轮和鼠标左键提供。鼠标左键在$x$和$y$坐标下转换场景。滚动鼠标滚轮可在z坐标系（朝向或远离相机）平移场景。`Interaction` 类存储当前场景的转换，并使用`translate` 函数对其进行修改。查看器在渲染期间检索`Interaction` 相机位置，以便在 `glTranslated` 调用中使用。

#### 选择场景对象

现在用户可以移动和旋转整个场景以获得所需的透视图，下一步是允许用户修改和操纵组成场景的对象。

为了让用户操纵场景中的对象，他们需要能够选择元素。

为了选择一个元素，我们使用当前的投影矩阵来生成一条表示鼠标单击的光线，就像鼠标指针将一条光线射入场景一样。选定节点是距离光线相交的相机最近的节点。因此，选取问题简化为在场景中寻找光线和节点之间的交点的问题。所以问题是：我们如何判断光线是否命中一个节点？

精确计算光线是否与节点相交是一个具有挑战性的问题，无论是代码的复杂性还是性能。我们需要为每种类型的图元编写一个光线对象相交检查。对于具有多个面的复杂网格几何体的场景节点，计算精确的光线与对象相交将需要针对每个面测试光线，计算成本较高。

为了保持代码简洁和性能合理，我们使用了一个简单、快速的近似方法来进行光线对象相交测试。在我们的实现中，每个节点存储一个轴对齐的边界框（AABB），这是它所占空间的近似值。为了测试光线是否与节点相交，我们测试光线是否与节点的AABB相交。这种实现意味着所有节点共享用于交叉测试的相同代码，这意味着所有节点类型的性能代价都是恒定的且较小的。

```py
    # Viewer 类
    def get_ray(self, x, y):
        """ 生成一条从附近平面开始，指向x y坐标面向方向的射线
            参数 x, y：屏幕上鼠标的x，y坐标
            返回： 射线的 start, direcion 
        """
        self.init_view()
    
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
    
        # get two points on the line.
        start = numpy.array(gluUnProject(x, y, 0.001))
        end = numpy.array(gluUnProject(x, y, 0.999))
    
        # convert those points into a ray
        direction = end - start
        direction = direction / norm(direction)
    
        return (start, direction)
    
    def pick(self, x, y):
        """ 对一个对象执行 pick 操作。选择场景中的一个对象 """
        start, direction = self.get_ray(x, y)
        self.scene.pick(start, direction, self.modelView)
```

为了确定单击了哪个节点，我们遍历场景以测试光线是否命中任何节点。我们取消选择当前选定的节点，然后选择交点最接近光线原点的节点。

```py
    # Scene 类
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
        mindist = sys.maxint
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
```

在 `Node` 类中，`pick` 函数测试光线是否与节点的轴对齐边界盒（AABB）相交。如果选择了某个节点，则 `select` 函数将切换该节点的选定状态。请注意，AABB的 `ray_hit` 函数接受框的坐标空间和光线坐标空间之间的变换矩阵作为第三个参数。每个节点在进行 `ray_hit` 函数调用之前对矩阵应用自己的变换。

```py
 # Node 类
    def pick(self, start, direction, mat):
        """
        返回光线是否命中对象
        参数： start, direction 需要检查的射线
               mat 转换光线用的 modelview 矩阵
        """

        # transform the modelview matrix by the current translation
        newmat = numpy.dot(
            numpy.dot(mat, self.translation_matrix), 
            numpy.linalg.inv(self.scaling_matrix)
        )
        results = self.aabb.ray_hit(start, direction, newmat)
        return results

    def select(self, select=None):
       """ Toggles or sets selected state """
       if select is not None:
           self.selected = select
       else:
           self.selected = not self.selected
```

光线-AABB选择方法非常易于理解和实施。但是，在某些情况下结果是错误的。

![](/modeller/markdown/img/AABBError.png)


例如，在球体中，球体本身仅接触 AABB 每个面的中心的 AABB。但是，如果用户单击球体的AABB角，则会检测到与球体的碰撞，即便用户打算单击球体后的某个物体。

在计算机图形学和软件工程的许多领域中，复杂性，性能和准确性之间的这种折衷是常见的。

#### 修改场景对象

接下来，我们希望允许用户操作选定的节点。它们可能需要移动、调整大小或更改选定节点的颜色。当用户输入一个命令来操作一个节点时，`Interaction` 类将输入转换为用户想要的操作，并调用相应的回调。

当查看器接收到其中一个事件的回调时，它会调用场景中相应的函数，该函数反过来将转换应用于当前选定的节点。

```py
    # Viewer 类
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
```

#### 更改颜色

操纵颜色通过颜色列表完成。用户可以使用箭头键在列表中循环。场景将颜色更改命令调度到当前选定的节点。

```py
    # Scene 类
    def rotate_selected_color(self, forwards):
        """ 旋转当前选定节点的颜色 """
        if self.selected_node is None: return
        self.selected_node.rotate_color(forwards)
```

每个节点存储其当前颜色。`rotate_color` 函数只修改节点的当前颜色。渲染节点时，颜色将通过 `glColor` 传递给OpenGL。

```py
    # Node 类
    def rotate_color(self, forwards):
        self.color_index += 1 if forwards else -1
        if self.color_index > color.MAX_COLOR:
            self.color_index = color.MIN_COLOR
        if self.color_index < color.MIN_COLOR:
            self.color_index = color.MAX_COLOR
```

#### 缩放节点

与颜色一样，场景会将任何缩放修改发送到选定节点（如果存在）。

```py
    # Scene 类
    def scale_selected(self, up):
        """ 缩放当前选择节点 """
        if self.selected_node is None: return
        self.selected_node.scale(up)
```

每个节点存储一个当前矩阵，该矩阵存储其比例。按参数$x$、$y$和$z$在这些方向缩放的矩阵是：

$$ \begin{bmatrix} x & 0 & 0 & 0 \\ 0 & y & 0 & 0 \\ 0 & 0 & z & 0 \\ 0 & 0 & 0 & 1 \\ \end{bmatrix} $$ $$ \begin{bmatrix} x & 0 & 0 & 0 \\ 0 & y & 0 & 0 \\ 0 & 0 & z & 0 \\ 0 & 0 & 0 & 1 \\ \end{bmatrix} $$

当用户修改节点的比例时，生成的缩放矩阵乘以该节点的当前缩放矩阵。

```py
    # class Node
    def scale(self, up):
        s =  1.1 if up else 0.9
        self.scaling_matrix = numpy.dot(self.scaling_matrix, scaling([s, s, s]))
        self.aabb.scale(s)
```

函数 `scaling` 返回这样一个矩阵，给定$x$、$y$和$z$缩放因子的列表。

```py
def scaling(scale):
    s = numpy.identity(4)
    s[0, 0] = scale[0]
    s[1, 1] = scale[1]
    s[2, 2] = scale[2]
    s[3, 3] = 1
    return s
```

#### 移动节点

为了平移节点，我们和选择对象一样，使用光线计算。我们将表示当前鼠标位置的光线传递到场景的 `move` 函数中。节点的新位置应位于光线上。为了确定在光线上放置节点的位置，我们需要知道节点与相机的距离。因为我们在选择节点时（在 `pick` 函数中）存储了节点的位置和与相机的距离，所以我们可以在这里使用这些数据。我们找到沿目标光线距离相机的距离相同的点，并计算新位置和旧位置之间的向量差。然后我们根据得到的向量来转换节点。

```py
    # Scene 类
    def move_selected(self, start, direction, inv_modelview):
        """
        如果有选中节点，移动它
        
        参数：  start, direction: 描述光线
               inv_modelview: 场景当前矩阵的反转
        """
        if self.selected_node is None: return
    
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
```

请注意，新位置和旧位置是在相机坐标空间中定义的。我们需要在世界坐标系中定义我们的平移。因此，我们通过乘以 modelview 矩阵的倒数将相机空间平移转换为世界空间平移。

与缩放一样，每个节点都存储一个表示其平移的矩阵。平移矩阵如下所示：

$$ \begin{bmatrix} 1 & 0 & 0 & x \ 0 & 1 & 0 & y \ 0 & 0 & 1 & z \ 0 & 0 & 0 & 1 \ \end{bmatrix} $$

当节点被平移时，我们为当前的平移构造一个新的平移矩阵，并将其乘以节点的平移矩阵，以便在渲染期间使用。

```py
    # class Node
    def translate(self, x, y, z):
        self.translation_matrix = numpy.dot(
            self.translation_matrix, 
            translation([x, y, z]))
```

`translation` 函数返回一个平移矩阵，给定一个表示$x$、$y$和$z$平移距离的列表。

```py
def translation(displacement):
    t = numpy.identity(4)
    t[0, 3] = displacement[0]
    t[1, 3] = displacement[1]
    t[2, 3] = displacement[2]
    return t
```

#### 放置节点

节点放置使用选择节点和平移节点相同的技术。我们对当前鼠标位置使用相同的光线计算来确定节点的放置位置。

```py
    # Viewer 类
    def place(self, shape, x, y):
        """ 执行place，将一个基本体放置到场景中 """
        start, direction = self.get_ray(x, y)
        self.scene.place(shape, start, direction, self.inverseModelView)
```

要放置新节点，我们首先创建相应类型节点的新实例并将其添加到场景中。我们想把节点放在用户光标的下方，这样我们就可以在光线上找到一个点，与相机保持固定的距离。同样，光线是在相机空间中表示的，因此我们将生成的平移向量乘以逆模型视图矩阵，将其转换为世界坐标空间。最后，根据计算出的向量对新节点进行平移。

```py
    # Scene 类
    def place(self, shape, start, direction, inv_modelview):
        """
        放置新节点
        
        参数：  shape: 要添加的形状
               start, direction: 描述光线
               inv_modelview: 场景当前矩阵的反转
        """
        new_node = None
        if shape == 'sphere': new_node = Sphere()
        elif shape == 'cube': new_node = Cube()
        elif shape == 'figure': new_node = SnowFigure()
    
        self.add_node(new_node)
    
        # 将节点放置在相机空间中的光标处
        translation = (start + direction * self.PLACE_DEPTH)
    
        # 将 translation 转换为世界空间
        pre_tran = numpy.array([translation[0], translation[1], translation[2], 1])
        translation = inv_modelview.dot(pre_tran)
    
        new_node.translate(translation[0], translation[1], translation[2])
```

## 概要

祝贺你！我们成功地实现了一个小型的三维建模器！

![](/modeller/markdown/img/StartScene.png)

我们了解了如何开发可扩展的数据结构来表示场景中的对象。我们注意到，使用复合设计模式和基于树的数据结构可以很容易地遍历场景进行渲染，并允许我们在不增加复杂性的情况下添加新类型的节点。我们利用这种数据结构将设计渲染到屏幕上，并在场景图的遍历中操纵 OpenGL 矩阵。我们为应用程序级事件构建了一个非常简单的回调系统，并用它来封装操作系统事件的处理。我们讨论了光线对象碰撞检测的可能实现，以及正确性、复杂性和性能之间的权衡。最后，我们实现了对场景内容进行操作的方法。

你可以期望在生产 3D 软件中找到这些相同的基本构建块。从 CAD 工具到游戏引擎，场景图结构和相对坐标空间在许多类型的 3D 图形应用程序中都可以找到。这个项目的一个主要简化是用户界面。一个生产的 3D 建模器应该有一个完整的用户界面，这就需要一个更复杂的事件系统，而不是我们简单的回调系统。

我们可以做进一步的实验，为这个项目添加新功能。试试以下方法：

- 添加节点类型以支持任意形状的三角形网格。
- 添加撤消堆栈，以允许撤消/重做建模器操作。
- 使用 DXF 等 3D 文件格式保存/加载设计。
- 集成渲染引擎：导出设计以用于照片级渲染器。
- 通过精确的光线对象相交来改进碰撞检测。

## 进一步探索

为了进一步深入了解真实世界的三维建模软件，一些开源项目很有趣。

Blender 是一个开源的全功能三维动画套件。它提供了一个完整的三维管道，以建立视频特效，或游戏创作。建模器是这个项目的一小部分，它是将建模器集成到大型软件套件中的一个很好的例子。

OpenSCAD 是一个开源的三维建模工具。它不是交互式的，而是读取指定如何生成场景的脚本文件。这让设计师“完全控制建模过程”。

有关计算机图形学中的算法和技术的更多信息，Graphics Gems 是一个很好的资源。

