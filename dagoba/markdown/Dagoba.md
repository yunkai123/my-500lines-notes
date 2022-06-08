# Dagoba：一个内存中的图形数据库

## 作者介绍

Dann喜欢和他两岁的孩子建造东西，比如编程语言，数据库，分布式系统，聪明友善的社区以及小马城堡。

## 序言

"When we try to pick out anything by itself we find that it is bound fast by a thousand invisible cords that cannot be broken, to everything in the universe." —John Muir

"What went forth to the ends of the world to traverse not itself, God, the sun, Shakespeare, a commercial traveller, having itself traversed in reality itself becomes that self." —James Joyce

很久以前，当世界还很年轻时，所有数据都在一个文件中愉快地传输。如果你想让数据越过围栏，只需将围栏设置在其路径上，然后每个数据依次跳过。打卡进，打卡出。生活轻松，编程轻而易举。

然后随机访问革命到来，数据在山坡上自由放牧。管理数据已成为一个值得关注的问题：如果你可以随时访问任何数据，那么你如何知道接下来要选择哪个呢？技术已经进步，可以通过在记录项[^items]之间形成链接来把数据关进栅栏，通过链接的集合让成组的数据形成编队。查询数据就像挑选一只绵羊，并获取与之相关的一切。

后来的程序员脱离了这一传统，为如何聚合数据添加了一套规则[^relationaltheory]。与其将完全不同的数据直接捆绑在一起，不如将它们按内容聚类，将数据分解成小片段，收集起来，并用名字标签分类。提出查询后，会导致将部分分解的数据（关系学家称为“正常”的状态）聚集到集合中并返回给程序员。

在许多已记录的历史中，这种关系模型至高无上。经过了两次主要的语言战争和无数次小规模冲突，它的统治地位受到了挑战。它通过同一个模型提供你查询的一切，导致效率低下、笨重且缺乏可伸缩性。一直以来这都是程序员愿意付出的代价。然后互联网出现了。

分布式革命再次改变了一切。数据摆脱了空间限制，在机器之间传输。使用CAP的理论家打破了关系型数据的垄断，为新的数据管理技术打开了大门，其中一些最早可以追溯到管理随机访问数据的尝试。我们将研究其中之一的图形数据库。

[^items]:最早的数据库设计之一是分层模型，它将记录项分组为树状的层次结构，现在仍然用作 IBM 的 IMS 产品（一种高速事务处理系统）的基础。它的影响还体现在 XML、文件系统和地理信息存储方面。由 Charles Bachmann 发明并由 CODASYL 标准化的网络模型，通过允许多个父代，形成一个 DAG 而不是树来推广层次模型。这些导航数据库模型在20世纪60年代开始流行，并一直占据主导地位，直到80年代性能的提高使关系数据库可用。

[^relationaltheory]:edgarf.Codd 在 IBM 工作时发展了关系数据库理论，但 Big Blue 担心关系数据库会蚕食 IMS 的销售。虽然 IBM 最终构建了一个名为 System R 的研究原型，但它基于一种新的非关系语言 SEQUEL，而不是 Codd 最初的 Alpha 语言。SEQUEL 语言被 Larry Ellison 在发布前的会议论文的基础上复制到他的 Oracle 数据库中，并将其名称更改为SQL，以避免商标争议。

## 做一个

在本文中，我们将建立一个图数据库[^dagoba]。在构建它时，我们将探索问题空间，为我们的设计决策生成多个解决方案，比较这些解决方案以了解它们之间的权衡取舍，最后为我们的系统选择正确的解决方案。本项目会更加注重代码简洁性，但是这个过程可以反映所自古以来软件专业人员所使用的方法。本章的目的是教授你这个过程，并建立一个图数据库[^purpose]。

[^dagoba]: 这个数据库最初是一个管理有向无环图（DAG）的库。它的名字“Dagoba”最初打算在结尾处加上一个无声的“h”，以向这个充满沼泽的虚构星球致敬，但是有一天，我们读到一块巧克力的背面，发现没有 h 版本指的是默默思考事物之间联系，这似乎更加合适。

[^purpose]: 本文的目的是教授这个过程，建立一个图数据库，并获得乐趣。

使用图数据库让我们能够以优雅的方式解决一些有趣的问题。图是一种非常自然的数据结构，用于探索事物之间的联系。图由一组顶点和一组边构成。换句话说，它是一组由线连接的点。数据库呢？“数据库”就像是数据堡垒。你可以将数据放入其中或从中取出数据。

那么，图数据库可以解决哪些问题？假设你喜欢追踪祖先树：父母，祖父母，表亲，类似这种情况。你想开发一个系统，使你可以进行自然而优雅的查询，例如“谁是 Thor 的有相同（外）祖父母的隔辈表亲？”或“ Freyja 与 Valkyries 是什么关系？”

此数据结构的合理模式是拥有一个实体表和一个关系表。查询 Thor 的父母可能看起来像：

```sql
SELECT e.* FROM entities as e, relationships as r
WHERE r.out = "Thor" AND r.type = "parent" AND r.in = e.id
```

但是，我们如何将其扩展到祖父母呢？ 我们需要执行子查询，或使用其他类型的特定供应商的 SQL 扩展。到隔辈表亲时，我们将写出大量 SQL。

我们想写什么？既简洁又灵活的东西；以自然的方式对查询建模并扩展到其它类似查询的东西。`second_cousins('Thor')` 简洁明了，但是没有给我们带来任何灵活性。上面的 SQL 很灵活，但是缺乏简洁性。

诸如 `Thor.parents.parents.parents.children.children.children` 取得了不错的平衡。这些原语使我们可以灵活地提出许多类似的问题，并且查询简洁自然。但这个特殊的表述给我们带来了过多的结果，因为它包含了堂兄弟姐妹和兄弟姐妹，我们只需要单个结果。

能为我们提供这种接口的最简单的方法是什么？我们可以制作一个顶点列表和一个边列表，就像关系模式一样，然后构建一些辅助函数。它可能看起来像这样：

```js
V = [ 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15 ]
E = [ [1,2], [1,3],  [2,4],  [2,5],  [3,6],  [3,7],  [4,8]
    , [4,9], [5,10], [5,11], [6,12], [6,13], [7,14], [7,15] ]

parents = function(vertices) {
  var accumulator = []
  for(var i=0; i < E.length; i++) {
    var edge = E[i]
    if(vertices.indexOf(edge[1]) !== -1)
      accumulator.push(edge[0])
  }
  return accumulator
}
```

上面函数的本质是遍历一个列表，为用一些代码计算每个项并建立一个结果累加器。但是，这还不够清楚，因为循环构造会引入一些不必要的复杂性。

如果为此目的设计一个更具体的循环结构将会很好。碰巧的是，reduce 函数恰好做到了：给定一个列表和一个函数，它会针对列表中的每个项对函数进行计算，同时在每次计算过程中线程化累加器。

用这种更实用的样式编写的查询更短，更清晰：

```js
parents  = (vertices) => E.reduce( (acc, [parent, child])
         => vertices.includes(child)  ? acc.concat(parent) : acc , [] )
children = (vertices) => E.reduce( (acc, [parent, child])
         => vertices.includes(parent) ? acc.concat(child)  : acc , [] )
```

给定一个顶点列表，我们在边上使用 reduce，如果边的子项在输入列表中，则将边的父项添加到累加器中。children函数相同，但是会检查边的父项以确定是否添加边的子项。

这些函数是有效的JavaScript，但是使用了一些撰写本文时浏览器尚未实现的功能。 此翻译版本在现在可以运行：

```js
parents  = function(x) { return E.reduce(
  function(acc, e) { return ~x.indexOf(e[1]) ? acc.concat(e[0]) : acc }, [] )}
children = function(x) { return E.reduce(
  function(acc, e) { return ~x.indexOf(e[0]) ? acc.concat(e[1]) : acc }, [] )}
```

现在我们可以这样表达：

```js
  children(children(children(parents(parents(parents([8]))))))
```

它向后读，使我们迷失在无数的 `parents` 中，但在其它方面与我们想要的非常接近。花一点时间看一下代码，你能想到改进的方法吗？

我们将边作为全局变量，这意味着每次只能在一个数据库中使用这些辅助函数，这有很大的限制性。

我们也没有使用顶点。这说明什么？这意味着我们需要的一切都在 `edges` 数组中，在这种情况下的正确说法是：顶点值是标量，因此它们独立存在于 `edges` 数组中。如果我们要回答诸如“ Freyja 与 Valkyries 是什么关系？”之类的问题，我们需要向顶点添加更多数据，这意味着使它们成为复合值，且 `edges` 数组应引用顶点而不是复制其值。

我们的边也是如此：它包含一个“入”顶点和一个“出”顶点[^vertexnote]，但没有优雅的方式来包含其它信息。我们需要用它来回答诸如“Loki 有多少继父母？”或“Odin 在 Thor 出生之前生了多少个孩子？”的问题。

你会发现我们两个选择器的代码看起来非常相似，这表明它们可以进行更深层的抽象。

你还有其他问题吗？

[^vertexnote]:请注意，我们将边建模为一对顶点。还要注意，这些对是有序的，因为我们使用的是数组。这意味着我们要建模一个有向图，每个边都有一个起始点和一个结束点。我们的“点和线”视觉模型变成了“点和箭头”模型。这给我们的模型增加了复杂性，因为我们必须追踪边的方向，但同时也允许我们提出更有趣的问题，比如“哪个顶点指向顶点3？”或者“哪个顶点的出边最多？”如果我们需要为无向图建模，我们可以为有向图中的每个现有边添加一条反向边。换个方向可能很麻烦：从无向图模拟有向图。你能想出一个方法吗？

## 创建更好的图

让我们来解决我们发现的问题。将顶点和边设为全局结构会使我们一次只能绘制一张图，但我们希望拥有更多图。为了解决这个问题，我们需要一些结构。 让我们从命名空间开始。

```js
Dagoba = {}                                     // the namespace
```

我们将使用一个对象作为我们的命名空间。JavaScript 中的对象通常只是键/值对的无序集合。在JavaScript中，我们只有四种基本数据结构可供选择，因此我们将大量使用这一结构。（在聚会的时候问一个有趣的问题“ JavaScript的四个基本数据结构是什么？”）

现在我们需要一些图。我们可以使用经典的 OOP 模式来构建这些对象，但是 JavaScript 提供了原型继承，这意味着我们可以构建一个原型对象（我们将其称为 Dagoba.G），然后使用工厂函数实例化该对象的副本。 这种方法的优点是我们可以从工厂返回不同类型的对象，而不是将创建过程绑定到单个类构造函数。 因此，我们得到了一些额外的灵活性。

```js
Dagoba.G = {}                                   // the prototype

Dagoba.graph = function(V, E) {                 // the factory
  var graph = Object.create( Dagoba.G )

  graph.edges       = []                        // fresh copies so they're not shared
  graph.vertices    = []
  graph.vertexIndex = {}                        // a lookup optimization

  graph.autoid = 1                              // an auto-incrementing ID counter

  if(Array.isArray(V)) graph.addVertices(V)     // arrays only, because you wouldn't
  if(Array.isArray(E)) graph.addEdges(E)        //   call this with singular V and E

  return graph
```

我们将接受两个可选参数：顶点列表和边列表。JavaScript在参数方面比较宽松，因此所有命名参数都是可选的，如果未提供，则默认为 `undefined`[^optionalparams]。在构建成图并使用 `V` 和 `E` 参数之前，我们通常会具有顶点和边，但是在创建时没有这些顶点和边并以编程方式构建图也是很常见的[^graphbuilding]。

[^optionalparams]:它在另一个方向上也很宽松：所有函数都是可变参数，所有参数都可以通过 `arguments` 对象按位置使用，这几乎类似于数组，但不完全是。（“可变（Variadic）”是一种奇特的说法，表示函数具有不确定的参数数量。“一个函数有不确定的参数数量”是一种很花哨的说法，表示它需要可变数量的变量。）

[^graphbuilding]:这里的 `Array.isArray` 检查是为了区分我们的两个不同的用例，但是一般来说，我们不会做很多生产代码所期望的验证，以便将重点放在架构而不是垃圾箱上。

然后，我们创建一个新对象，它具有原型的所有优点，而没有原型的缺点。我们为边构建了一个新数组（基本 JS 数据结构之一），为顶点构建了一个新数组，一个名为 `vertexIndex` 的新对象和一个ID计数器，稍后进行介绍。（思考：为什么我们不能将它们放在原型中？）

然后，我们在工厂内部调用 `addVertices` 和 `addEdges` ，因此让我们现在定义它们。

```js
Dagoba.G.addVertices = function(vs) { vs.forEach(this.addVertex.bind(this)) }
Dagoba.G.addEdges    = function(es) { es.forEach(this.addEdge  .bind(this)) }
```

好吧，这太简单了，我们只是将工作传递给 `addVertex` 和 `addEdge` 。我们现在应该定义它们。

```js
Dagoba.G.addVertex = function(vertex) {         // accepts a vertex-like object
  if(!vertex._id)
    vertex._id = this.autoid++
  else if(this.findVertexById(vertex._id))
    return Dagoba.error('A vertex with that ID already exists')

  this.vertices.push(vertex)
  this.vertexIndex[vertex._id] = vertex         // a fancy index thing
  vertex._out = []; vertex._in = []             // placeholders for edge pointers
  return vertex._id
}
```

如果顶点尚不具有 `_id` 属性，则使用 autoid 为其分配一个。[^autoid]如果 _id 已存在于图形中的某个顶点上，则我们会废弃新顶点。这在什么时候会发生？ 并且顶点到底是什么？

[^autoid]:这里为什么我们不能使用 `this.vertices.length`？

在传统的面向对象的系统中，我们希望找到一个顶点类，所有顶点都将是它的一个实例。这里我们将采用另一种方法，将包含三个属性 `_id`，`_in` 和 `_out` 的任何对象视为顶点。这是为什么？最终，归根结底是要让 Dagoba 来控制与主机应用程序共享哪些数据。

如果我们在 `addVertex` 函数内创建一些 `Dagoba.Vertex` 实例，则我们的内部数据将永远不会与主机应用程序共享。如果我们接受 `Dagoba.Vertex` 实例作为 `addVertex` 函数的参数，则主机应用程序可以保留指向该顶点对象的指针并在运行时对其进行操作，从而打破不变量。

因此，如果我们创建一个顶点实例对象，就必须预先决定是将我们将提供的数据复制到一个新对象中（有可能使我们的空间使用量增加一倍）还是允许主机应用程序不受限制地访问数据库对象。这是在性能和数据保护之间进行取舍，正确的平衡取决于你的特定用例。

在顶点的属性上的鸭子类型（duck typing）允许我们在运行时做出决定，是深拷贝[^deepcopying]输入数据还是直接将其用作顶点[^vertexdecision]。我们并不总是希望将平衡安全性和性能的责任交给用户，但是由于这两套用例差异很大，因此灵活性很重要。

现在我们有了新的顶点，我们将其添加到图的顶点列表中，将其添加到 vertexIndex 中以通过 _id 进行有效查找，并向其添加两个附加属性：_out 和 _in，这两个属性均是边[^edgelistadt]的列表。

[^deepcopying]:当面临由于深度复制而导致的空间泄漏时，解决方案是使用路径复制持久数据结构，该结构只允许对$\log{}N$额外空间进行无突变的更改。但问题仍然存在：如果宿主应用程序保留了指向顶点数据的指针，那么它可以随时对该数据进行更改，无论我们在数据库中施加了什么限制。唯一可行的解决方案是深度复制顶点，这将使我们的空间使用量加倍。Dagoba 的原始用例涉及到被宿主应用程序视为不可变的顶点，这允许我们避免这个问题，但需要用户遵守一定的规则。

[^vertexdecision]:我们可以根据一个 Dagoba 级别的配置参数、一个特定于图的配置或者可能是某种启发式方法来做出这个决策。

[^edgelistadt]:我们使用术语列表来表示需要推送和迭代操作的抽象数据结构。我们使用 JavaScript 的“array”具体数据结构来实现列表抽象所需的 API。从技术上讲，“边列表”和“边数组”都是正确的，因此我们在给定时刻使用哪个取决于上下文：如果我们依赖 JavaScript 数组的特定细节，比如 .length 属性，我们将称之为“边数组”。否则，我们说“边列表”，表示任何列表实现都足够了。

```js
Dagoba.G.addEdge = function(edge) {             // accepts an edge-like object
    edge._in  = this.findVertexById(edge._in)
    edge._out = this.findVertexById(edge._out)

    if(!(edge._in && edge._out))
        return Dagoba.error("That edge's " + (edge._in ? 'out' : 'in')
                                        + " vertex wasn't found")

    edge._out._out.push(edge)                     // edge's out vertex's out edges
    edge._in._in.push(edge)                       // vice versa

    this.edges.push(edge)
```

首先，我们找到边连接的两个顶点，然后，如果缺少任何一个顶点，则拒绝边。我们将使用一个辅助函数来记录拒绝时的错误。所有错误都会通过此辅助函数传递，因此我们可以基于每个应用程序覆盖其行为。我们以后可以扩展它，以允许注册 `onError` 处理程序，以便主机应用程序可以链接自己的回调而不会覆盖辅助函数。我们可能允许按图，按应用程序或按两种方式注册此类处理程序，具体取决于所需的灵活性级别。

```js
Dagoba.error = function(msg) {
  console.log(msg)
  return false
}
```
然后，将新边添加到两个顶点的边列表中：边的外顶点的外边列表，以及内顶点的内边列表。

这就是我们现在需要的所有图结构！

## 输入查询

该系统实际上只有两部分：保存图的部分和回答有关图的问题的部分。如我们所见，保存图的部分非常简单，查询部分有些棘手。

我们将和前面一样从一个原型和一个查询工厂开始。

```js
Dagoba.Q = {}

Dagoba.query = function(graph) {                // factory
  var query = Object.create( Dagoba.Q )

  query.   graph = graph                        // the graph itself
  query.   state = []                           // state for each step
  query. program = []                           // list of steps to take
  query.gremlins = []                           // gremlins for each step

  return query
}
```

下面介绍一些新概念。

*program* 是一系列的*step*。每个步骤就像一条流水线中的管道，数据进入一端，以某种方式转换，然后流出另一端。我们的管道并不能完全这样工作，但和这种方式类似。

程序中的每个步骤都有*state*，而 query.state 是每个步骤状态的列表，该状态的索引与 query.program 中的步骤列表相关。

*gremlin* 是一种通过图来执行我们的指令的生物。在数据库中找到 gremlin 可能是一件令人惊讶的事情，但是它们的历史可以追溯到 Tinkerpop 的 Blueprints 以及 Gremlin 和 Pacer 查询语言。他们记得去过的地方，并允许我们找到有趣问题的答案。

还记得我们想回答的有关 Thor 的有相同（外）祖父母的隔代表亲的问题吗？我们认为 Thor.parents.parents.parents.children.children.children 是一种很好的表达方式。每个父母或孩子实例都是我们程序的一个步骤。 这些步骤中的每一步都包含对其 pipetype 的引用，pipetype 是执行步骤操作的函数。

我们的实际系统中的查询可能类似于：

```js
    g.v('Thor').out().out().out().in().in().in()
```

每个步骤都是一个函数调用，因此它们可以接受*参数（arguments）*。解释器将步骤的参数传递给步骤的 pipetype 函数，因此在查询 g.v('Thor').out(2,3)中，out类型的  pipetype 函数将接收到[2，3]作为其第一个参数。

我们需要一种向查询添加步骤的方法。下面是一个辅助函数：

```js
Dagoba.Q.add = function(pipetype, args) { // add a new step to the query
    var step = [pipetype, args]
    this.program.push(step)                 // step is a pair of pipetype and its args
    return this
}
```

每个步骤都是一个复合实体，将 pipetype 函数与要应用于该函数的参数相结合。在这个阶段，我们可以将这两部分组合成一个偏应用函数（partially applied function），而不是使用元组 [^tupleadt]，但是这样我们就失去了一些稍后将被证明有用的内省功能。

[^tupleadt]:元组是另一种抽象数据结构，它比列表更受约束。特别是元组有固定的大小：在本例中，我们使用的是2元组（在数据结构研究人员的技术术语中也称为“对”）。对于未来的实现者来说，使用这个术语来描述所需的最受约束的抽象数据结构是一个不错的选择。

我们将使用一小组查询初始化器从图中生成新的查询。这是我们大多数例子的开头：v方法。它构建一个新的查询，然后使用 add 辅助函数填充初始查询程序。这使用了顶点管道类型，我们很快就会看到它。

```js
Dagoba.G.v = function() {                       // query initializer: g.v() -> query
    var query = Dagoba.query(this)
    query.add('vertex', [].slice.call(arguments)) // add a step to our program
    return query
}
```

注意 [].slice.call（arguments）是 JS 的说法，意思是“请向我传递此函数的参数数组”。参数已经是一个数组也是可以的，因为它在许多情况下的行为都像一个数组，但是它缺少我们在现代 JavaScript 数组中使用的许多功能。

## 立即加载的问题

在研究管道类型本身之前，我们先看看激动人心的执行策略领域。有两种主要的思想流派：按值调用，它们严格要求在应用函数之前对所有的参数进行处理。他们的对立派别，按需调用，满足于拖延到最后一刻才做任何事情，总而言之，h后者是延迟加载的。

JavaScript 是一种严格的语言，将在每个步骤被调用时对其进行处理。我们期望对 `g.v('Thor').out().in()` 的处理是首先找到 Thor 顶点，然后找到通过输出边与其相连的所有顶点，最终从这些顶点的每一个中返回它们通过输入边连接的所有顶点。

使用非严格语言，我们将得到相同的结果，执行策略在这里并没有多大区别。 但是，如果我们增加了一些额外的调用呢？考虑到 Thor 的连通性，我们的 `g.v('Thor').out().out().out().in().in().in()` 查询可能会产生很多结果。事实上，由于我们没有对顶点列表限制唯一性，他可能会产生比整个图中顶点更多的结果。

我们可能只想获取一些唯一的结果，因此我们将查询做一些更改：`g.v('Thor').out().out().out().in().in().in().unique().take(10)`。现在，我们的查询最多产生 10 个结果。但是，如果我们对表达式进行计算，会发生什么？在仅返回前 10 个结果之前，我们仍然需要计算数十亿个结果。

所有图数据库都必须支持一种机制，以尽可能减少工作量，并且大多数数据库都选择某种形式的非严格计算来执行。由于我们正在构建自己的解释器，因此可以对程序进行延迟计算，但是可能需要应对某些后果。

## 我们的思维模型对计算策略的影响

到目前为止，我们用来计算的思维模型非常简单：

- 请求一组顶点
- 将返回的集合作为输入传递给管道
- 根据需要重复步骤

我们希望为我们的用户保留该模型，因为它更易于推论，但是正如我们已经看到的那样，我们不再将该模型用于实现。让用户思考与实际实现不同的模型会带来很多麻烦。泄露抽象是这种形式的一个小规模版本。它会再一定程度上导致用户产生挫折感、认知失调和愤怒。

不过，对于这种欺骗，我们的情况几乎是最佳的：无论执行模式如何，任何查询的答案都是相同的。唯一的区别是性能。权衡是让所有用户在使用系统之前学习更复杂的模型，还是强制用户子集从简单模型转换为复杂模型，以便更好地了解查询性能。

做出决定时要考虑的一些因素包括：

- 学习简单模型与更复杂模型的相对认知困难；
- 首先使用简单模型然后前进到复杂模型而不是跳过简单模型并仅学习复杂模型而施加的额外认知负荷；
- 进行过渡所需的用户子集，包括比例大小，认知可用性，可用时间等。

在我们的案例中，这种权衡是有意义的。在大多数情况下，查询将以足够快的速度返回结果，从而使用户不必担心优化查询结构或学习更深入的模型。那些仅针对大型数据集编写高级查询的用户，他们也很有可能是最有能力过渡到新模型的用户。另外，我们希望在学习更复杂的模型之前，使用简单模型只会增加较小的难度。

我们将很快对此新模型进行更详细的介绍，但与此同时，在下一节中，请牢记以下要点：

- 每个管道一次返回一个结果，而不是一组结果。每个管道可以在计算查询时被多次激活。
- 读/写头控制着接下来激活哪个管道。头部从管道的末端开始，其移动由当前活动管道的结果引导。
- 这个结果可能是前面提到的 gremlin 之一。每个 gremlin 代表一个潜在的查询结果，它们通过管道携带状态。gremlin 会使头部向右移动。
- 管道可以返回“pull”的结果，它向头部发出信号，表示它需要输入并将其向右移动。
- 结果为“done”告诉头部之前没有任何东西需要再次激活，并将头部向左移动。

## 管道类型

管道类型构成了我们系统的核心。一旦我们理解了它们每个的工作原理，我们将有一个更好的基础来理解它们在解释器中如何一起被调用和排序。

我们将首先创建一个放置管道类型的地方，以及添加新管道类型的方法。

```js
Dagoba.Pipetypes = {}

Dagoba.addPipetype = function(name, fun) {              // adds a chainable method
  Dagoba.Pipetypes[name] = fun
  Dagoba.Q[name] = function() {
    return this.add(name, [].slice.apply(arguments)) }  // capture pipetype and args
}
```

管道类型的函数被添加到管道类型列表中，然后将新方法添加到查询对象。每个管道类型都必须具有相应的查询方法。该方法及其参数一起添加到查询程序新步骤中。

当我们计算 `g.v('Thor').out('parent').in('parent')` 的时候，`v` 方法调用并返回一个查询对象，`out` 方法添加一个新步骤并返回一个查询对象，然后 `in` 方法做同样的事。这就是我们实现方法链式 API 的原因。

请注意，添加具有相同名称的新管道类型将替换已有管道类型，从而允许在运行时修改已有管道类型。这个决策有什么代价？还有哪些选择？

```js
Dagoba.getPipetype = function(name) {
  var pipetype = Dagoba.Pipetypes[name]                 // a pipetype is a function

  if(!pipetype)
    Dagoba.error('Unrecognized pipetype: ' + name)

  return pipetype || Dagoba.fauxPipetype
}
```

如果找不到管道类型，则会生成一个错误并返回默认管道类型，该默认管道类型是一个空管道：消息从一侧进入，传递到另一侧。

```js
Dagoba.fauxPipetype = function(_, _, maybe_gremlin) {   // pass the result upstream
  return maybe_gremlin || 'pull'                        // or send a pull downstream
}
```

看到那些下划线了吗？我们使用它们来标记在我们的函数中不使用的参数。大多数其它管道类型将使用三个参数，并具有所有三个参数的名称。这样我们能够一眼分辨出特定管道类型所依赖的参数。

这种下划线技术也很重要，因为它使注释排列得很美观。如果程序“必须写得能供人阅读，机器执行只是附带”，那么我们的首要关注点应该是使代码变得更漂亮。

### 顶点

我们的大多数管道类型都将使用 gremlin 并生成更多的 gremlin，但是这种特定的管道类型仅通过字符串即可生成 gremlin。给定一个顶点 ID，它将返回一个新的 gremlin。给定一个查询，它将找到所有匹配的顶点，并一次生成一个新的 gremlin，直到处理完成为止。

```js
Dagoba.addPipetype('vertex', function(graph, args, gremlin, state) {
  if(!state.vertices)
    state.vertices = graph.findVertices(args)       // state initialization

  if(!state.vertices.length)                        // all done
    return 'done'

  var vertex = state.vertices.pop()                 // OPT: requires vertex cloning
  return Dagoba.makeGremlin(vertex, gremlin.state)  // gremlins from as/back queries
})
```

我们首先检查是否已经收集了匹配的顶点，否则我们尝试找到一些顶点。如果有顶点，就弹出一个，并返回一个位于该顶点上的新 gremlin。每个 gremlin 都携带着自己的状态，就像日记记录了去过的地方以及在旅程中看到的有趣事情。如果我们收到一个 gremlin 作为此步骤的输入，我们将为退出时的 gremlin 复制其日志。

请注意，我们在这里直接更改 `state` 参数，而没有将其传递回去。另一种选择是返回一个对象而不是 gremlin 或信号，然后以这种方式返回状态。这使我们的返回值更加复杂，并创建了一些额外的垃圾[^garbage]。如果 JS 允许多个返回值，会使此选项更加优雅。

[^garbage]:寿命很短的垃圾，这是第二优先选择的垃圾。

不过，我们仍然需要找到一种方法来处理这些突变，因为调用位置保持对原始变量的引用。如果我们有某种方法来确定某个特定的引用是否是“唯一的”，即它是对该对象的唯一引用呢？

如果我们知道一个引用是唯一的，那么我们将获得不变性的好处，同时避免了昂贵的写时复制方案或复杂的持久数据结构。仅一个引用，我们无法确定对象是否已被更改或新对象是否已随我们的请求一起返回：保持了“观察到的不变性” [^obsimmutability]。

[^obsimmutability]:对同一个可变数据结构的两个引用就像一对对讲机，允许任何持有它们的人直接通信。这些对讲机可以从一个函数传递到另一个函数，并且可以克隆出大量的对讲机。这完全颠覆了代码已经拥有的自然通信通道。在一个没有并发的系统中，你有时可以摆脱它，但是会引入多线程或异步行为，所有这些对讲机的噪音都会成为障碍。

有一些常见的解决方法：在静态类型的系统中，我们可以利用唯一性类型[^uniquenesstypes]来保证在编译时每个对象只有一个引用。如果我们有一个引用计数器[^referencecounter]，即使只是廉价的两位粘滞计数器，我们就可以在运行时知道一个对象只有一个引用，并利用这一点为我们带来好处。

[^uniquenesstypes]:唯一性类型使用 Clean 语言去除，并且与线性类型有非线性关系，线性类型本身就是子结构类型的一个子类型。

[^referencecounter]:大多数现代 JS 运行时都使用分代垃圾收集器，并且有意将该语言与引擎的内存管理保持一定距离，以减少编程不确定性的来源。

JavaScript 没有这两种功能，但是如果我们真的非常严格地遵守规则，我们可以得到几乎相同的效果。这也是我们接下来要做到的。

### In-N-Out

浏览图就像点汉堡一样简单。这两行为我们设置了 in 和 out 管道类型。

```js
Dagoba.addPipetype('out', Dagoba.simpleTraversal('out'))
Dagoba.addPipetype('in',  Dagoba.simpleTraversal('in'))
```

`simpleTraversal` 函数返回一个接受 gremlin 作为输入的管道类型处理程序，并在每次查询时生成一个新的 gremlin。一旦这些 gremlin 消失了，它就会发送回“pull”请求，从其前身那里获得新的 gremlin。

```js
Dagoba.simpleTraversal = function(dir) {
  var find_method = dir == 'out' ? 'findOutEdges' : 'findInEdges'
  var edge_list   = dir == 'out' ? '_in' : '_out'

  return function(graph, args, gremlin, state) {
    if(!gremlin && (!state.edges || !state.edges.length))     // query initialization
      return 'pull'

    if(!state.edges || !state.edges.length) {                 // state initialization
      state.gremlin = gremlin
      state.edges = graph[find_method](gremlin.vertex)        // get matching edges
                         .filter(Dagoba.filterEdges(args[0]))
    }

    if(!state.edges.length)                                   // nothing more to do
      return 'pull'

    var vertex = state.edges.pop()[edge_list]                 // use up an edge
    return Dagoba.gotoVertex(state.gremlin, vertex)
  }
}
```

前几行处理 in 版本和 out 版本之间的差异。然后，我们准备返回我们的 `pipetype` 函数，该函数看起来很像我们刚刚看到的顶点管道类型。不同的是，这里需要一个 gremlin，而顶点管道类型则生成 gremlin。

我们可以看到这里出现了同样的情况，增加了查询初始化步骤。如果没有 gremlin 并且我们没有可用的边，那么我们就拉取。如果我们有一个 gremlin，但尚未设置状态，那么我们会找到沿正确方向的边并将其添加到我们的状态。如果有一个 gremlin，但是它的当前顶点没有合适的边，那么我们就拉取。最后，我们取出一条边，并在其指向的顶点上返回一个新克隆的 gremlin。

看一下这段代码，我们看到在三个子句中的 `!state.edges.length` 重复了！。试图对此进行重构以降低条件复杂性是很诱人的。但有两个问题使我们无法这样做。

一个相对较次要：第三个 `!state.edges.length` 表示与前两个不同的东西，因为 `state.edges` 在第二个和第三个条件之间已更改。 实际上，这鼓励我们进行重构，因为在一个函数中使用同一个标签代表两个不同的东西，通常并不理想。

第二个更严重。这不是我们正在编写的唯一管道类型函数，并且我们将看到这些查询初始化和/或状态初始化的想法反复出现。在编写代码时，总是要在结构化质量和非结构化质量之间进行平衡。太多的结构会让你在样板和抽象复杂性上付出高昂的代价。结构太少，你就得把所有的管道细节都记在脑子里。

在这种情况下，大约有十几种管道类型，正确的选择似乎是尽可能相似地设置每种管道类型函数的样式，并用注释标记组成部分。因此，我们抵抗了重构特定管道类型的冲动，因为这样做会降低一致性，但是我们也不想为查询初始化、状态初始化等设计正式的结构抽象。如果有数百种管道类型，则后一种选择可能是正确的：抽象的复杂性成本是恒定的，而收益则随单位数量线性增长。 当处理这么多移动部件时，你可以采取的任何措施来加强其中的规则性都是有帮助的。

### Property

让我们暂停片刻考虑基于我们已经看到的三种管道类型的示例查询。我们可以用以下方式查找 Thor 的祖父母[^runnote]：

[^runnote]:查询末尾的 `run()` 调用解释器并返回结果。

```js
g.v('Thor').out('parent').out('parent').run()
```

但是，如果我们想要他们的名字呢？我们可以在末尾放一张地图：

```js
g.v('Thor').out('parent').out('parent').run()
 .map(function(vertex) {return vertex.name})
```

这是一个常见的操作，我们希望编写更多类似的内容：

```js
g.v('Thor').out('parent').out('parent').property('name').run()
```

使用这种方式，属性管道是查询的组成部分，而不是后面附加的内容。我们将很快看到这样做的好处。

```js
Dagoba.addPipetype('property', function(graph, args, gremlin, state) {
  if(!gremlin) return 'pull'                                  // query initialization
  gremlin.result = gremlin.vertex[args[0]]
  return gremlin.result == null ? false : gremlin             // false for bad props
})
```

这里查询初始化很简单：如果没有 gremlin，我们拉取。如果存在 gremlin，则将其结果设置为属性的值。然后，gremlin 可以继续前进。如果它通过了最后一个管道，它将收集结果并从查询中返回。并非所有的 gremlin 都具有结果（result）属性。 那些不返回其最近访问的顶点的没有。

请注意，如果该属性不存在，我们将返回 `false` 而不是 gremlin，因此属性管道也可以充当一种过滤器。你能想到此用途吗？在此设计决策中要权衡哪些方面？

### Unique

如果我们想收集 Thor 祖父母的所有孙子孙女（他的堂兄弟姐妹，兄弟姐妹和他自己），我们可以做这样一个查询 `g.v('Thor').in().in().out().out().run()`。不过，这会给我们带来很多重复。事实上至少会有四个托尔本人的。（你能想到什么时候还会有更多吗？）

为了解决这个问题，我们引入了一种称为“unique”的新管道类型。 我们的新查询将产生与孙代一一对应的输出：

```js
  g.v('Thor').in().in().out().out().unique().run()
```

管道类型的实现：

```js
Dagoba.addPipetype('unique', function(graph, args, gremlin, state) {
  if(!gremlin) return 'pull'                                  // query initialization
  if(state[gremlin.vertex._id]) return 'pull'                 // reject repeats
  state[gremlin.vertex._id] = true
  return gremlin
})
```

一个 `unique` 管道纯粹是一个过滤器：它要么使 gremlin 原封不动地通过，要么尝试从前面的管道中拉取出新的 gremlin。

我们通过尝试收集 gremlin 初始化。如果 gremlin 的当前顶点在我们的缓存中，那么我们之前已经看过它，因此我们尝试收集一个新的顶点。否则，我们将 gremlin 的当前顶点添加到缓存中并传递它，十分简单。

### Filter

我们已经看到了两种简单的过滤方法，但是有时我们需要更复杂的约束。如果我们想找到 Thor 所有体重大于身高的兄弟姐妹，该怎么办？以下查询将为我们提供答案：

```js
g.v('Thor').out().in().unique()
 .filter(function(asgardian) { return asgardian.weight > asgardian.height })
 .run()
```

其工作原理如下：

```js
Dagoba.addPipetype('filter', function(graph, args, gremlin, state) {
  if(!gremlin) return 'pull'                                  // query initialization

  if(typeof args[0] == 'object')                              // filter by object
    return Dagoba.objectFilter(gremlin.vertex, args[0])
         ? gremlin : 'pull'

  if(typeof args[0] != 'function') {
    Dagoba.error('Filter is not a function: ' + args[0])
    return gremlin                                            // keep things moving
  }

  if(!args[0](gremlin.vertex, gremlin)) return 'pull'         // gremlin fails filter
  return gremlin
})
```

如果过滤器的第一个参数不是对象或函数，则会触发一个错误，并传递 gremlin。暂停一分钟，然后考虑替代方法。为什么遇到错误还要继续查询？

出现此错误可能有两个原因。首先涉及程序员通过 REPL 或直接在代码中键入查询。运行时，该查询将产生结果，并且还会产生程序员可观察到的错误。程序员随后纠正错误以进一步过滤产生的结果集。或者，系统可以仅显示错误而不产生结果，当修复所有错误将允许显示结果。

第二种可能原因是在运行时动态应用过滤器。这是一个非常重要的场景，因为调用查询的人不一定是查询代码的作者。因为这是在网络上，所以我们的默认规则是始终显示结果，永不中断。通常更可取的是在遇到麻烦时继续战斗，而不是屈服于挫折，并向用户显示严重的错误信息。

对于那些结果显示太少胜于显示太多的情况，可以重写 `Dagoba.error` 以抛出错误，从而规避正常控制流程。

### Take

我们并不总是希望一次就得到所有的结果。有时我们只需要一小部分的结果；比如说我们想要十几个 Thor 的同代人，我们一路回到最开始：

```js
g.v('Thor').out().out().out().out().in().in().in().in().unique().take(12).run()
```

如果没有 take 管道，查询可能需要很长时间才能运行，但是由于我们的延迟加载求值策略，使用 take 管道的查询非常高效。

有时候我们一次只想要一个：我们会处理结果，处理它，然后再回来拿另一个。这种管道类型也允许我们这样做。

```js
q = g.v('Auðumbla').in().in().in().property('name').take(1)

q.run() // ['Odin']
q.run() // ['Vili']
q.run() // ['Vé']
q.run() // []
```

我们的查询可以在异步环境中运行，允许我们根据需要收集更多的结果。当我们用完时，会返回一个空数组。

```js
Dagoba.addPipetype('take', function(graph, args, gremlin, state) {
  state.taken = state.taken || 0                              // state initialization

  if(state.taken == args[0]) {
    state.taken = 0
    return 'done'                                             // all done
  }

  if(!gremlin) return 'pull'                                  // query initialization
  state.taken++
  return gremlin
})
```

如果 `state.taken` 不存在，则将其初始化为零。JavaScript 具有隐式强制，但我们需要将 `undefined` 强制转换为 `NaN`，因此在此处必须使用显式[^explicit]。

[^explicit]:有些人会认为最好一直都是显式的。其他人则认为，一个好的隐式系统可以使代码更简洁、可读，样板文件更少，可触发的bug更少。我们都同意的一点是，要有效地使用 JavaScript 的隐式强制，就需要记住很多非直观的特殊情况，这对新手来说是个雷区。

然后，当 `state.taken` 到达 `args[0]` 时，我们返回“done”，将前面的管道密封起来。我们还重置了 `state.taken` 计数器，使我们以后可以重复查询。

在查询初始化之前，我们执行了这两个步骤以处理 `take(0)` 和 `take()`[^takereturn]的情况。然后我们增加计数器，返回 gremlin。

[^takereturn]:你希望每一个返回什么？他们实际返回了什么？

### As

接下来的四个管道类型作为一个组工作，以允许更高级的查询。这仅允许你标记当前的顶点。我们将在接下来的两个管道类型中使用该标记。

```js
Dagoba.addPipetype('as', function(graph, args, gremlin, state) {
  if(!gremlin) return 'pull'                                  // query initialization
  gremlin.state.as = gremlin.state.as || {}                   // init the 'as' state
  gremlin.state.as[args[0]] = gremlin.vertex                  // set label to vertex
  return gremlin
})
```

初始化查询后，我们确保 gremlin 的本地状态有一个 `as` 参数。然后我们将该参数的属性设置为 gremlin 的当前顶点。

### Merge

一旦标记了顶点，我们就可以使用 `merge` 来提取它们。如果我们想要 Thor 的父母、祖父母和曾祖父母，我们可以这样做：

```js
g.v('Thor').out().as('parent').out().as('grandparent').out().as('great-grandparent')
           .merge('parent', 'grandparent', 'great-grandparent').run()
```

以下是 `merge` 管道类型：

```js
Dagoba.addPipetype('merge', function(graph, args, gremlin, state) {
  if(!state.vertices && !gremlin) return 'pull'               // query initialization

  if(!state.vertices || !state.vertices.length) {             // state initialization
    var obj = (gremlin.state||{}).as || {}
    state.vertices = args.map(function(id) {return obj[id]}).filter(Boolean)
  }

  if(!state.vertices.length) return 'pull'                    // done with this batch

  var vertex = state.vertices.pop()
  return Dagoba.makeGremlin(vertex, gremlin.state)
})
```

我们映射每个参数，在 gremlin 的标记顶点列表中查找它。如果找到它，我们就把 gremlin 复制到那个顶点。请注意，只有进入此管道的 gremlin 才会包含在 `merge` 中，如果 Thor 的母亲的父母不在图中，则她将不在结果集中。

### Except

我们已经见过这样的例子，“给我所有 Thor 的兄弟姐妹除了他自己”。我们可以使用过滤器：

```js
g.v('Thor').out().in().unique()
           .filter(function(asgardian) {return asgardian._id != 'Thor'}).run()
```

使用 `as` 和 `except` 更直接：

```js
g.v('Thor').as('me').out().in().except('me').unique().run()
```

有一些查询很难过滤。如果我们想要 Thor 的叔叔阿姨呢？我们如何过滤他的父母？使用 as 和 except[^unexpectedresults]很容易：

```js
g.v('Thor').out().as('parent').out().in().except('parent').unique().run()
```

[^unexpectedresults]:在某些条件下，此特定查询可能会产生意外结果。你能想到什么吗？你如何修改它以处理这些情况？

```js
Dagoba.addPipetype('except', function(graph, args, gremlin, state) {
  if(!gremlin) return 'pull'                                  // query initialization
  if(gremlin.vertex == gremlin.state.as[args[0]]) return 'pull'
  return gremlin
})
```

这里我们检查当前顶点是否等于我们以前存储的顶点。如果是，我们就跳过它。

### Back

我们提出的一些问题涉及进一步检查图，如果答案是肯定的，则稍后再返回到我们的起点。假设我们想知道 Fjörgynn 的哪些女儿和 Bestla 的儿子之一拥有孩子？

```js
g.v('Fjörgynn').in().as('me')       // first gremlin's state.as is Frigg
 .in()                              // first gremlin's vertex is now Baldr
 .out().out()                       // clone that gremlin for each grandparent
 .filter({_id: 'Bestla'})           // keep only the gremlin on grandparent Bestla
 .back('me').unique().run()         // jump gremlin's vertex back to Frigg and exit
```

以下是 `back` 的定义：

```js
Dagoba.addPipetype('back', function(graph, args, gremlin, state) {
  if(!gremlin) return 'pull'                                  // query initialization
  return Dagoba.gotoVertex(gremlin, gremlin.state.as[args[0]])
})
```

我们使用 `Dagoba.gotoVertex` 辅助函数来完成所有实际工作。让我们来看一下它和其它一些辅助函数。

## 辅助函数

上面的管道类型依靠一些辅助函数来完成工作。在深入了解解释器之前，让我们快速看一下。

### Gremlin

Gremlin 是一种简单的生物：它们有一个当前顶点和一些局部状态。所以要生成一个新的 gremlin，我们只需要用这两个样。

```js
Dagoba.makeGremlin = function(vertex, state) {
  return {vertex: vertex, state: state || {} }
}
```

根据这个定义，任何具有顶点属性和状态属性的对象都是 gremlin，因此我们可以内联构造函数，将其包装在函数中允许我们在一个地方将新属性添加到所有 gremlin 中。

我们还可以获取一个现有的 gremlin 并将其发送到一个新顶点，正如我们在 `back` 管道类型和 `simpleTraversal` 函数中看到的那样。

```js
Dagoba.gotoVertex = function(gremlin, vertex) {               // clone the gremlin
  return Dagoba.makeGremlin(vertex, gremlin.state)
}
```

注意，此函数实际上返回一个全新的 gremlin：原来 gremlin 的克隆，并发送到我们想要的目的地。这意味着一个 gremlin 可以在一个顶点上，而它的克隆体被发送出去探索其它顶点。这正是在 `simpleTraversal` 中发生的事情。

作为可能的增强功能示例，我们可以添加一些状态来跟踪 gremlin 访问的每个顶点，并添加新的管道类型来利用这些路径。

### 查找

`vertex` 管道类型使用 `findVertices` 函数收集一组初始顶点，并从这些初始顶点开始我们的查询。

```js
Dagoba.G.findVertices = function(args) {                      // vertex finder helper
  if(typeof args[0] == 'object')
    return this.searchVertices(args[0])
  else if(args.length == 0)
    return this.vertices.slice()                              // OPT: slice is costly
  else
    return this.findVerticesByIds(args)
}
```

该函数将其参数作为列表接收。如果第一个参数是一个对象，则将其传递给`searchVertices`，从而允许以下查询：

```js
  g.v({_id:'Thor'}).run()
  g.v({species: 'Aesir'}).run()
```

否则，如果有参数，则将其传递给 `findVerticesByIds`，后者处理 `g.v('Thor', 'Odin').run()` 之类的查询。

如果根本没有参数，那么我们的查询就像 `g.v().run()` 一样。对于大型图，这不是经常需要做的操作，尤其是因为我们在返回顶点列表之前要对其进行切片。我们之所以进行切片，是因为有些调用站点在处理返回的列表时，通过弹出项来直接操作返回的列表。我们可以通过在调用站点进行克隆来优化这种情形，或者避免这些操作。（我们可以让计数器保持状态，而不是弹出。）

```js
Dagoba.G.findVerticesByIds = function(ids) {
  if(ids.length == 1) {
    var maybe_vertex = this.findVertexById(ids[0])            // maybe it's a vertex
    return maybe_vertex ? [maybe_vertex] : []                 // or maybe it isn't
  }

  return ids.map( this.findVertexById.bind(this) ).filter(Boolean)
}

Dagoba.G.findVertexById = function(vertex_id) {
  return this.vertexIndex[vertex_id]
}
```

注意这里 `vertexIndex` 的用法。如果没有这个索引，我们将不得不一次一个地遍历列表中的每个顶点以确定它是否匹配ID，从而将一个固定时间操作转换为线性时间操作，以及任何直接依赖它的$O(n)$操作转换为$O(n^2)$操作。

```js
Dagoba.G.searchVertices = function(filter) {        // match on filter's properties
  return this.vertices.filter(function(vertex) {
    return Dagoba.objectFilter(vertex, filter)
  })
}
```

`searchVertices` 函数对图中的每个顶点使用 `objectFilter` 辅助函数。我们将在下一节讨论 `objectFilter`，但同时，你能想出一种方法来延迟搜索顶点吗？

### 过滤

我们看到 ·simpleTraversal· 在遇到的边上使用了过滤函数。这是一个简单的函数，但是足以满足我们的需求。

```js
Dagoba.filterEdges = function(filter) {
  return function(edge) {
    if(!filter)                                 // no filter: everything is valid
      return true

    if(typeof filter == 'string')               // string filter: label must match
      return edge._label == filter

    if(Array.isArray(filter))                   // array filter: must contain label
      return !!~filter.indexOf(edge._label)

    return Dagoba.objectFilter(edge, filter)    // object filter: check edge keys
  }
}
```

第一种情况没有过滤器：`g.v('Odin').in().run()` 遍历所有到 Odin 的边。

第二种情况根据边的标签过滤：`g.v('Odin').in('parent').run()` 遍历那些带有 `parent` 标签的边。

第三种情况接受一个标签数组：`g.v('Odin').in(['parent', 'spouse']).run()` 遍历 `parent` 和 `spouse` 边。

第四种情况使用我们之前看到的 `objectFilter` 函数：

```js
Dagoba.objectFilter = function(thing, filter) {
  for(var key in filter)
    if(thing[key] !== filter[key])
      return false

  return true
}
```

这使我们可以使用 `filter` 对象查询边：

```js
g.v('Odin').in({_label: 'spouse', order: 2}).run()    // finds Odin's second wife
```

## 解释器的本质

我们到达了最后，准备讲解最核心的部分：解释器。代码实际上相当简洁，但是该模型有一些巧妙之处。

我们之前比较了程序和管道，这是编写查询的一个很好的思维模型。但是，正如我们所看到的，我们需要一个不同的模型来实际实现。这个模型更像是一个图灵机而不是管道：在一个特定的步骤上有一个读/写头。它“读取”步骤，更改其“状态”，然后向右或向左移动。

读取步骤意味着计算管道类型函数。正如我们在上面看到的，每个函数都接受整个图、它自己的参数（可能是 gremlin）和它自己的局部状态作为输入。作为输出，它提供一个 gremlin、false 或者“pull”或“done”的信号。这个输出是我们的准图灵机读取的，以便改变机器的状态。

该状态只包含两个变量：一个用于记录“done”的步骤，另一个用于记录查询结果。这些被更新，然后要不头移动，要不查询结束并返回结果。

现在我们已经描述了机器中的所有状态。我们将有一个开始为空的结果列表：

```js
 var results = []
```

在第一步之后开始的最后一个“done”步骤的索引：

```js
var done = -1
```

我们需要一个地方来存储最新步骤的输出，它可能是一个gremlin，也可能什么都不是，因此我们将其称为 maybe_gremlin：

```js
var maybe_gremlin = false
```

最后，我们需要一个程序计数器来指示读/写头的位置。

```js
var pc = this.program.length - 1
```

除了...等等。我们怎样才能变成延迟加载[^getlazy]？从立即加载的系统中构建延迟加载系统的传统方法是将参数以“thunk”形式存储到函数调用中，而不是对它们求值。你可以把 thunk 看作是一个未赋值的表达式。在具有头等函数（first-class function）和闭包的 JS 中，我们可以通过将函数及其参数包装在不带参数的新匿名函数中来创建 thunk：

[^getlazy]:从技术上讲，我们需要实现一个具有非严格语义的解释器，这意味着它只在被迫时求值。惰性求值是一种用于实现非严格性的技术。我们把两者混为一谈有点偷懒，所以我们只有在被迫的时候才会消除歧义。

```js
function sum() {
  return [].slice.call(arguments).reduce(function(acc, n) { return acc + (n|0) }, 0)
}

function thunk_of_sum_1_2_3() { return sum(1, 2, 3) }

function thunker(fun, args) {
  return function() {return fun.apply(fun, args)}
}

function thunk_wrapper(fun) {
  return function() {
    return thunker.apply(null, [fun].concat([[].slice.call(arguments)]))
  }
}

sum(1, 2, 3)              // -> 6
thunk_of_sum_1_2_3()      // -> 6
thunker(sum, [1, 2, 3])() // -> 6

var sum2 = thunk_wrapper(sum)
var thunk = sum2(1, 2, 3)
thunk()                   // -> 6
```

在真正需要一个 thunk 之前，不会调用任何 thunk，这通常意味着需要某种类型的输出：在我们的场景下是查询的结果。每次解释器遇到新的函数调用时，我们都将其包装在一个 thunk 中。回忆一下我们对查询的原始表述：`children(children(children(parents(parents(parents([8]))))))`。每一层都是一个 thunk，像洋葱一样被包裹起来。

这种方法权衡了两个方面：一个是空间性能变得更加难以解释，因为可以创建大量的 thunk 图。另一个是我们的程序现在被表达成一个单一的 thunk，此时我们不能做太多事情。

第二点通常不是问题，因为编译器运行优化时与运行时所有 thunk 产生存在阶段分离。在我们的案例中，我们没有这个优势：因为我们使用方法链来实现一个流畅的接口[^fluentinterface]，如果我们也使用 thunk 来实现延迟加载，我们将在调用每个新方法时对其使用 thunk，这意味着在运行 `run()` 时，我们只有一个 thunk 作为输入，无法优化查询。

[^fluentinterface]:方法链使我们可以编写 `g.v('Thor').in().out().run()` 而不是六行非流利的 JS。

有趣的是，我们流畅的接口隐藏了查询语言和常规编程语言之间的另一个区别。如果不使用方法链，则可以将查询 `g.v('Thor').in().out().run()` 重写为 `run(out(in(v(g, 'Thor'))))` 。在 JS 中，我们首先处理 `g` 和 `Thor`，然后是 `v`，然后是 `in`、`out` 和 `run`，从内到外运行。在具有非严格语义的语言中，我们将从外向内运行，仅在需要时处理每个连续嵌套的参数层。

因此，如果我们在语句末尾使用 `run` 开始计算查询，然后回到 `v('Thor')`，仅根据需要计算结果，那么我们就有效地实现了非严格性。秘密在于查询的线性。分支使流程图复杂化，同时还引入了重复调用的机会，这需要记忆（memoization ）以避免浪费资源。查询语言的简单性意味着我们可以基于线性读/写头模型实现同样简单的解释器。

除了允许运行时优化外，这种风格还有许多其他与插装（instrumentation）容易程度相关的好处：历史记录、可逆性、逐步调试、查询统计。所有这些都很容易动态添加，因为我们控制解释器，并将其作为虚拟机求值器，而不是将程序简化为单个 thunk。

## 解释器揭开面纱

```js
Dagoba.Q.run = function() {                 // a machine for query processing

  var max = this.program.length - 1         // index of the last step in the program
  var maybe_gremlin = false                 // a gremlin, a signal string, or false
  var results = []                          // results for this particular run
  var done = -1                             // behindwhich things have finished
  var pc = max                              // our program counter

  var step, state, pipetype

  while(done < max) {
    var ts = this.state
    step = this.program[pc]                 // step is a pair of pipetype and args
    state = (ts[pc] = ts[pc] || {})         // this step's state must be an object
    pipetype = Dagoba.getPipetype(step[0])  // a pipetype is just a function
```

这里 `max` 只是一个常量，以及有关当前步骤的步骤、状态和管道类型缓存信息。我们已经进入驱动循环，在最后一步完成之前不会停止。

```js
maybe_gremlin = pipetype(this.graph, step[1], maybe_gremlin, state)
```

用其参数调用当前步骤的管道类型函数。

```js
if(maybe_gremlin == 'pull') {           // 'pull' means the pipe wants more input
  maybe_gremlin = false
  if(pc-1 > done) {
    pc--                                // try the previous pipe
    continue
  } else {
    done = pc                           // previous pipe is done, so we are too
  }
}
```

为了处理“pull”的情况，我们首先将 `maybe_gremlin[^maybegremlin]` 设置为 `false`。我们把“maybe”作为一个通道来传递“pull”和“done”信号，从而使“maybe”加载，但一旦这些信号中的一个被取出，我们又会将其视为正确的“maybe”。

[^maybegremlin]:我们称之为 `maybe_gremlin`，是为了提醒自己它可能是一个 gremlin，也可能是其他东西。也因为最初它不是一个 gremlin 就是什么都没有。

如果前面的步骤没有“done”[^stepnotdone]，我们将头向后移动并重试。否则，我们会把自己标记为“done”并让头部向前移动。

[^stepnotdone]:回想一下，done 从 -1 开始，所以第一步的前一步总是 done。

```js
if(maybe_gremlin == 'done') {           // 'done' tells us the pipe is finished
  maybe_gremlin = false
  done = pc
}
```

处理“done”情况更容易：将 `maybe_gremlin` 设置为 `false` 并将此步骤标记为“done”。

```js
  pc++                                    // move on to the next pipe

  if(pc > max) {
    if(maybe_gremlin)
      results.push(maybe_gremlin)         // a gremlin popped out of the pipeline
    maybe_gremlin = false
    pc--                                  // take a step back
  }
}
```

我们完成了当前步骤，并将头部移到下一步。如果我们在程序的末尾，并且 `maybe_gremlin` 包含一个 gremlin，我们会将它添加到结果中，将 `maybe_ gremlin` 设置为 `false` 并将头部移回程序的最后一步。

这也是初始化状态，因为 pc 是以 max 开始的，所以我们从这里开始，然后回到这里，对于查询返回的每个最终结果，至少要在这里结束一次。

```js
  results = results.map(function(gremlin) { // return projected results, or vertices
    return gremlin.result != null
         ? gremlin.result : gremlin.vertex } )

  return results
}
```

我们现在已经脱离了驱动循环：查询已经结束，结果已经包含在内，我们只需要处理并返回它们即可。如果任何一个 gremlin 有结果集，我们将返回它，否则我们将返回 gremlin 的最终顶点。我们还有别的东西要返回吗？这里需要权衡什么？

## 查询转换器

现在我们为查询程序提供了一个不错的简洁解释器，但是我们仍然缺少一些东西。每一个现代数据库管理系统（DBMS）都有一个查询优化器作为系统的重要组成部分。对于非关系型数据库，优化我们的查询计划很难产生与关系数据库类似的指数级加速效果[^dboptimize]，但这仍然是数据库设计的一个重要方面。

[^dboptimize]：或者，更确切地说，措辞不好的查询不太可能产生指数级的减速。作为 RDBMS 的最终用户，查询质量通常是相当不透明的。

我们能为合理地称为查询优化器做的最简单的事情是什么？我们可以在运行查询程序之前编写一些函数来转换它们。我们将一个程序作为输入传入，并将另一个程序作为输出返回。

```js
Dagoba.T = []                               // transformers (more than meets the eye)

Dagoba.addTransformer = function(fun, priority) {
  if(typeof fun != 'function')
    return Dagoba.error('Invalid transformer function')

  for(var i = 0; i < Dagoba.T.length; i++)  // OPT: binary search
    if(priority > Dagoba.T[i].priority) break

  Dagoba.T.splice(i, 0, {priority: priority, fun: fun})
}
```

现在我们可以将查询转换器添加到我们的系统中。查询转换器是一个接受程序并返回一个带有优先等级的程序。更高优先级的转换器更靠近列表的前面。我们要确保 `fun` 是一个函数，因为我们稍后会对它求值[^paramdomain]。

[^paramdomain]:请注意，我们保持 `priority` 参数的域是开放的，因此它可以是整数、有理数、负数，甚至可以是无穷大或 `NaN` 之类的。

我们假设不会添加大量的转换器，通过线性遍历列表来添加一个新的转换器。如果这个假设被证明是错误的，我们会留下一个注释：对于长列表，二叉搜索的性能更加优秀，但是增加了复杂性，并且不能加快短列表的速度。

为了运行这些转换器，我们将在解释器的顶部插入一行代码：

```js
Dagoba.Q.run = function() {                     // our virtual machine for querying
  this.program = Dagoba.transform(this.program) // activate the transformers
```

我们将使用它来调用这个函数，它将程序依次传递给每个转换器：

```js
Dagoba.transform = function(program) {
  return Dagoba.T.reduce(function(acc, transformer) {
    return transformer.fun(acc)
  }, program)
}
```

到目前为止，我们的引擎一直在以简单换取性能，这种策略的好处之一是，它为全局优化敞开了大门，如果我们在设计系统时选择了局部优化，那么这些全局优化可能是不可用的。

优化程序通常会增加复杂性，降低系统的优雅度，使其更难理解和维护。打破抽象障碍以提高性能是一种更为恶劣的优化形式，即使看似无害，如将面向性能的代码嵌入业务逻辑，也会使维护变得更加困难。

有鉴于此，这种“正交优化”特别吸引人。我们可以在模块甚至用户代码中添加优化器，而不是让它们与引擎紧密耦合。我们可以单独测试它们，也可以分组测试，通过添加生成测试，我们甚至可以自动化该过程，确保我们可用的优化程序能够很好地协同工作。

我们还可以使用这个转换器系统来添加与优化无关的新功能。现在我们来看一个例子。

## 别名

进行类似 `g.v('Thor').out().in()` 的查询非常简洁，但是这是 Thor 的兄弟姐妹还是他的伙伴呢？两种解释都不完全令人满意。更好的说法是：`g.v('Thor').parents().children()` 或 `g.v('Thor').children().parents()`。

我们可以使用查询转换器，通过几个额外的辅助函数创建别名：

```js
Dagoba.addAlias = function(newname, oldname, defaults) {
  defaults = defaults || []                     // default arguments for the alias
  Dagoba.addTransformer(function(program) {
    return program.map(function(step) {
      if(step[0] != newname) return step
      return [oldname, Dagoba.extend(step[1], defaults)]
    })
    }, 100)                                     // 100 because aliases run early

  Dagoba.addPipetype(newname, function() {})
}
```

我们正在为现有步骤添加一个新名称，因此我们需要创建一个查询转换器，以便在遇到新名称时将其转换为原名称。我们还需要将新名称作为方法添加到主查询对象上，以便将其提取到查询程序。

如果我们可以捕获丢失的方法调用并将它们路由到处理程序函数，那么我们就可以以较低的优先级运行这个转换器，但目前还没有办法做到这一点。相反，我们将以 100 的高优先级运行它，以便在调用别名方法之前添加它们。

我们调用另一个辅助函数来合并传入步骤的参数与别名的默认参数。如果传入步骤缺少参数，那么我们将使用该插槽别名的参数。

```js
Dagoba.extend = function(list, defaults) {
  return Object.keys(defaults).reduce(function(acc, key) {
    if(typeof list[key] != 'undefined') return acc
    acc[key] = defaults[key]
    return acc
  }, list)
}
```

现在我们可以创建所需的别名：

```js
Dagoba.addAlias('parents', 'out')
Dagoba.addAlias('children', 'in')
```

我们还可以通过将父级和子级之间的每条边标记为“父级”边，开始对数据模型进行更多的专门化。那么我们的别名应该是这样的：

```js
Dagoba.addAlias('parents', 'out', ['parent'])
Dagoba.addAlias('children', 'in', ['parent'])
```

现在我们可以为配偶、继父母，甚至被抛弃的前恋人添加边。如果我们增强 `addAlias` 函数，我们可以为祖父母、兄弟姐妹甚至堂兄弟姐妹引入新的别名：

```js
Dagoba.addAlias('grandparents', [ ['out', 'parent'], ['out', 'parent']])
Dagoba.addAlias('siblings',     [ ['as', 'me'], ['out', 'parent']
                                , ['in', 'parent'], ['except', 'me']])
Dagoba.addAlias('cousins',      [ ['out', 'parent'], ['as', 'folks']
                                , ['out', 'parent'], ['in', 'parent']
                                , ['except', 'folks'], ['in', 'parent']
                                , ['unique']])
```

那个堂兄弟的别名有点麻烦。也许我们可以扩展 `addAlias` 函数，允许我们在别名中使用其他别名，并这样调用：

```js
Dagoba.addAlias('cousins',      [ 'parents', ['as', 'folks']
                                , 'parents', 'children'
                                , ['except', 'folks'], 'children', 'unique'])
```

现在代替

```js
g.v('Forseti').parents().as('parents').parents().children()
                        .except('parents').children().unique()
```

我们表述为 `g.v('Forseti').cousins()`。

但是，我们引入了一些泡菜：当我们的 `addAlias` 函数解析别名时，它还必须解析其它别名。如果父母叫其它别名，而我们在解决 `cousins` 时又不得不停下来解析 `parents`，然后再解析别名，会怎么样？如果 `parents` 的别名最终被称为 `cousins` 怎么办？

这使我们进入了依赖关系解析领域[^dependencyresolution]，它是现代包管理器的核心组件。在选择理想版本、tree shaking、一般优化等方面有很多技巧，但基本思想相当简单。我们将绘制一张所有依赖及其关系的图，然后尝试找到一种方法来排列顶点，同时使所有箭头从左到右。如果可以的话，这种特殊的顶点排序被称为“拓扑排序”，并且我们已经证明了我们的依赖图没有循环：它是一个有向无环图（DAG）。如果我们不能这样做，那么我们的图至少有一个循环。

[^dependencyresolution]:你可以在本书的相关章节中了解有关依赖关系解析的更多信息。

另一方面，我们期望我们的查询通常会很短（100 步将是一个非常长的查询），并且我们的转换器数量很少。如果有任何变化，我们可以从转换函数返回`true`，然后运行它直到它停止生产，而不是使用 DAG 和依赖管理。这要求每个转换器都是幂等的，这是一个非常有用的属性。这两种途径的利弊是什么？

## 性能

所有的生产图数据库都有特定的性能特征：图遍历查询相对于总图大小来说是恒定的时间[^ifadjacency]。在非图数据库中，查询某人的朋友列表所需的时间与条目的数量成正比，因为在最糟糕的情况下，您必须查看每个条目。这意味着，如果一个 10 个条目的查询需要一毫秒的时间，那么一个1000万个条目的查询将需要将近两个星期的时间。如果用 Pony Express[^ponyexpress] 发送，你的朋友列表会更快到达！

[^ifadjacency]:合适的术语是“无索引邻接”。

[^ponyexpress]:由于横贯大陆的电报的到来和美国内战的爆发，虽然它只运行了18个月，但人们至今仍记得它在短短十天内将邮件从一个海岸送到另一个海岸。

为了缓解这种糟糕的性能，大多数数据库在经常查询的字段上建立索引，这会将$O(n)$搜索转换为$O(logn)$搜索。这样可以提供更好的搜索性能，以牺牲一些写入性能和大量空间为代价，索引可以轻松地将数据库的大小扩大一倍。对大多数数据库来说，仔细平衡索引的空间/时间权衡是永久调优过程的一部分。

图数据库通过在顶点和边之间建立直接的连接来避免这个问题，因此图遍历只是指针跳转；不需要扫描每个项，不需要索引，完全不需要额外的工作。现在，无论图中有多少人，找到你的朋友都是一样的代价，没有额外的空间成本或写入时间成本。这种方法的一个缺点是，当整个图都在同一台机器的内存中时，指针将发挥最佳效果。在多台机器上有效地分片一个图数据库仍然是一个活跃的研究领域[^graphdbsharding]。

[^graphdbsharding]:分片图数据库需要对图进行分区。即使对于树和网格这样的简单图，最优图划分也是NP难的，好的近似也具有指数渐近复杂度。

如果我们替换掉寻找边的函数，我们可以在 Dagoba 的缩影中看到这一点。这是一个简单的版本，它在线性时间内搜索所有的边。它与我们的第一个实现类似，但是使用了我们构建的所有结构。

```js
Dagoba.G.findInEdges  = function(vertex) {
  return this.edges.filter(function(edge) {return edge._in._id  == vertex._id} )
}
Dagoba.G.findOutEdges = function(vertex) {
  return this.edges.filter(function(edge) {return edge._out._id == vertex._id} )
}
```

我们可以为边添加一个索引，这使我们在处理小图的时候能够做到这一点，但是对于大图来说却有一些问题。

```js
Dagoba.G.findInEdges  = function(vertex) { return this.inEdgeIndex [vertex._id] }
Dagoba.G.findOutEdges = function(vertex) { return this.outEdgeIndex[vertex._id] }
```

在这里，我们又见到了我们的老朋友：无索引的邻接关系。

```js
Dagoba.G.findInEdges  = function(vertex) { return vertex._in  }
Dagoba.G.findOutEdges = function(vertex) { return vertex._out }
```

你可以自己运行这些程序来体验图数据库的差异[^jslistfilter]。

[^jslistfilter]:在现代JavaScript引擎中，对小图过滤列表的速度相当快，由于底层数据结构和代码的JIT编译方式，原始版本实际上可能比无索引版本快。尝试使用不同大小的图形来查看这两种方法是如何缩放的。

## 序列化

在内存中有一个图是很好的，但是我们如何在第一时间得到它呢？我们看到，我们的图构造器可以获取一个顶点和边的列表，并为我们创建一个图，但是一旦这个图被构建好了，我们如何将这些顶点和边取出来呢？

我们自然倾向于做类似 `JSON.stringify(graph)` 之类的事情，这会产生非常常见的错误“TypeError:Converting circular structure to JSON”。 在图构建过程中，顶点被链接到它们的边上，并且所有边都被链接到它们的顶点，因此现在所有内容都引用了其它所有内容。 那么，我们如何才能再次提取出漂亮整洁的列表呢？ JSON 替代函数可以为你提供帮助。

`JSON.stringify` 函数需要一个值来 `stringify`，但它还需要两个附加参数：替代函数和空白数字[^protip]。替换程序允许你自定义字符串化的进行方式。

[^protip]:专家提示：给定一棵深树 `deep_tree`，在 JS 控制台中运行 `JSON.stringify(deep_uTree, 0, 2)` 是一种使其可读的快速方法。

我们需要对顶点和边进行一些不同的处理，因此我们将手动将两侧合并为一个 JSON 字符串。

```js
Dagoba.jsonify = function(graph) {
  return '{"V":' + JSON.stringify(graph.vertices, Dagoba.cleanVertex)
       + ',"E":' + JSON.stringify(graph.edges,    Dagoba.cleanEdge)
       + '}'
}
```

这些是顶点和边的替代函数。

```js
Dagoba.cleanVertex = function(key, value) {
  return (key == '_in' || key == '_out') ? undefined : value
}

Dagoba.cleanEdge = function(key, value) {
  return (key == '_in' || key == '_out') ? value._id : value
}
```

它们之间唯一的区别是当一个循环即将形成时它们会做什么：对于顶点，我们完全跳过边列表。对于边，我们将每个顶点替换为其 ID。这样就消除了我们在构建图时创建的所有循环。

我们在 `Dagoba.jsonify` 中手动操作JSON，通常不推荐这样做，因为 JSON 格式比较固定。即使再小也很容易漏掉一些东西，并且很难从视觉上确认其正确性。

我们可以将这两个替换函数合并为一个函数，然后通过执行 `JSON.stringify(graph, my_cool_replacer)` 在整个图上使用新替换函数。这使我们不必手动处理 JSON 输出，但是生成的代码可能会有点混乱。你可以自己尝试一下，看看是否可以找到一个可以避免手工编写 JSON 的、经过良好设计的解决方案。（如果合适，则可获得奖励积分。）

## 持久性

持久性通常是数据库中比较棘手的部分之一：磁盘相对安全，但速度较慢。批量写入，使它们成为原子操作，日志记录——这些都很难做到既快又正确。

幸运的是，我们正在构建一个内存数据库，因此不用担心这些！不过，我们有时可能希望在本地保存数据库的副本，以便在页面加载时快速重新启动。我们可以使用我们刚刚构建的序列化程序来实现这一点。首先让我们把它包装在一个辅助函数中：

```js
Dagoba.G.toString = function() { return Dagoba.jsonify(this) }
```

在 JavaScript 中，只要将对象强制为字符串，就会调用该对象的 `toString` 函数。因此，如果 `g` 是一个图，那么 `g+""` 将是该图的序列化 JSON 字符串。

`fromString` 函数不是语言规范的一部分，但是用起来方便。

```js
Dagoba.fromString = function(str) {             // another graph constructor
  var obj = JSON.parse(str)                     // this can throw
  return Dagoba.graph(obj.V, obj.E)
}
```

现在，我们将在持久性函数中使用它们。`toString` 函数隐藏了，你能发现吗？

```js
Dagoba.persist = function(graph, name) {
  name = name || 'graph'
  localStorage.setItem('DAGOBA::'+name, graph)
}

Dagoba.depersist = function (name) {
  name = 'DAGOBA::' + (name || 'graph')
  var flatgraph = localStorage.getItem(name)
  return Dagoba.fromString(flatgraph)
}
```

为了避免污染域的 `localStorage` 属性，我们在名称前面加上了一个伪命名空间，因为域中可能会非常拥挤。通常还有一个较低的存储限制，所以对于较大的图，我们可能需要使用某种类型的 Blob。

如果来自同一域的多个浏览器窗口同时持久化和去持久化，也存在潜在的问题。`localStorage` 空间是在这些窗口之间是共享的，它们可能位于不同的事件循环中，因此有可能一个窗口不小心覆盖另一个窗口的工作。规范说，对 `localStorage` 的读/写访问应该需要一个互斥体，但是它在不同的浏览器之间实现不一致，即使是像我们这样简单的实现，也可能会遇到问题。

如果我们希望我们的持久性实现是多窗口并发感知的，那么我们可以利用当 `localStorage` 被更改时激发的存储事件来相应地更新我们本地的图。

## 更新

我们的 `out` 管道类型复制顶点的输出边，并在每次需要时弹出一个。构建新的数据结构需要时间和空间，并将更多的工作推到内存管理器上。我们可以直接使用顶点的输出边列表，用一个计数器变量追踪我们的位置。你能想出这种方法的问题吗？

如果有人在查询过程中删除了我们访问过的一个边，这将改变边列表的大小，然后我们将跳过一个边，因为计数器会关闭。为了解决这个问题，我们可以锁定查询中涉及的顶点，但是我们要么失去定期更新图的能力，要么失去使长期查询对象能够按需响应更多结果的请求的能力。即使我们处于单线程事件循环中，我们的查询也可以跨越多个异步重新输入，这意味着像这样的并发问题是一个非常现实的问题。

所以我们将付出性能代价来复制边列表。不过，仍然存在一个问题，即长期查询可能无法看到完全一致的时间顺序。我们将在访问一个顶点时遍历它的每一条边，但是在查询期间，我们在不同的时钟时间访问顶点。假设我们保存一个查询，比如 `var q = g.v('Odin').children().children().take(2)`，然后调用 `q.run()` 来收集 Odin 的两个孙子。一段时间后，我们需要再拉两个孙子，所以我们再次调用 `q.run()`。如果 Odin 在这段时间内有了一个新的孙子，我们可能会看到也可能看不到，这取决于我们第一次运行查询时是否访问了父顶点。

解决这种不确定性的一种方法是更改更新处理程序以向数据添加版本控制。然后，我们将更改驱动循环以将图的当前版本传递到查询中，因此我们始终可以看到与首次初始化查询时一致的视图。向我们的数据库添加版本控制也为真正的事务和类似STM的方式自动回滚/重试打开了大门。

## 未来发展方向

我们之前看到了收集祖先的一种方式：

```js
g.v('Thor').out().as('parent')
           .out().as('grandparent')
           .out().as('great-grandparent')
           .merge(['parent', 'grandparent', 'great-grandparent'])
           .run()
```

这相当笨拙，并且扩展性不好，如果我们想要六层祖先呢？或者通过浏览任意数量的祖先来寻找我们想要的东西？

如果我们能这样说就好了：

```js
g.v('Thor').out().all().times(3).run()
```

我们想从中得到类似于上述查询的信息：

```js
g.v('Thor').out().as('a')
           .out().as('b')
           .out().as('c')
           .merge(['a', 'b', 'c'])
           .run()`
```

在查询转换器全部运行之后。 我们可以先运行倍数转换器，以产生：

```js
g.v('Thor').out().all().out().all().out().all().run()
```

然后运行 `all` 转换器，并让它将每个 `all` 转换为唯一标记 `as`，并在最后一个 `as` 放置 `merge`。

不过，这也有一些问题。首先，这种 `as/merge` 技术只有在每个路径都存在于图中时才起作用：如果我们缺少一个 Thor 的曾祖父母的条目，那么我们将跳过有效的条目。另一方面，如果我们只想对查询的一部分而不是整个查询执行此操作，会发生什么情况？如果有多个 `all` 怎么办？

为了解决第一个问题，我们将不得不将 `all` 视为不仅仅是 `as/merge` 的东西。我们需要每一个父 gremlin 都跳过干预步骤。我们可以把它看作是一种从管道的一部分直接跳到另一部分的远程传输，或者我们可以把它看作某种分支管道，但是不管怎样，它都会使我们的模型复杂化。另一种方法是把 gremlin 想象成以一种悬浮的动画形式穿过中间的管道，直到被一个特殊的管道唤醒。然而，确定悬挂/未悬挂管道的范围可能很棘手。

接下来的两个问题比较简单。为了只修改查询的一部分，我们将用特殊的开始/结束步骤包装该部分，比如 `g.v('Thor').out().start().in().out().end().times(4).run()`。实际上，如果解释器知道这些特殊的管道类型，我们就不需要结束步骤，因为序列的结尾总是一个特殊的管道类型。我们将这些特殊的管道类型称为“副词（adverbs）”，因为它们像副词修饰动词一样修饰常规管道类型。

为了处理多个 `all`，我们需要运行所有的转换器两次：一次在倍数 `times` 之前，唯一地标记所有的 `all`，然后在倍数 `times` 之后再次以唯一的方式重新标记所有标记的 `all`。

搜索无限数量的祖先仍然是一个问题，例如，我们如何找出 Ymir 的哪些后代在诸神黄昏中生存下来了？我们可以进行单独的查询，比如 `g.v('Ymir').in().filter({survives: true})` 和 `g.v('Ymir').in().in().in().in().filter({survives: true})`，然后自己手动收集结果，但这太糟糕了。

我们想用这样一个副词：

```js
g.v('Ymir').in().filter({survives: true}).every()
```

这将像 `all + times` 一样工作，但没有强制限制。不过，我们可能希望在遍历上强制使用特定的策略，比如固定的 BFS 或 YOLO DFS，所以 `g.v('Ymir').in().filter({survives: true}).bfs()` 会更灵活。通过这种方式，我们可以用一种简单的方式来声明比如“检查诸神黄昏幸存者，一次跳过一代”的复杂查询：`g.v('Ymir').in().filter({survives: true}).in().bfs()`。

## 总结

我们学到了什么？图数据库非常适合存储计划通过图遍历查询的互连[^sortainterconnected]数据。通过添加非严格语义，可以在出于性能原因而无法在即时系统中表达的查询中提供流畅的接口，并允许你跨越异步边界。时间使事情变得复杂，而从多个角度来看时间（即并发性）使事情变得非常复杂，因此只要我们能够避免引入时间依赖性（例如，状态、可观察的效果等），我们就可以更容易地对系统进行推理。以一种简单、解耦和非优化风格构建，为以后的全局优化打开了大门，并且使用驱动循环实现正交优化，而不会引入脆弱性和复杂性这些大多数优化技术的特点。

最后一点着重强调：保持简单。为了简单而避免优化。努力通过找到合适的模型来实现简单性。探索多种可能性。本书中的章节提供了充分的证据，证明伟大的应用程序可以有一个小而简洁的内核。一旦你找到了你正在构建的应用程序的内核，就要努力防止复杂性污染它。构建用于附加功能的钩子，并不惜一切代价维护抽象障碍。很好地使用这些技术并不容易，但它们可以帮助你解决其它棘手问题。

[^sortainterconnected]:虽然你希望边的数量与顶点的数量成正比增长，但二者没有太大的关联。换句话说，连接到一个顶点的平均边数不应该随图的大小而变化。我们考虑放入图数据库中的大多数系统已经具有这样的特性：如果 Loki 有100000个额外的孙子孙女，Thor 顶点的度数并不会增加。

## 致谢

非常感谢 Amy Brown，Michael DiBernardo，Colin Lupton，Scott Rostrup，Michael Russo，Erin Toliver和Leo Zovic对本文所做的宝贵贡献。

