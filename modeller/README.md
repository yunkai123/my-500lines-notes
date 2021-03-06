# Modeller

这个项目是一个非常小且有限的三维建模。

## 先决条件 

Python 3，需安装 pyopengl 和 numpy。需要注意的是如果是64位的机器需要手动安装64位 pyopengl（pip自动安装的是32位版本）。

## 运行

viewer.py 是主文件。

## 用法

鼠标左键左键选择并拖动屏幕上的对象。

鼠标中键可移动场景。

鼠标右键可旋转屏幕。

“C”在鼠标光标处放置一个立方体。

“S”在鼠标光标处放置一个球体。

## 代码结构

Viewer 是主驱动程序类,它将动作分派到场景并开始渲染。

Interaction 处理用户输入。它保持当前鼠标位置、轨迹球和按下的按钮的状态。

Scene 表示概念场景。它包含一个节点列表，在本例中，这些节点都是基本体，但理论上可能更复杂。

Node 包含 node 类的实现，以及 sphere 和 cube 原始部件。一个 node 可以转换，并且有一个 AABB 用于碰撞。

AABB表示轴对齐边界盒（Axis Aligned Bounding Box）。它目前只用于选择，但也可以用于计算节点之间的碰撞。

Transformation 为一些常见的变换建立矩阵，没啥可讲的。

Primitive 为使用的原语部件建立 OpenGL 调用列表。有 100 多行没枯燥的设置代码。