#  Contingent:一个完全动态的构建系统

## 原文作者

Brandon Rhodes 和 Daniel Rocco。

Brandon Rhodes 在 20 世纪 90 年代末就开始使用 Python，17 年来一直在使用 Python 为业余天文学家维护 PyEphem 库。他在 Dropbox 工作，教授公司客户 Python 编程课程，为新英格兰野花协会的“Go Botany” Django网站 项目提供咨询，并将在2016年和2017年担任 PyCon会议主席。Brandon 认为，编写良好的代码是一种文学，那些格式精美的代码是平面设计作品，正确的代码是最易懂的思想形式之一。

Daniel Rocco 热爱 Python、咖啡、工艺、黑啤酒、对象和系统设计，波旁威士忌、教学、树木和拉丁吉他。他靠 Python 谋生，他总是在寻找从社区的其他人学习的机会，并通过分享知识作出贡献。他经常在 PyAtl 上演讲介绍性话题、测试、设计和耀眼的产品。他喜欢在有人分享一个新奇的的想法时看到人们眼中闪烁着惊奇和喜悦的火花。Daniel 和一个微生物学家以及四个有抱负的火箭专家住在 Atlanta。

## 引言

长期以来，构建系统一直是计算机编程中的标准工具。

标准的 make 构建系统于 1976 年首次开发，为它的作者赢得了 ACM 软件系统奖。它不仅让你声明一个输出文件依赖于一个（或多个）输入文件，而且可以递归地进行操作。例如，一个程序可能依赖一个目标文件，而目标文件又依赖相应的源代码：

```
    prog: main.o
            cc -o prog main.o

    main.o: main.c
            cc -C -o main.o main.c
```

make 在下一次调用时发现 main.c 源文件的修改时间比 main.o 更晚，它不仅会重建 main.o 对象文件，还会重建 prog 本身。

构建系统是分配给本科计算机科学专业学生的一个普通的学期项目，这不仅是因为构建系统几乎用在所有软件项目中，而且因为构建系统涉及基本数据结构和有向图算法（本文稍后将对此进行详细讨论）。

在构建系统经过数十年的使用和实践之后，人们可能会期望它们已完全成为通用的系统，可以满足最高的需求。但实际上，构建软件之间的一种常见交互作用（动态交叉引用问题）在大多数构建系统中都处理得很差，因此在本文中我们不仅要练习用于解决 make 的问题的经典解决方案和数据结构，还要将该解决方案扩展到更高需求的领域。

问题就是交叉引用，交叉引用出现在哪里？在文本文档、DOC 文档和印刷书籍中！

## 问题：构建文件系统

从源重建格式化文档的系统总是做太多或者太少的工作。

当文档变动很小时，它们会让你等待不相关的章节被重新编辑和重新设置格式，这时候它们做了太多工作。但是它们也可能在重新构建中做过少的工作，给你一个和要求不一致的最终产品。

考虑一下 Sphinx，它是 Python 语言官方文档和 Python 社区中许多项目的文档构建器。Sphinx 项目的 `index.rst` 通常会包含一个目录表：

```
Table of Contents
=================

.. toctree::

    install.rst
    tutorial.rst
    api.rst
```

该章节文件名列表告诉 Sphinx 在构建 `index.html` 输出文件时，需要包括指向三个章节中每个章节的链接。它还将包含指向每一章中任何小节的链接。除去其标记，上面的标题和 `toctree` 命令产生的文本可能是：

```
Table of Contents

• Installation

• Newcomers Tutorial
    • Hello, World
    • Adding Logging

• API Reference
    • Handy Functions
    • Obscure Classes
```

如你所见，此目录是来自四个不同文件的信息的汇总。虽然其基本顺序和结构来自 `index.rst`，但每个章节的实际标题均从这三章源文件本身中提取。

如果你考虑修改这个教程的章节标题。毕竟，“Newcomer”一词听起来很古怪，就像你的用户是刚来到 Wyoming 的定居者一样。那么你将编辑 `tutorial.rst` 的第一行来写出更好的内容：

```
-Newcomers Tutorial
+Beginners Tutorial
==================

Welcome to the tutorial!
This text will take you through the basics of...
```

当你准备重新构建时，Sphinx 会做正确的事！它将重新构建教程章节本身和索引。（将输出加入 `cat` 命令会使 Sphinx 在单独的行上说明每个重新构建的文件，而不是使用裸回车符将这些进度更新重复覆盖到一行。）

```
$ make html | cat
writing output... [ 50%] index
writing output... [100%] tutorial
```

因为 Sphinx 选择重新构建两个文档，所以现在除了 `tutorial.html` 要将其新标题放在顶部，`index.html` 展示的输出要在目录中显示更新的章节标题。 Sphinx 已经重新构建了所有内容，以便输出保持一致。

如果你对 `tutorial.rst` 的编辑较小，该怎么办？

```
Beginners Tutorial
==================

-Welcome to the tutorial!
+Welcome to our project tutorial!
This text will take you through the basics of...
```

在这种情况下，无需重新构建 `index.html`，因为对段落内部的较小编辑不会更改目录中的任何信息。但是事实证明，Sphinx 不再像前面展示的那样聪明！即使结果内容完全相同，它也将继续执行重新构建 `index.html` 的多余工作。

```
writing output... [ 50%] index
writing output... [100%] tutorial
```

你可以在 `index.html` 的“之前”和“之后”版本上运行 `diff` 命令，以确认你的小修改对首页没有影响——但是 Sphinx 还是让你等待它重新构建。

对于易于编译的小型文档你甚至可能没有注意到额外的构建工作。但是，当你频繁调整和编辑冗长、复杂的文档或涉及诸如绘图或动画之类的多媒体生成的文档时，工作流程的延迟会变得至关重要。虽然 Sphinx 会在你进行一次更改时努力不重新构建每一章。例如，它没有因为响应你的 `tutorial.rst` 编辑而重新构建 `install.html` 或 `api.html`，但它所做的超出了必要的范围。

事实证明，Sphinx 甚至会更糟：有时它做得太少，给你一个用户会注意到的不一致输出。

为了查看其中一个最简单的问题，请首先在你的 API 文档的顶部添加一个交叉引用：

```
API Reference
=============

+Before reading this, try reading our :doc:`tutorial`!
+
The sections below list every function
and every single class and method offered...
```

对于目录，Sphinx 通常会格外小心，将尽职地重新构建此 API 参考文档以及项目的 `index.html` 主页：

```
writing output... [ 50%] api
writing output... [100%] index
```

在 `api.html` 输出文件中，你可以确认 Sphinx 是否已将 tutorial 章节引人入胜的标题包含在交叉引用的 anchor 标签中：

```
<p>Before reading this, try reading our
<a class="reference internal" href="tutorial.html">
    <em>Beginners Tutorial</em>
</a>!</p>
```

如果现在再次对 `tutorial.rst` 文件顶部的标题进行编辑怎么办？你将使三个输出文件无效：

- 现在 `tutorial.html` 顶部的标题已过期，因此需要重新构建。
- `index.html` 中的目录仍然具有旧标题，因此需要重新构建。
- `api.html` 第一段中嵌入的交叉引用仍然具有旧的章节标题，还需要重新构建。

Sphinx 做了什么？

```
writing output... [ 50%] index
writing output... [100%] tutorial
```

哎呀。

仅重建了两个文件，而不是三个。 Sphinx 无法正确重新构建你的文档。

如果现在将 HTML 推送到网络，那么用户将在 `api.html` 顶部的交叉引用中看到旧标题，但一旦链接将他们带到 `tutorial.html` 本身，便会看到另一个标题（新标题）。Sphinx 支持的多种交叉引用均可能会发生这种情况：章标题，节标题，段落，类，方法和函数。

## 构建系统和一致性

上面描述的问题并非 Sphinx 特有的。它不仅困扰着其它文档系统（例如 LaTeX），而且甚至会困扰那些试图以古老的 make 编译的项目，如果它们的资源碰巧进行了交叉引用。

由于该问题是古老且普遍存在的，因此其解决方案的使用寿命也同样悠长：

```
$ rm -r _build/
$ make html
```

如果删除所有输出，则可以保证完全重新构建！有些项目甚至将 rm -r 重命名为 clean，因此仅需进行快速清理就可以清除项目输出。

通过消除每个中间或输出资源的副本，庞大的 rm -r 能够在不缓存任何内容的情况下强制重新构建，不会存储任何可能会导致产品过时的早期状态。

但是，我们可以开发出更好的方法吗？

如果你的构建系统是一个持续的过程，当它从一个文档的源代码传递到另一个文档的文本时，需要注意每个章节标题和每个交叉引用的短语，该怎么办？它关于更改单个源文件后是否需要重新构建其他文档的决定必须是精确的，而不是仅仅凭猜测，并且是正确的，而不是使输出出现不一致状态。 

结果将是一个类似于旧有的静态 make 工具的系统，但是该系统在构建文件时就了解了文件之间的依赖关系：在添加、更新和删除交叉引用时动态地添加和删除了依赖关系。

在下面的小节中，我们将使用 Python 构造一个名为 Contingent 的工具。Contingent 在存在动态依赖项的情况下保证正确性，同时执行最少的重建步骤。尽管它可以应用于任何问题领域，但我们将针对上面提到的一小部分问题运行它来解决。

## 链接任务以制作图

任何构建系统都需要一种链接输入和输出的方法。例如，在我们上面的讨论中，三个标记文本分别产生一个相应的 HTML 输出文件。表达这些关系最自然的方法是将它们变成一个框和箭头（或者用数学术语来说是节点和边）组成的图形。

![](/contingent/markdown/img/figure1.png)

程序员用来编写构建系统的每种语言都将提供各种数据结构，用这些数据结构可以表示节点和边的图形。

我们在 Python 中如何表示这样的图？

Python 语言通过直接支持四种通用数据结构的语法来赋予它们优先级。你可以通过简单地在源代码中键入它们的文本表示形式来创建四大数据结构的新实例，并且它们四个类型对象可以作为内置符号，无需导入即可使用。

**元组(tuple)** 是用于保存异构数据的只读序列，元组中的每个元素通常表示不同的含义。下面的例子中，元组将主机名和端口号放在一起，如果重新排列它将失去其含义：

```py
('dropbox.com', 443)
```

**列表(list)** 是一个用于保存同构数据的可变序列，每个项通常具有与其它项有相同的结构和含义。列表既可以保留数据的原始输入顺序，也可以重新排列或排序以建立新的更有用的顺序。

```py
['C', 'Awk', 'TCL', 'Python', 'JavaScript']
```

**集合(set)** 不保留顺序。集合仅记住是否已添加给定值，而不记住多少次，因此可用于从数据中删除重复项。 例如，以下两个集合将各自包含三个元素：

```py
{3, 4, 5}
{3, 4, 5, 4, 4, 3, 5, 4, 5, 3, 4, 5}
```

**字典dict** 是一个关联数据结构，用于存储通过键可访问的值。使用字典，程序员可以选择对每个值进行索引的键，而不是像元组和列表那样使用自动整数索引。字典的查找由哈希表支持，这意味着无论字典有十二个键还是一百万个键，查找都以相同的速度运行。

```py
{'ssh': 22, 'telnet': 23, 'domain': 53, 'http': 80}
```

Python 灵活性的关键在于这四个数据结构是可以组合的。程序员可以将它们彼此任意嵌套以产生更复杂的数据存储，其规则和语法仍然遵循基础元组，列表，集合和字典中的简单规则。

假设我们图的每个边都需要至少知道其源节点和目标节点，那么最简单的表示可能就是元组。图顶部的边可能看起来像：

```py
('tutorial.rst', 'tutorial.html')
```

我们如何存储多个边？虽然我们最初的想法可能是将所有边元组都放入一个列表中，但这会有一些不利条件。列表很小心地保持顺序，但是图形中边的绝对顺序是没有意义的。即使我们只希望能够在 tutorial.rst 和 tutorial.html 之间绘制单个箭头，列表也会保存完全相同的边的多个副本。因此，正确的选择是集合，这样我们将上图表示为：

```py
{('tutorial.rst', 'tutorial.html'),
    ('index.rst', 'index.html'),
    ('api.rst', 'api.html')}
```

这允许我们在所有边上进行快速迭代、对单个边进行快速的插入和删除操作以及快速检查特定的边是否存在。

当然，我们需要做的操作不止这些。

像 Contingent 这样的构建系统需要了解给定节点与连接到该节点的所有节点之间的关系。例如，当 `api.rst` 发生更改时，Contingent 需要知道该更改会影响哪些资源，以最大程度地减少要执行的工作，同时确保完整的构建。要回答这个问题：“ `api.rst` 下游有哪些节点？” ，我们需要检查 `api.rst` 传出的边。

但是构建依赖关系图要求 Contingent 也要考虑节点的输入。例如，当构建系统组装输出文档 `tutorial.html` 时，使用了哪些输入？通过观察每个节点的输入，Contingent 可以知道 `api.html` 依赖于 `api.rst`，而 `tutorial.html` 则没有。当源发生更改并进行重新构建时，Contingent 会重新构建每个更改的节点的输入边，以删除不再使用的边，并重新了解这次任务使用的资源。

我们的元组集合很难解决这些问题中的任何一个。如果我们需要了解 `api.html` 与图的其余部分之间的关系，则需要遍历整个集合以查找在 `api.html` 节点处开始或结束的边。

像 Python 的字典这样的关联数据结构将允许直接从特定节点查找所有边，从而使这个问题变得更加容易：

```py
{'tutorial.rst': {('tutorial.rst', 'tutorial.html')},
    'tutorial.html': {('tutorial.rst', 'tutorial.html')},
    'index.rst': {('index.rst', 'index.html')},
    'index.html': {('index.rst', 'index.html')},
    'api.rst': {('api.rst', 'api.html')},
    'api.html': {('api.rst', 'api.html')}}
```

现在查找特定节点的边会非常快，代价是必须将每条边存储两次：一次存储在一组传入边中，一次存储在一组传出边中。但是每一组中的边都必须手动检查，看哪些是传入的，哪些是传出的。在节点的边集中反复命名节点也有点多余。

解决这两个问题的方法是将传入和传出的边放在它们各自独立的数据结构中，这也就免除了我们在每个节点的相关边中都必须反复提到节点。

```py
    incoming = {
        'tutorial.html': {'tutorial.rst'},
        'index.html': {'index.rst'},
        'api.html': {'api.rst'},
        }

    outgoing = {
        'tutorial.rst': {'tutorial.html'},
        'index.rst': {'index.html'},
        'api.rst': {'api.html'},
        }
```

请注意，`outgoing` 直接用 Python 语法表示我们在前面图中绘制的内容：左侧的源文档将由构建系统转换为右侧的输出文档。对于这个简单的示例，每个源只指向一个输出，所有输出集只有一个元素，但是我们将很快看到一个输入节点具有多个下游结果的示例。

在这个字典的集合数据结构中，每个边都会被表示两次，一次作为一个节点的输出边(`tutorial.rst → tutorial.html`)又一次成为另一个的边缘(`tutorial.html ← tutorial.rst`). 这两种表示精确地捕捉到相同的关系，只是从边两端的两个节点的相反角度。但作为这种冗余的回报，这种数据结构支持 Contingent 需要的快速查找。

## 类的正确使用

你可能会对上面讨论的 Python 数据结构中缺少类感到惊讶。毕竟，类是构建应用程序的一种常见机制，也是其拥护者和批评者之间激烈辩论的一个常见主题。类曾经被认为是非常重要的，以至于整个教育课程都围绕着它们而设计，而大多数流行的编程语言都包含了定义和使用它们的专用语法。

但事实证明，类通常与数据结构设计问题相关。类不是为我们提供一个完全替代的数据建模范式，而是简单地重复我们已经看到的数据结构：

- 一个类实例被*实现*为dict。
- 一个类实例就像可变元组一样*使用*。

类通过一个更优雅的语法提供键查找，在这里你可以使用 `graph.incoming` 而不是 `graph["incoming"]`。但是，在实践中，类实例几乎从未被用作通用键值存储。相反，它们被用来按属性名组织相关但异构的数据，将细节封装在接口后面。

因此，不需要将主机名和端口号放在一个元组中，并且不必记住哪个是第一个，哪个是第二个，而是创建一个 `Address` 类，该类的每个实例都有一个 `host` 属性和一个 `port` 属性。然后，你可以将 `Address` 对象传递到原本有匿名元组的位置。代码变得更易于阅读和编写。但是使用类实例并不会真正改变我们在进行数据设计时遇到的任何问题；它只是提供了一个更优雅、更不匿名的容器。

因此，类的真正价值并不在于它们改变了数据设计的科学性。类的价值在于，它们允许你对程序的其余部分隐藏数据设计！

成功的应用程序设计取决于我们能否利用 Python 提供的强大的内置数据结构，同时尽可能减少我们在任何时候需要记住的细节。类提供了解决这种明显的困境的机制：有效地使用，类提供了围绕系统总体设计的一些小子集的外观。当我们在一个子集（例如 `Graph`）中工作时，只要我们能记住它们的接口，我们就可以忘记其它子集的实现细节。通过这种方式，程序员在编写系统的过程中经常会发现自己在几个抽象层次之间导航，现在使用特定子系统的特定数据模型和实现细节，通过接口连接更高级的概念。

例如，从外部看，代码可以简单地请求一个新的 `Graph` 实例：

```py
>>> from contingent import graphlib
>>> g = graphlib.Graph()
```

不需要了解 `Graph` 如何工作的细节。简单使用图的代码在操作图时（如添加边或执行其他操作时）只看到接口动词（方法调用）：

```py
>>> g.add_edge('index.rst', 'index.html')
>>> g.add_edge('tutorial.rst', 'tutorial.html')
>>> g.add_edge('api.rst', 'api.html')
```

细心的读者会注意到，我们在没有显式地创建“节点”和“边”对象的情况下向图中添加了边，并且这些早期示例中的节点本身只是字符串。来自其它语言和传统，人们可能期望看到系统中所有内容的用户定义类和接口：

```java
    Graph g = new ConcreteGraph();
    Node indexRstNode = new StringNode("index.rst");
    Node indexHtmlNode = new StringNode("index.html");
    Edge indexEdge = new DirectedEdge(indexRstNode, indexHtmlNode);
    g.addEdge(indexEdge);
```

Python 语言和社区明确而有意地强调使用简单的通用数据结构来解决问题，而不是为我们想要处理的问题的每一分钟细节创建自定义类。这是“Pythonic”解决方案概念的一个方面：Pythonic 解决方案试图最大程度的减少语法开销，并利用 Python 强大的内置工具和广泛的标准库。

考虑到这些因素，让我们回到 `Graph` 类，检查它的设计和实现，看看数据结构和类接口之间的相互作用。当构建一个新的 `Graph` 实例时，已经使用我们在上一节中概述的逻辑构建了一对字典来存储边：

```py
class Graph:
    """构建任务之间关系的有向图"""

    def __init__(self):
        self._inputs_of = defaultdict(set)
        self._consequences_of = defaultdict(set)
```

属性名  `_inputs_of` 和 `_consequences_of` 前面的前导下划线在 Python 社区中用来表示属性是私有的。这种约定是社区建议程序员通过空间和时间相互传递消息和警告的一种方式。认识到需要标记公共对象属性和内部对象属性之间的差异，社区采用了单一的前导下划线作为其它程序员（包括未来的我们自己）的简洁一致的指示符，即属性最好作为类的不可见内部机制的一部分来处理。

为什么我们要使用 `defaultdict` 而不是标准 dict？在使用其它数据结构编写 dict 时，一个常见的问题是处理缺少的键。对于普通 dict，检索不存在的键会引发 `KeyError`：

```py
>>> consequences_of = {}
>>> consequences_of['index.rst'].add('index.html')
Traceback (most recent call last):
     ...
KeyError: 'index.rst'
```

使用普通 dict 需要在整个代码中进行特殊检查，以处理此特定情况，例如添加新边时：

```py
    # 处理 “我们还未见过此任务” 特殊场景:

    if input_task not in self._consequences_of:
        self._consequences_of[input_task] = set()

    self._consequences_of[input_task].add(consequence_task)
```

这种需求是如此普遍，以至于 Python 包含一个特殊的工具 `defaultdict`，它使你可以提供一个返回缺少键值的函数。当我们询问图尚未看到的边时，我们将获得一个空集而不是一个异常：

```py
>>> from collections import defaultdict
>>> consequences_of = defaultdict(set)
>>> consequences_of['api.rst']
set()
```

以这种方式构建我们的实现意味着每个键的首次使用看起来与第二次及以后相同：

```py
>>> consequences_of['index.rst'].add('index.html')
>>> 'index.html' in consequences_of['index.rst']
True
```

基于这些技术，让我们研究一下 `add_edge` 的实现，我们前面用它来构建图。

```py
    def add_edge(self, input_task, consequence_task):
        """添加一条边：consequence_task，使用 input_task 的输出。"""
        self._consequences_of[input_task].add(consequence_task)
        self._inputs_of[consequence_task].add(input_task)
```

这种方法隐藏了以下事实，即每个新边需要两个而不是一个存储步骤，这样我们就可以从两个方向知道它。请注意 `add_edge()` 不知道或不关心之前是否看到过这两个节点。因为输入和结果数据结构都是一个 `defaultdict(set)`，`add_edge()` 方法不知道节点是新的，`defaultdict` 通过动态创建一个新的 `set` 对象来处理差异。正如我们在上面看到的，如果不使用 `defaultdict`，`add_edge()` 将延长三倍。更重要的是，理解和解释结果代码将更加困难。这个实现展示了一种解决问题的 Pythonic 风格方法：简单、直接和简洁。

还应向调用方提供访问每个边的简单方法，而不必学习如何遍历我们的数据结构：

```py
    def edges(self):
        """以 (input_task, consequence_task) 元组的形式返回所有边"""
        return [(a, b) for a in self.sorted(self._consequences_of)
                       for b in self.sorted(self._consequences_of[a])]
```

这个 `Graph.sorted()` 方法尝试按自然排序顺序（如字母顺序）对节点进行排序，这样可以为用户提供稳定的输出顺序。

通过使用这种遍历方法，我们可以看到，在前面的三个“add”方法调用之后，g现在表示与上图中看到的相同的图。

```py
>>> from pprint import pprint
>>> pprint(g.edges())
[('api.rst', 'api.html'),
 ('index.rst', 'index.html'),
 ('tutorial.rst', 'tutorial.html')]
```

我们现在有了一个真实的 Python 对象，而不仅仅是一个图，我们可以问它有趣的问题！例如，当 Contingent 从源文件构建博客时，它需要知道诸如“什么依赖 `api.rst`？”之类的信息。当 `api.rst` 的内容发生变化时：

```py
>>> g.immediate_consequences_of('api.rst')
['api.html']
```

`Graph` 告诉 Contingent，当 `api.rst` 变化时，`api.html` 文件现在已经过时，必须重新构建。

`index.html` 呢？

```py
>>> g.immediate_consequences_of('index.html')
[]
```

返回了一个空列表，表示 `index.html` 位于图的右边，因此如果更改，则无需再重新构建。由于已经进行了数据布局工作，因此可以非常简单地表示此查询：

```py
    def immediate_consequences_of(self, task):
        """返回使用 task 作为输入的任务"""
        return self.sorted(self._consequences_of[task])
 >>> from contingent.rendering import as_graphviz
 >>> open('figure1.dot', 'w').write(as_graphviz(g)) and None
```

上图忽略了我们在本文开头部分发现的一个最重要的关系：文档标题在目录中的显示方式。让我们把这个细节填一下。我们将为每个需要通过解析输入文件生成的标题字符串创建一个节点，然后传递给其他例程之一：

```py
>>> g.add_edge('api.rst', 'api-title')
>>> g.add_edge('api-title', 'index.html')
>>> g.add_edge('tutorial.rst', 'tutorial-title')
>>> g.add_edge('tutorial-title', 'index.html')
```

结果是一个图，这可以很好地处理重新构建我们在本文开头讨论过的目录。

![](/contingent/markdown/img/figure2.png)

这本手册演示了我们最终将让 Contingent 为我们做什么：图 `g` 捕捉了项目文档中各种工件的输入和结果。

## 学习联系

我们现在有了一种方法让 Contingent 跟踪任务以及它们之间的关系。如果我们仔细看一下图2，然而，我们看到它实际上有点波折和模糊：`api.rst` 是如何产生 `api.html` 的？我们如何知道 `index.html` 需要 tutorial中的标题吗？这种依赖关系是如何解决的？

当我们手动构建结果图时，我们对这些想法的直觉概念起到了作用，但不幸的是，计算机并不是非常直观，所以我们需要更精确地了解我们想要的东西。

从数据源生成输出需要哪些步骤？这些步骤是如何定义和执行的？ Contingent 如何知道它们之间的联系？

在 Contingent 中，构建任务被建模为函数加参数。这些函数定义了特定项目理解如何执行的动作。这些参数提供了具体的细节：应该读取哪个源文档，需要哪个博客标题。当它们运行时，这些函数可能依次调用其他任务函数，传递它们需要答案的任何参数。

为了了解这是如何工作的，我们现在将实现本文开头描述的文档生成器。为了防止我们陷入一堆细节的泥潭中，我们将使用简化的输入和输出文档格式。我们的输入文档将由第一行的标题组成，其余部分构成正文。交叉引用只是反引号包含的源文件，输出时用输出中相应文档的标题替换。

下面是我们示例的 `index.txt`, `api.txt` 和 `tutorial.txt` 的内容，说明我们的小文档格式的标题、文档正文的交叉引用：

```
>>> index = """
... Table of Contents
... -----------------
... * `tutorial.txt`
... * `api.txt`
... """

>>> tutorial = """
... Beginners Tutorial
... ------------------
... Welcome to the tutorial!
... We hope you enjoy it.
... """

>>> api = """
... API Reference
... -------------
... You might want to read
... the `tutorial.txt` first.
... """
```

既然我们有一些源材料可以使用，那么一个基于 Contingent 的博客构建器需要什么功能呢？

在上面的简单示例中，HTML 输出文件直接从源代码开始，但在实际系统中，将源代码转换为标记需要几个步骤：从磁盘读取原始文本，将文本解析为方便的内部表示形式，处理作者可能指定的任何指令，解析交叉引用或其他外部依赖项（如 include 文件），并应用一个或多个视图转换来将内部表示形式转换为其输出形式。

Contingent 通过将任务分组到一个 `Project` 中来管理任务，`Project` 是一种构建系统的工具，将自身注入到构建过程中间，并记录每次一个任务与另一个任务之间的关系图，以构建所有任务之间的关系图。

```py
>>> from contingent.projectlib import Project, Task
>>> project = Project()
>>> task = project.task
```

本文开头给出的示例的构建系统可能涉及一些任务。

我们的 `read()` 任务将假装从磁盘读取文件。由于我们在变量中定义了源文本，因此只需将文件名转换为相应的文本即可。

```py
  >>> filesystem = {'index.txt': index,
  ...               'tutorial.txt': tutorial,
  ...               'api.txt': api}
  ...
  >>> @task
  ... def read(filename):
  ...     return filesystem[filename]
```

`parse()` 任务根据文档格式的规范解释文件内容的原始文本。我们的格式非常简单：文档的标题出现在第一行，其余内容被视为文档的正文。

```py
  >>> @task
  ... def parse(filename):
  ...     lines = read(filename).strip().splitlines()
  ...     title = lines[0]
  ...     body = '\n'.join(lines[
```

由于格式非常简单，所以解析器有点笨，但它说明了解析器需要执行的解释责任。（一般来说，解析是一个非常有趣的主题，很多书籍都有部分或完全关于它的内容。）在 Sphinx 这样的系统中，解析器必须理解系统定义的许多标记、指令和命令，将输入文本转换成系统其他部分可以处理的内容。

请注意 `parse()` 和 `read()` 之间的连接点，解析的第一个任务是将已提供的文件名传递给 `read()`，后者查找并返回该文件的内容。

指定源文件名的 `title_of()` 任务返回文档的标题：

```py
  >>> @task
  ... def title_of(filename):
  ...     title, body = parse(filename)
  ...     return title
```

这个任务很好地说明了文档处理系统各个部分之间的职责分离。`title_of()` 函数直接从文档的内存表示（在本例中是元组）中工作，而不是利用它自己重新解析整个文档来查找标题。`parse()` 函数根据系统规范的约定单独生成内存中的表示形式，而其它博客构建器处理函数如 `title_of()` 只使用其输出作为其权限。

如果你习惯了传统的面向对象，这种面向功能的设计可能看起来有点奇怪。在 OO 解决方案中，`parse()` 将返回某种 `Document` 对象，该对象的 `title_of()` 作为方法或属性。实际上，Sphinx 就是这样工作的：它的 `Parser` 子系统生成一个“Docutils 文档树”对象，供系统的其他部分使用。

对于这些不同的设计范例，Contingent 并不固执己见，同样支持这两种方法。在本章中我们将保持简单。

最后一个任务 `render()` 将文档的内存表示形式转换为输出形式。实际上，它是 `parse()` 的逆函数。`parse()` 获取符合规范的输入文档并将其转换为内存中的表示形式，`render()` 则获取内存中的表示形式并生成符合某种规范的输出文档。

```py
  >>> import re
  >>>
  >>> LINK = '<a href="{}">{}</a>'
  >>> PAGE = '<h1>{}</h1>\n<p>\n{}\n<p>'
  >>>
  >>> def make_link(match):
  ...     filename = match.group(1)
  ...     return LINK.format(filename, title_of(filename))
  ...
  >>> @task
  ... def render(filename):
  ...     title, body = parse(filename)
  ...     body = re.sub(r'`([^`]+)`', make_link, body)
  ...     return PAGE.format(title, body)
```

下面是一个运行示例，它将调用上述逻辑的每个阶段，渲染 `tutorial.txt` 以产生输出：

```py
>>> print(render('tutorial.txt'))
<h1>Beginners Tutorial</h1>
<p>
Welcome to the tutorial!
We hope you enjoy it.
<p>
```

下面展示了任务图，该图以传递方式连接生成输出所需的所有任务，从读取输入文件到解析和转换文档，并呈现文档：

![](/contingent/markdown/img/figure3.png)

事实证明，上图不是手绘的，而是直接从 Contingent 中产生的！Project 对象可以构建此图，因为它维护自己的调用堆栈，类似于 Python 维护的实时执行帧堆栈，以便在当前函数返回时记住哪个函数要继续运行。

每次调用一个新任务时，Contingent 可以假定它已经被当前位于堆栈顶部的任务调用，并且它的输出将被使用。维护堆栈需要围绕任务 *T* 的调用执行几个额外的步骤：

 1. 把 *T* 推入栈上。
 2. 执行 *T*，让它调用它需要的任何其它任务。
 3. 从堆栈中弹出 *T*。
 4. 返回其结果。

为了拦截任务调用，`Project` 利用了 Python 的一个关键特性：*函数装饰器*。在定义函数时，允许装饰器处理或转换该函数。`Project.task` 装饰器利用此机会将每个任务打包到另一个函数（包装器）中，这使包装器（它将代表 Project 关注图和堆栈管理）与关注文档处理的任务函数之间的职责明确分离。任务装饰器样板如下所示：

```py
        from functools import wraps

        def task(function):
            @wraps(function)
            def wrapper(*args):
                # wrapper 正文,会调用 function()
            return wrapper
```

这是一个典型的 Python 装饰器声明。然后，可以通过在创建函数的 `def` 顶部的 `@` 字符将其命名为函数：

```py
    @task
    def title_of(filename):
        title, body = parse(filename)
        return title
```

完成此定义后，名称 `title_of` 将引用函数的包装版本。包装器可以通过名称 `function` 访问函数的原始版本，并在适当的时候调用它。Contingent 包装器的主体运行如下内容：

```py
    def task(function):
        @wraps(function)
        def wrapper(*args):
            task = Task(wrapper, args)
            if self.task_stack:
                self._graph.add_edge(task, self.task_stack[-1])
            self._graph.clear_inputs_of(task)
            self._task_stack.append(task)
            try:
                value = function(*args)
            finally:
                self._task_stack.pop()

            return value
        return wrapper
```

此包装器执行几个关键的维护步骤：

 1. 为了方便起见，将任务（一个函数及其参数）打包到一个小对象中。此处的 `wrapper` 为任务函数的包装版本命名。
 2. 如果此任务已由当前正在运行的任务调用，请添加一个边以捕获此任务是已运行任务的输入这一事实。
 3. 忘记我们上次所学的关于这个任务的任何东西，因为这次可能会做出新的决定——例如，如果 API 指南的源文本不再提及 Tutorial，则其 `render()` 将不再要求 Tutorial 文档的 `title_of()`。
 4. 将此任务推入任务堆栈的顶部，以防它在执行工作的过程中调用其它任务。
 5. 调用 `try...finally` 块中的任务，该块确保我们正确地从堆栈中移除已完成的任务，即使它因引发异常而死亡。
 6. 返回任务的返回值，以使此包装器的调用者无法判断他们没有简单地调用普通任务函数本身。

 步骤4和5维护任务堆栈本身，然后由步骤2使用它来执行结果跟踪，这是我们首先构建任务堆栈的全部原因。

 由于每个任务都被它自己的包装器函数副本包围，所以仅仅调用和执行正常的任务堆栈就会产生一个关系图，这是一个不可见的副作用。这就是为什么我们在定义的每个处理步骤周围谨慎地使用包装器：

 ```py
     @task
    def read(filename):
        # body of read

    @task
    def parse(filename):
        # body of parse

    @task
    def title_of(filename):
        # body of title_of

    @task
    def render(filename):
        # body of render
```

感谢这些包装器，当我们调用 `parse('tutorial.txt')` 时，装饰器学习了  `parse` 和 `read` 之间的联系。我们可以通过构建另一个 `Task` 元组并询问如果其输出值发生变化会产生什么后果来询问这种关系：

```py
>>> task = Task(read, ('tutorial.txt',))
>>> print(task)
read('tutorial.txt')
>>> project._graph.immediate_consequences_of(task)
[parse('tutorial.txt')]
```

重读 `tutorial.txt` 文件并发现其内容已更改的结果是我们需要重新执行该文档的 `parse()` 例程。如果我们渲染整个文档集会怎么样？Contingent 能够学习整个构建过程吗？

```py
>>> for filename in 'index.txt', 'tutorial.txt', 'api.txt':
...     print(render(filename))
...     print('=' * 30)
...
<h1>Table of Contents</h1>
<p>
* <a href="tutorial.txt">Beginners Tutorial</a>
* <a href="api.txt">API Reference</a>
<p>
==============================
<h1>Beginners Tutorial</h1>
<p>
Welcome to the tutorial!
We hope you enjoy it.
<p>
==============================
<h1>API Reference</h1>
<p>
You might want to read
the <a href="tutorial.txt">Beginners Tutorial</a> first.
<p>
```

成功了！从输出中，我们可以看到，我们的转换用文档标题代替了源文档中的指令，这表明 Contingent 能够发现构建文档所需的各种任务之间的联系。

![图4](/contingent/markdown/img/figure4.png)

通过观察一个任务通过 `task` 包装器调用另一个任务，`Project` 已经自动学习了输入和结果的图。因为它有一个完整的结果图可供使用，所以如果任何任务的输入发生变化，Contingent 都知道需要重建的所有内容。

## 追赶结果

一旦初始构建运行到完成，Contingent 需要监视输入文件的更改。当用户完成新的编辑并运行“保存”时，需要调用 `read()` 方法及其结果。

这将要求我们按照与创建图时相反的顺序来遍历图。你还记得，它是通过为 API 引用调用 `render()` 并调用 `parse()` 最终调用 `read()` 任务而构建的。现在我们转向另一个方向：我们知道 `read()` 现在将返回新内容，我们需要弄清楚下游将产生什么结果。

编译结果的过程是一个递归的过程，因为每个结果本身都可以有依赖它的任务。我们可以通过重复调用图来手动执行这种递归。（请注意，我们在这里利用了这样一个事实：Python 提示符保存了最后一个显示在名称 `_`下的值，以便在后续表达式中使用。）

```py
>>> task = Task(read, ('api.txt',))
>>> project._graph.immediate_consequences_of(task)
[parse('api.txt')]
>>> t1, = _
>>> project._graph.immediate_consequences_of(t1)
[render('api.txt'), title_of('api.txt')]
>>> t2, t3 = _
>>> project._graph.immediate_consequences_of(t2)
[]
>>> project._graph.immediate_consequences_of(t3)
[render('index.txt')]
>>> t4, = _
>>> project._graph.immediate_consequences_of(t4)
[]
```

这种反复查找直接结果的递归任务，只有在我们到达没有进一步结果的任务时才停止，这是一个足够基本的图操作，它由 `Graph` 类上的方法直接支持：

```py
>>> # Secretly adjust pprint to a narrower-than-usual width:
>>> _pprint = pprint
>>> pprint = lambda x: _pprint(x, width=40)
>>> pprint(project._graph.recursive_consequences_of([task]))
[parse('api.txt'),
 render('api.txt'),
 title_of('api.txt'),
 render('index.txt')]
```

事实上，`recursive_consequences_of()` 试图更聪明一点。如果某个特定任务作为其它几个任务的下游结果重复出现，则应注意在输出列表中仅提及一次，并将其移到接近末尾的位置，以便它只出现在作为其输入的任务之后。这种智能由拓扑排序的经典深度优先实现提供支持，这该法通过一个隐藏的递归辅助函数并用 Python 编写。请查看 `graphlib.py` 源代码以获取细节。

如果在检测到变化后，我们小心地在递归结果中重新运行每一个任务，那么 Contingent 将能够避免重建太少。然而，我们的第二个挑战是避免重建过多。请再次参阅图4，我们希望避免每次 `tutorial.txt` 更改都重建这三个文档，因为大多数编辑可能不会影响其标题，而只影响其正文。如何做到这一点？

解决方案是使图的重新计算依赖于缓存。当逐步处理更改的递归结果时，我们将只调用输入与上次不同的任务。

此优化将涉及最终的数据结构。我们将为 `Project` 提供一个 `_todo` 集合，用它来记住至少有一个输入值已更改因此需要重新执行的任务。因为只有 `_todo` 中的任务过期，构建过程可以跳过运行任何出现在那里的任务。

同样，Python 方便统一的设计使得这些特性非常容易编写代码。因为任务对象是可散列的，所以 `_todo` 可以是一个通过标识记住任务项的 set 集合，保证任务永远不会出现两次，而以前运行的返回值的 `_cache` 可以是一个以任务为键的 dict。

更准确地说，只要 `_todo` 非空，重建步骤就必须保持循环。在每个循环中，它应该：

- 调用 `recursive_consequences_of()` 并传入 `_todo` 中列出的每个任务。返回值不仅是 `_todo` 任务本身的一个列表，还包括它们下游的每个任务，换句话说，如果这次输出不同，可能需要重新执行的每个任务。

- 对于列表中的每个任务，请检查它是否列在 `_todo` 中。如果没有，那么我们可以跳过运行它，因为我们在它的上游重新调用的所有任务都没有产生一个需要重新计算任务的新返回值。

- 但是，对于在到达时确实在 `_todo` 中列出的任何任务，我们都需要要求它重新运行并重新计算其返回值。如果任务包装函数检测到这个返回值与旧的缓存值不匹配，那么则在我们将其返回递归结果列表之前，它的下游任务将自动添加到 `_todo` 中。

当我们到达列表末尾时，每个可能需要重新运行的任务实际上都应该重新运行。但以防万一，我们将检查 `_todo`，如果它还不是空的，会再试一次。即使对于快速变化的依赖树，这也应该很快解决。只有一个循环，例如，任务 A 需要任务 B 的输出，而任务 B 本身也需要任务 A 的输出，才会使构建器处于无限循环中，并且前提是它们的返回值永远不稳定。幸运的是，实际的构建任务通常没有循环。

让我们通过一个例子来跟踪该系统的行为。

假设你编辑 `tutorial.txt` 同时更改标题和正文内容。我们可以通过修改文件系统 dict 中的值来模拟：

```py
>>> filesystem['tutorial.txt'] = """
... The Coder Tutorial
... ------------------
... This is a new and improved
... introductory paragraph.
... """
```

现在内容已经更改，我们可以要求项目重新运行 read() 任务，方法是使用它的 cache_off() 上下文管理器暂时禁止它返回给定任务和参数的旧缓存结果：

```py
>>> with project.cache_off():
...     text = read('tutorial.txt')
```

新的 tutorial 文本现在已读入缓存。需要重新执行多少个下游任务？

为了帮助我们回答这个问题，Project 类支持一个简单的跟踪工具，它将告诉我们在重建过程中执行了哪些任务。因为以上更改为 tutorial.txt 影响到它的正文和标题，所有下游的内容都需要重新计算：

```py
>>> project.start_tracing()
>>> project.rebuild()
>>> print(project.stop_tracing())
calling parse('tutorial.txt')
calling render('tutorial.txt')
calling title_of('tutorial.txt')
calling render('api.txt')
calling render('index.txt')
```

回顾一下图4，你可以看到，正如预期的那样，每个任务都是 `read('tutorial.txt')` 的直接结果或下游结果。

但是如果我们再次编辑它，且这次保留标题不变呢？

```py
>>> filesystem['tutorial.txt'] = """
... The Coder Tutorial
... ------------------
... Welcome to the coder tutorial!
... It should be read top to bottom.
... """
>>> with project.cache_off():
...     text = read('tutorial.txt')
```

这个小的、有限的更改应该不会对其他文档产生影响。

```py
>>> project.start_tracing()
>>> project.rebuild()
>>> print(project.stop_tracing())
calling parse('tutorial.txt')
calling render('tutorial.txt')
calling title_of('tutorial.txt')
```

成功！只重建了一个文档。`title_of()` 在给定新的输入文档时返回了相同的值，这意味着所有进一步的下游任务都不会受到更改的影响，并且不会被重新调用。

## 总结

在某些语言和编程方法下，Contingent 将成为一个令人窒息的小类森林，问题域中的每个概念都有冗长的名称。

然而，在用 Python 编写 Contingent 时，我们跳过了创建诸如`TaskArgument`、`CachedResult` 和 `ConsequenceList` 之类的十几个可能的类。相反，我们借鉴了 Python 使用通用数据结构解决一般问题的强大传统，从而使代码反复使用核心数据结构元组、列表、集合和字典中的一小部分思想。

但这不会造成问题吗？

通用数据结构本质上也是匿名的。我们的 `project._cache` 是一个集合。`Graph` 中上游和下游节点的每个集合也是如此。我们是否有可能看到通用的集合错误消息而不知道是在项目中还是在图实现中查找错误？

事实上，我们并没有风险！

由于封装的谨慎原则，只允许 `Graph` 代码接触图的集合，而 `Project` 代码接触项目的集合。如果在项目的后期阶段，集合操作返回错误，就不会有歧义。发生错误时最内部执行方法的名称必然会将我们指向错误所涉及的类和集合。只要我们将传统的下划线放在数据结构属性前面，然后小心不要从类外部的代码中接触它们，就没有必要为数据类型的每个可能的应用程序创建 `set` 的子类。

Contingent 演示了来自划时代的书籍 *Design Patterns* 的外观（Facade）模式对于精心设计的 Python 程序有多么关键。并不是 Python 程序中的每个数据结构和数据片段都是自己的类。相反，在代码的概念性支点处，类的使用是有节制的，在这种情况下，一个大的概念（如依赖关系图的概念）可以被包装成一个隐藏在其下面的简单泛型数据结构细节的外观。

外观角色之外的代码列出了它需要的大概念和它想要执行的操作。在外观角色的内部，程序员操纵 Python 编程语言的小而方便的移动部件来实现操作。

