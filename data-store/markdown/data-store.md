# DBDB：Dog Bed 数据库

## 作者

Taavi Burns 在 Countermeasure 乐团是一名男低音（有时是男高音），Taavi 总是打破常规。在他职业生涯中，工作场所多种多样：IBM（做 C 和 Perl），FreshBooks（什么都做），Points.com 网站（做 Python），现在在 PagerDuty（做 Scala）。除此之外，当他没有在骑他的 Brompton 折叠自行车时，你可能会发现他和他的儿子一起玩 Minecraft，或者和他的妻子一起跑酷（或者攀岩或其它冒险活动）。他的爱好十分广泛。

## 简介

DBDB（Dog Bed 数据库）是一个用 Python 实现的简单的键/值数据库。它允许你将键与值相关联，并将该关联存储在磁盘上以供以后检索。

DBDB 的目标是在计算机崩溃和程序错误情况下保存数据。它还避免了一次将所有数据保存在 RAM 中，这样就可以存储比 RAM 更多的数据。

## 回忆

我记得第一次被 bug 困扰的情景。当我输入完 BASIC 程序并运行它时，屏幕上出现了奇怪的闪烁光点，程序提前中止。当我回去看代码时，程序的最后几行消失不见了。

我妈妈的一个朋友会编程，所以我打电话咨询了她。在和她交谈的几分钟，我发现了问题：程序太大了，占用了显存。清除屏幕终止了程序，这些闪烁的光点是苹果 BASIC 电脑在程序结束后将程序状态存储在 RAM 中的行为的产物。

从那时起，我开始注意内存分配。我学习了指针以及如何用 malloc 分配内存。我了解了数据结构是如何在内存中布局的。我学会了非常非常小心地修改内存。

几年后，当我学习一种名为 Erlang 的面向过程的语言时，我才知道进程之间通信不必复制一份数据，因为所有数据都是不可变的。然后我在 Clojure 中发现了不可变的数据结构，它开始引起我的注意。

当我在 2013 年读到 CouchDB 时，我才意识到复杂数据在变化时管理的结构和机制。

我认识到可以设计一个基于不可变数据的系统。

然后我同意写下这个章节。

我认为描述 CouchDB 的核心数据存储概念（据我所知）会很有趣。

当我试图写一个二叉树算法来改变树的位置时，我认识到这个算法太过复杂。边界场景的数量和试图解释树的某个部分的变化如何影响其他部分让我很是头痛。我不知道该怎么解释这一切。

想起以前的经验教训，我仔细观察更新不可变二叉树的递归算法，结果证明它更加简单。

我再次认识到，处理不可变的事物更容易。

然后就有了 DBDB。

## 为什么这个项目很有趣？

大多数项目都需要某种数据库。你没必要自己写；即使你只是在把 JSON 写到磁盘上，也有很边界场景会困扰你：

- 如果文件系统的储存空间用完了怎么办？
- 如果你的笔记本电脑没电了怎么办？
- 如果数据大小超过可用内存怎么办？（对于现代桌面计算机上的大多数应用程序来说不太可能，但是对于移动设备或服务器端 Web 应用程序来说有可能会出现这种情况。）

如果你想了解数据库如何处理所有这些问题，那么为自己编写一个数据库是个不错的选择。

我们在这里讨论的技术和概念应该适用于应对各种情况。

关于不足。。。

## 不足之处

数据库通常以它们对 ACID 属性的实现程度为特征：原子性、一致性、隔离性和持久性。

DBDB 中的更新具有原子性和持久性，这两个属性将在本章后面介绍。DBDB 不提供一致性保证，因为对存储的数据没有约束。隔离性在 DBDB 同样没有实现。

当然，应用程序代码可以保证自身一致性，但是实现隔离性需要事务管理器。这里我们不尝试这样做，你可以在CircleDB一章中了解更多关于事务管理的信息。

DBDB 可以添加压缩功能，但这是留给读者的练习[^bonus]。

[^bonus]:额外功能：你能保证压缩的树结构是平衡的吗？这有助于保证性能。

## DBDB 的架构

DBDB 将“把数据放到磁盘某处”（数据在文件中的布局方式；物理层）与数据的逻辑结构（本例中是一个二叉树；逻辑层）和键/值存储的内容（键 `a` 与值 `foo` 的关联；公共API）分开。

许多数据库为了提高性能会将逻辑和物理方面分开，例如 DB2 的 SMS（文件系统中的文件）与 DMS（原始块设备）表空间，或者 MySQL 的替代引擎。

## 了解设计

本文使用了大量篇幅介绍一个程序是怎么从无到有的写出来的。但是，这并不是大多数人参与、开发代码的方式。我们通常先是阅读别人写的代码，然后通过修改或者拓展这些代码来达到自己的需求。

所以，我们假设 DBDB 是一个完整的项目，然后去了解它的流程和逻辑。让我们先从 DBDB 的包含的文件开始了解吧。

### DBDB 的文件组织

下列文件的排列顺序是从前到后，比如说，第一个文件是这个程序的用户可能最需要了解的模块，而最后一个模块是他们应该很少与之交互的模块。

- `tool.py` 是一个在终端中执行的命令行工具。
- `interface.py` 定义了一个 DBDB 类，它使用二叉树来实现了 Python 中的字典。
- `logical.py` 定义了逻辑层。是使用键/值存储的接口。
  - `LogicalBase` 提供了使用get， set， commit 的接口，用了一个子类来完成具体的实现。它还用于管理存储的锁定，和内部节点的解引用。
  - `ValueRef` 是一个 Python 对象，是存在数据库中的二进制大型对象 BLOB(basic large object). 它间接使我们能够避免将整个数据存储一次性加载到内存中。
- `binary_tree.py` 定义了逻辑接口下的二叉树算法。
  - `BinaryTree` 提供二叉树的具体实现，包括get, insert, 和delete。`BinaryTree` 是一个 不可变的(immutable) 的树，所以数据的更新会产生一个新的树。
  - `BinaryNode` 实现了二叉树的节点的类。
  - `BinaryNodeRef` 是一个特殊的 `ValueRef` 实现，用来实现 `BinaryNode` 的序列化和反序列化。
- `physical.py` 定义了物理层，`Storage` 类提供了持久的，(大部分是)只可添加的记录存储。

模块中每个类都只有一个单一的职责，换句话说，每个类只有一个改变的原因。

### 读取值

我们将从一个简单的例子开始：从数据库里读取一个值。一起来看看怎么从  `example.db` 数据库里获取键为 `foo` 的值:

```
$ python -m dbdb.tool example.db get foo
```

这行代码从 `dbdb.tool` 中的 `main()` 函数开始运行。

```py
# dbdb/tool.py
def main(argv):
    if not (4 <= len(argv) <= 5):
        usage()
        return BAD_ARGS
    dbname, verb, key, value = (argv[1:] + [None])[:4]
    if verb not in {'get', 'set', 'delete'}:
        usage()
        return BAD_VERB
    db = dbdb.connect(dbname)          # CONNECT
    try:
        if verb == 'get':
            sys.stdout.write(db[key])  # GET VALUE
        elif verb == 'set':
            db[key] = value
            db.commit()
        else:
            del db[key]
            db.commit()
    except KeyError:
        print("Key not found", file=sys.stderr)
        return BAD_KEY
    return OK
```

函数 `connect()` 会打开一个数据库文件(或者是创建一个新的，但是永远不会覆盖其它的文件)，然后返回一个名为 `DBDB` 的实例:

```py
# dbdb/__init__.py
def connect(dbname):
    try:
        f = open(dbname, 'r+b')
    except IOError:
        fd = os.open(dbname, os.O_RDWR | os.O_CREAT)
        f = os.fdopen(fd, 'r+b')
    return DBDB(f)
# dbdb/interface.py
class DBDB(object):

    def __init__(self, f):
        self._storage = Storage(f)
        self._tree = BinaryTree(self._storage)
```

从上面的代码中，我们可以看到 `DBDB` 包含了一个对 `Storage` 实例的引用，它还把这个引用分享给了 `self._tree`。为什么要这样呢？`self._tree` 不可以单独访问存储吗？

关于哪个对象应该“拥有”一个资源，在设计中通常是一个重要的问题，因为它影响到了程序的安全性。我们稍后会解释这个问题。

当我们获得 `DBDB` 的实例后，就可以通过字典查找根据键获取值（`db[key]`），即通过 Python 解释器调用 `DBDB.__getitem__()`。

```py
# dbdb/interface.py
class DBDB(object):
# ...
    def __getitem__(self, key):
        self._assert_not_closed()
        return self._tree.get(key)

    def _assert_not_closed(self):
        if self._storage.closed:
            raise ValueError('Database closed.')
```

`__getitem__()` 通过调用 `_assert_not_closed` 确保数据库仍处于打开状态。啊哈！这里我们看到了一个 `DBDB` 需要直接访问 `Storage` 实例的原因：因为这样它可以强制执行前提条件。(你同意这个设计吗？你能想出一个不同的方式吗？)

然后 `DBDB` 通过调用由 `LogicalBase` 提供的 `_tree.get()` 函数查找内部的 `_tree` 上的 `key` 所对应的值：

```py
# dbdb/logical.py
class LogicalBase(object):
# ...
    def get(self, key):
        if not self._storage.locked:
            self._refresh_tree_ref()
        return self._get(self._follow(self._tree_ref), key)
```

`get()` 先检查储存是否被锁。目前，我们并不明白为什么在这里可能会有一个锁，但是我们可以猜到它是用来管理数据写入权限的。如果存储没有被锁会发生什么呢？

```py
# dbdb/logical.py
class LogicalBase(object):
# ...
def _refresh_tree_ref(self):
        self._tree_ref = self.node_ref_class(
            address=self._storage.get_root_address())
```

`_refresh_tree_ref` 用磁盘上数据重置数据的树的“视图”，这使我们能够操作最新的数据。

如果我们读取数据的时候，数据被锁了呢？这说明其它的进程或许正在更新这部分数据；我们读取的数据可能不是最新的。这通常被称为“脏读”(dirty read)。这种模式允许许多读者访问数据，而不用担心阻塞，相对的缺点就是数据可能不是最新的。

现在，一起来看看如何检索取数据：

```py
# dbdb/binary_tree.py
class BinaryTree(LogicalBase):
# ...
    def _get(self, node, key):
        while node is not None:
            if key < node.key:
                node = self._follow(node.left_ref)
            elif node.key < key:
                node = self._follow(node.right_ref)
            else:
                return self._follow(node.value_ref)
        raise KeyError
```

这是一个对节点引用的标准二叉搜索。通过阅读源码我们知道 `Node` 和 `NodeRef` 是 `BinaryTree` 中的值对象。它们是不可变的，它们的值永远不会改变。`Node` 类包括关联的键值和左右子项，这些联系都不会改变。只有当更换根节点时，整个 `BinaryTree` 的内容才会明显变化。这意味着在执行搜索时，我们不需要担心树的内容被改变。

一旦找到了相应的值，`main()` 函数会把这个值写入到 `stdout`，而不添加额外的换行符，以确保准确地显示用户数据。

#### 插入和更新

现在，我们在 `example.db` 数据库中，把 `foo` 键的值设为 `bar`：

```
$ python -m dbdb.tool example.db set foo bar
```

同样，它从运行 `dbdb.tool` 的 `main()` 函数开始，因为我们已经看过这段代码，所以我们将重点介绍以下重要部分：

```py
# dbdb/tool.py
def main(argv):
    ...
    db = dbdb.connect(dbname)          # CONNECT
    try:
        ...
        elif verb == 'set':
            db[key] = value            # SET VALUE
            db.commit()                # COMMIT
        ...
    except KeyError:
        ...
```

这次我们用 `db[key] = value` 设置值，它会调用 `DBDB.__setitem__()`。

```py
# dbdb/interface.py
class DBDB(object):
# ...
    def __setitem__(self, key, value):
        self._assert_not_closed()
        return self._tree.set(key, value)
```

`__setitem__` 确保了数据库的连接是打开的，然后调用 `_tree.set()` 来把键 `key` 和值 `value` 存入 `_tree`。

`_tree.set()` 由 `LogicalBase` 提供:

```py
# dbdb/logical.py
class LogicalBase(object):
# ...
    def set(self, key, value):
        if self._storage.lock():
            self._refresh_tree_ref()
        self._tree_ref = self._insert(
            self._follow(self._tree_ref), key, self.value_ref_class(value))
```

set() 先检查数据有没有被锁:

```py
# dbdb/storage.py
class Storage(object):
    ...
    def lock(self):
        if not self.locked:
            portalocker.lock(self._f, portalocker.LOCK_EX)
            self.locked = True
            return True
        else:
            return False
```

这里有两个重要的点需要注意：

- 我们使用了的第三方库提供的锁，名叫 `portalocker`。
- 如果数据库已经被锁了，`lock()` 函数会返回 `False`。否则，会返回 `True`。

回到 `_tree.set()`，现在我们明白了为什么需要先检查 `lock()` 的返回了：它会调用 `_refresh_tree_ref` 函数来获取最新的根节点引用，这样就不会丢失自上次从磁盘刷新树以来其它进程可能的更新。然后它会用一个已经插入或更新过数据的新树来替代原有的树。

插入和更新树不会改变任何一个节点。因为 `_insert()` 会返回一个新的树。新树与老树会共享数据不变的部分以节省内存和执行时间。我们使用了递归来实现：

```py
# dbdb/binary_tree.py
class BinaryTree(LogicalBase):
# ...
    def _insert(self, node, key, value_ref):
        if node is None:
            new_node = BinaryNode(
                self.node_ref_class(), key, value_ref, self.node_ref_class(), 1)
        elif key < node.key:
            new_node = BinaryNode.from_node(
                node,
                left_ref=self._insert(
                    self._follow(node.left_ref), key, value_ref))
        elif node.key < key:
            new_node = BinaryNode.from_node(
                node,
                right_ref=self._insert(
                    self._follow(node.right_ref), key, value_ref))
        else:
            new_node = BinaryNode.from_node(node, value_ref=value_ref)
        return self.node_ref_class(referent=new_node)
```

请注意我们总是返回一个新的节点(包装在一个 `NodeRef` 中)。我们建一个新的节点，它会与旧的节点共享未改变的子树。而不是更新节点指向新子树。这是我们的二叉树不可变(immutable)的原因。

你可能意识到有有个奇怪的地方：我们还没对磁盘上的数据做任何处理。我们目前所做的只是通过移动树的节点来操纵磁盘数据的视图。

为了真正的把新的数据写入磁盘，我们需要调用 `commit()` 函数。我们在前面的讲 `set` 操作的章节已经见过了这个函数。

`commit` 会把所有的脏状态(dirty state)写入内存中的，然后保存下树的新根节点的磁盘地址。

从 `commit` 的 API 接口开始看：

```py
# dbdb/interface.py
class DBDB(object):
# ...
    def commit(self):
        self._assert_not_closed()
        self._tree.commit()
```

`_tree.commit()` 是在 `LogicalBase` 里面实现的：

```py
# dbdb/logical.py
class LogicalBase(object)
# ...
    def commit(self):
        self._tree_ref.store(self._storage)
        self._storage.commit_root_address(self._tree_ref.address)
```

`NodeRef` 通过让它们的子节点调用 `prepare_to_store()` 完成序列化而完成自身的序列化。

```py
# dbdb/logical.py
class ValueRef(object):
# ...
    def store(self, storage):
        if self._referent is not None and not self._address:
            self.prepare_to_store(storage)
            self._address = storage.write(self.referent_to_string(self._referent))
```

这里的 `LogicalBase`里面的 `self._tree_ref`实际上是 `BinaryNodeRef`(`ValueRef` 的子类)。所以 `prepare_to_store()` 的具体实现方式为：

```py
# dbdb/binary_tree.py
class BinaryNodeRef(ValueRef):
    def prepare_to_store(self, storage):
        if self._referent:
            self._referent.store_refs(storage)
```

其中提及的 `BinaryNode`，`_referent` 要求它的引用存储它们。

```py
# dbdb/binary_tree.py
class BinaryNode(object):
# ...
    def store_refs(self, storage):
        self.value_ref.store(storage)
        self.left_ref.store(storage)
        self.right_ref.store(storage)
```

这个递归会在任何 `NodeRef` 有未写入的数据更新(比如说缺少 `_address`)的时候一直循环下去。

现在让我们来回到 `ValueRef` 里的 `store` 方法。`store()` 的最后一步是序列化这个节点，然后保存它的存储地址：

```py
# dbdb/logical.py
class ValueRef(object):
# ...
    def store(self, storage):
        if self._referent is not None and not self._address:
            self.prepare_to_store(storage)
            self._address = storage.write(self.referent_to_string(self._referent))
```

这里，`NodeRef` 的 `_referent` 保证会有所有它自身引用的地址，所以我们通过创建代表这个节点的字节串(bytestring)来序列化它：

```py
# dbdb/binary_tree.py
class BinaryNodeRef(ValueRef):
# ...
    @staticmethod
    def referent_to_string(referent):
        return pickle.dumps({
            'left': referent.left_ref.address,
            'key': referent.key,
            'value': referent.value_ref.address,
            'right': referent.right_ref.address,
            'length': referent.length,
        })
```

在 `store()` 中更新地址在实际上是改变 `ValueRef`。因为它对用户可见的值没有任何影响，所以我们可以认为它是不可变的。

根节点 `_tree_ref` 在 `store()` 完成之后(在 `LogicalBase.commit()` 中)，所有的数据就已经保存在磁盘上了。现在我们可以t提交根节点地址了：

```py
# dbdb/physical.py
class Storage(object):
# ...
    def commit_root_address(self, root_address):
        self.lock()
        self._f.flush()
        self._seek_superblock()
        self._write_integer(root_address)
        self._f.flush()
        self.unlock()
```

我们确保文件句柄已被刷新(所以系统就知道我们想要所有数据都保存到类似SSD 的稳定存储中)以及返回了根节点的地址。我们知道最后一次写入是具有原子性(atomic)的，因为我们将磁盘地址存储在扇区边界上(sector boundary)。这是文件中的最靠前的，所以无论扇区大小如何，这都是正确的，单扇区磁盘写入能由磁盘硬件保证原子性。

因为根节点地址要么是旧值要么是新值(没有中间值)，所以其它进程可以从数据库中读取而不需要锁。外部进程可能会看到新树或者旧树，但不会同时看到两者。因此，提交是原子性的。

因为我们在赋予根节点地址之前，会把新的数据写入磁盘并调用 `fsync` 系统调用[^fsync]，所以未提交的数据是无法访问的。 相反，一旦根节点地址被更新，我们知道它引用的所有数据也在磁盘上。以这种方式，提交也具有持久性(durability)。

[^fsync]:对文件描述符调用 `fsync` 会要求操作系统和硬盘驱动器（或SSD）立即写入所有缓冲数据。操作系统和驱动器通常不会为了提高性能而立即写入所有内容。

这样就完成了！

## NodeRefs如何节省内存

为了避免把这个树的数据同时保存在内存中，当从磁盘读取逻辑节点时，其左和右子节点的磁盘地址(还有值)将被加载到内存中。所以访问子节点及其值需要调用一个额外的函数 `NodeRef.get()` 来获取真正的数据。

`NodeRef` 只需包含一个地址：

```
+---------+
| NodeRef |
| ------- |
| addr=3  |
| get()   |
+---------+
```

对其调用 `get()` ，`NodeRef` 会返回具体的节点，并包括节点引用 `NodeRef` 类。

```
+---------+     +---------+     +---------+
| NodeRef |     | Node    |     | NodeRef |
| ------- |     | ------- | +-> | ------- |
| addr=3  |     | key=A   | |   | addr=1  |
| get() ------> | value=B | |   +---------+
+---------+     | left  ----+
                | right ----+   +---------+
                +---------+ |   | NodeRef |
                            +-> | ------- |
                                | addr=2  |
                                +---------+
```

当树的更改未提交时，它们保存在内存中，包括从根向下到更改的叶子。 当更改还没保存到磁盘时，所以被更改的节点包含具体的键和值，但是没有磁盘地址。处理写入的进程可以看到这些未提交的更改，并且可以在发出提交之前再次对其进行更改，这是因为 `NodeRef.get()` 会返回一个未提交的值（如果有的话）; 在通过 API 访问时，提交和未提交的数据之间没有区别。所有更新对其它读数据的进程都是原子的，因为只有新的根节点地址被写入磁盘，更改才可见。磁盘上的文件锁会阻止并发的更新操作。文件会在第一次更新时上锁，并在提交后解锁。

## 读者练习

`DBDB` 允许多进程同时访问同一个数据库而不阻塞。为做到这一点，我们付出的是，检索时有时获得的是过时的数据。如果我们需要总是读取最新的数据该怎么办？ 一个常见的场景是读取值，然后根据该值进行更新。 你如何在 `DBDB`上实现这个方法呢？你需要为提供这个功能进行哪些权衡？

更新数据存储的算法可以通过在 `interface.py` 文件中替换 `BinaryTree` 来使用别的算法。 比如说可以用 B-树, B+ 树或其它的结构来提高数据库的性能。一个平衡的二叉树需要做 $O(log2(n))$ 次随机节点的读取，来查找值。而B+树只需要更少的次数，比如 $O(log32(n))$ 次，因为每个节点有 32 个子节点而不是 2 个。这在实践中会包含巨大的难度。比如 40 亿条数据中查找一条记录，这需要大约 $log2(2 ^ {32})= 32$ 至 $log32(2 ^ {32})=6.4$ 次查找。每个查找都是随机访问，这对于旋转的硬盘来说开销非常大。SSD 或许可以减少延迟，但 I/O 的开销仍然存在。

默认情况下，值以字节的形式（为了能直接传入到 `Storage`）存储在 `ValueRef` 里。二叉树的节点是 `ValueRef` 的子类。通过 json 或者  msgpack 格式保存更丰富的数据只需要编写自己的文件并将其设置为 `value_ref_class`。`BinaryNodeRef` 就是一个使用 `pickle` 来序列化数据的例子。

数据库压缩是另一个有趣的练习。压缩可以随着树的移动通过中序遍历完成。如果树节点全部在一起可能是最好的，因为它们是查找数据片段时的遍历对象。将尽可能多的中间节点打包进到磁盘扇区中可以提高读取性能，至少在压缩之后是这样。如果你打算完成这个练习的话，这里有一些细节需要注意(例如，内存使用)。请记住：在修改前后，对性能进行基准测试！这会使你对结果感到惊讶。

## 模式和原则

测试接口，而不是实现。作为开发 DBDB 的一部分，我编写了许多测试，描述了我希望如何使用它。第一次测试是针对内存中版本的数据库运行的，然后我扩展了 DBDB 以持久化到磁盘，甚至后来添加了 NodeRefs 的概念。大多数测试都不需要改变，这让我相信它仍能正常工作。

尊重单一责任原则。类应该只有一个更改的原因。DBDB 的情况并非如此，但有多种扩展途径，只需要进行局部更改。当我添加特性时重构是一种乐趣！

## 总结

DBDB 是一个简单的数据库，它提供了简单的保证，但匆忙中还是变得有些复杂。为了管理这种复杂性，我所做的最重要的事情是用一个不可变的数据结构实现一个表面上可变的对象。我鼓励你当你处理一个棘手问题时，考虑一下这个技巧，这让你能跟踪更多的边缘情况。








