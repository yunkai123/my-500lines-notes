# 分布式系统（Clustering by Consensus）

## 作者

Dustin J. Mitchell。Dustin是一个开源的软件开发者，同时也是 Mozilla 的一名发布工程师。他参与的项目包括在 Puppet 中配置主机系统，一个基于 Flask 的 Web 框架，为防火墙配置做单元测试，还有一个在 Twisted Python 下开发的持续集成系统框架。

## 引言

在本文档，我们将会一起探索如何实现一个网络协议用于可靠的分布式计算。正确实现一个网络协议并不简单，因此我们会采用一些技术来尽可能的减少错误，并修复剩余的一部分。要构建一个可靠的软件，同样需要一些特别的开发和调试技巧。

## 情景示例

本文的重点在于网络协议的实现，但是首先让我们以简单的银行账户管理服务为例做一个思考。在这个服务中，每一个账户都有一个当前余额，同时每个账户都有自己的账号。用户可以通过“存款”、“转账”、“查询当前余额”等操作来连接账户。“转账”操作同时涉及了两个账户：转出账户和转入账户，并且如果账户余额不足，转账操作必须被驳回。

如果这个服务仅仅在一个服务器上部署，很容易就能够实现：使用一个操作锁来确保“转账”操作不会同时进行，同时对转出账户的余额进行校验。然而，银行不可能仅仅依赖于一个服务器来储存账户余额这样的关键信息，通常，这些服务都是被分布在多个服务器上，每一个服务器各自运行着相同代码的实例。用户可以通过任何一个服务器来操作账户。

在一个简单的分布式处理系统的实现中，每个服务器都会保存一份账户余额的副本。它会处理任何收到的操作，并且将账户余额的更新发送给其他的服务器。但是这种方法有一个严重的问题：如果两个服务器同时对一个账户进行操作，哪一个新的账户余额是正确的？即使服务器不共享余额而是共享操作，对一个账户同时进行转账操作也可能造成透支。

从根本上来说，这些错误的发生都是由于服务器使用它们本地状态来响应操作，而不是首先确保本地状态与其他服务器相匹配。比如，想象服务器 A 接到了从账号 101 向账号 202 转账的操作指令，而此时服务器 B 已经处理了另一个把账号 101 的钱都转到账号 202 的请求，却没有通知服务器 A。这样，服务器 A 的本地状态与服务器 B 不一样，即使会造成账户 101 透支，服务器 A 依然允许从账号101进行转账操作。

## 分布式状态机

为了防止上述情况发生我们采用了一种叫做“分布式状态机”的工具。它的思路是对每个同样的输入，每个服务器都运行同样的对应的状态机。由于状态机的特性，对于同样的输入每个服务器的输出都是一样的。“转账”、“查询当前余额”等操作及其参数（账号和余额）表示状态机的输入。

这个应用的状态机比较简单：

```py
def execute_operation(state, operation):
    if operation.name == 'deposit':
        if not verify_signature(operation.deposit_signature):
        return state, False
        state.accounts[operation.destination_account] += operation.amount
        return state, True
    elif operation.name == 'transfer':
        if state.accounts[operation.source_account] < operation.amount:
            return state, False
            state.accounts[operation.source_account] -= operation.amount
        state.accounts[operation.destination_account] += operation.amount
        return state, True
    elif operation.name == 'get-balance':
        return state, state.accounts[operation.account]
```

值得注意的是，运行“查询当前余额”操作时虽然并不会改变当前状态，但是我们依然把它当做一个状态变化操作来实现。这确保了返回的余额是分布式系统中的最新信息，而不是基于一个服务器上的本地状态来进行返回的。  

这可能跟你在计算机课程中学习到的典型的状态机不太一样。传统的状态机是一系列有限个状态的集合，每个状态都与一个标记的转移行为相对应，而在本文中，状态机的状态是账户余额的集合，因此存在无穷多个可能的状态。但是，状态机的基本规则同样适用于本文的状态机：对于同样的初始状态，同样的输入总是有同样的输出。

因此，分布式状态机确保了对于同样的操作，每个主机都会有同样的响应。但是前文提到的确保每个服务器都同意状态机的输入的问题依然存在。这是一个一致性问题，为了解决它我们采用了一种派生的 Paxos 算法。

## Paxos 共识

Leslie Lamport 于 1990 年在一篇神奇的论文中首先提出了 Paxos 算法，并最终在 1998 年发表了这篇名为 The Part-Time Parliament[^parttime] 的论文。Lamport 的论文比本文中介绍的要更加的详细。

Paxos 最简单的形式是提供一个让一组服务器在任何时候都对一个值达成一致。Multi-Paxos 算法在此基础上确定一系列有序的值，一次一个。为了实现分布式状态机，我们使用 Multi-Paxos 算法让每个状态机输入达成一致并按顺序执行。

[^parttime]: L. Lamport, "The Part-Time Parliament," ACM Transactions on Computer Systems, 16(2):133–169, May 1998

### 朴素 Paxos

让我们从“朴素 Paxos”开始，它也被称为议会协议，它提供了一种方法来对一个永不改变的值达成一致。Paxos 这个名字来自于论文 The Part-Time Parliament 中的一个神话岛屿，在那里，立法者通过一个被 Lamport 称为议会协议的程序投票立法。

我们会在下面看到这个算法是实现更复杂算法的基础。在示例中，我们达成一致的值是我们假设中的银行要处理的第一个交易。虽然银行每天都会处理交易，但是第一个交易只会发生一次并且不会改变，所以我们可以使用朴素 Paxos 来就其细节达成一致。

该协议通过一系列投票进行，每一次投票都由集群中的一名成员领导，这名成员被称为 Proposer。每一张选票都有一个基于整数和 Proposer 身份的唯一选票编号。Proposer 的目的是让充当 Acceptor 的大多数集群成员在没有确定另一个值的前提下接受它的值。

![](/cluster/markdown/img/ballot.png)

投票开始时，Proposer 发送一个带有选票编号 N 的 `Prepare` 消息给 Acceptor 并等待大多数成员的反馈。

`Prepare` 消息是对小于 N 的最大选票编号可接受值（如果有的话）的请求，Acceptor 将响应一个包含他们已经接受的任何值的 `Promise`，承诺将来不接受任何编号小于 N 的选票。如果 Acceptor 已经对更大的选票编号做出了承诺，那么它将在 `Promise` 中包含这个数字，表明 Proposer 身份已经被抢占。在这种情况下，投票已经结束，但是 Proposer 可以再次尝试另一次投票（并且使用更大的选票编号）。

当 Proposer 收到大多数 Acceptor 的回复后，它会向所有 Acceptor 发送一个包含选票编号和值的 `Accept` 消息。如果 Proposer 没有从任何 Acceptor 那里收到任何现有的值，那么它就会发送自己希望的值。否则，它将发送编号最高的 `Promise` 中的值。

除非打算违反承诺，否则每个 Acceptor 都将 `Accept` 消息中的值记录为已接收并回复一个 `Accepted` 消息。当 Proposer 从大多数 Acceptor 那里获取选票编号后，值就被决定，同时投票完成。

回到示例中，最开始的时候没有其它值被接受，因此 Acceptor 都返回一个没有值的 `Promise`，而 Proposer 发送一个包含其值的 `Accept` 信息，比如：

```py
operation(name='deposit', amount=100.00, destination_account='Mike DiBernardo')
```

如果另一个 Proposer 稍后发起了一次投票，其投票编号较低，并且进行了不同的操作（例如转账到 Dustin J.Mitchell 的帐户），那么 Acceptor 根本不会接受它。如果该选票的选票编号更高，那么 Acceptor 的 `Promise` 将通知 Proposer Michael 的 $100.00 存款操作，而 Proposer 将在 `Accept` 消息中发送该操作而不是转账到 Dustin。新的投票被接受，支持和第一轮投票相同的值。

事实上，协议永远不会允许两个不同的值被决定，即使投票重叠，消息延迟，或者少数 Acceptor 出现问题。

当两个 Proposer 同时进行投票时，两张选票都不会被接受。两个 Proposer 都会重新提议并希望其中一个获胜。但如果时间恰好的话僵局有可能会无限期地持续下去。

考虑以下事件顺序：

- Proposer A执行编号为 1 的投票的 `Prepare`/`Promise` 阶段。
- 在 Proposer A 的提议被接受之前，Proposer B 执行编号为 2 的选票的 `Prepare`/`Promise` 阶段。
- 当 Proposer A 发送了编号为1的投票的 `Accept` 消息时，Acceptor 们拒绝了它因为它们刚刚承诺了编号为 2 的投票。
- Proposer A 的反应是在 Proposer B 发送 `Accept` 信息之前立刻发送一个有较大编号3的 `Prepare` 消息。
- Proposer B的后续 `Accept` 信息也被拒绝，并重复这个过程。

碰到不那么幸运的时机，在长距离连接中更常见，因为在这种情况下发送消息和获得响应之间的时间很长，这种死锁可能会持续很多回合。

### Multi-Paxos

就单一的静态值达成共识用处并不大。像银行账户服务等集群系统更希望就随时间变化的特定状态（比如账户余额）达成一致。我们将像状态机转换一样使用 Paxos 对每个操作达成一致。

事实上，Multi-Paxos 由一系列按顺序编号的朴素 Paxos 实例（时隙slot）组成。每次状态转换都会获取一个“槽号”，并且集群的每个成员都以严格的数字顺序执行状态转换。为了更改集群的状态(例如处理一个传输操作)，我们会尝试在下一个时隙中就该操作达成一致。这意味着在每个消息中添加一个槽号，并在每个时隙的基础上跟踪所有协议状态。

为每个时隙运行 Paxos 算法(至少两次往返)会很慢。Multi-Paxos 算法通过对所有时隙使用相同的选票编号集进行优化，并同时对所有时隙执行 `Prepare`/`Promise` 阶段。

### 不易实现的Paxos

在真实软件中实现 Multi-Paxos 是出了名的困难，因此催生了许多嘲笑 Lamport 的论文“Paxos Made Simple”的文章，比如标题是“Paxos Made Practical”。

首先，上面描述的多 Proposer 问题在繁忙的环境中会出现问题，因为在每个时隙中每个集群成员都试图决定其状态机操作。解决办法是选出一个“Leader”来负责提交每个时隙的选票。所有其它集群节点都将新操作发送给 Leader 来执行。因此，在只有一名 Leader 的正常运作中，不会发生选票冲突。

`Prepare`/`Promise` 阶段可以起到 Leader 选举的作用：无论哪个集群成员拥有最近承诺的选票编号，都将被视为 Leader。然后，Leader 可以自由地直接执行 `Accept`/`Accepted` 阶段，而不必重复第一阶段。我们在下面会看到，实际上 Leader 的选举相当复杂。

朴素 Paxos 只能保证集群不会做出相互冲突的决策，它不能保证决策会被做出。例如，如果初始 `Prepare` 消息丢失并且没有到达 Acceptor，那么 Proposer 将等待一个永远不会到达的 `Promise` 消息。解决这一问题需要精心设计的重新传输：数量足够用来取得进一步的效果，但又不至于太多以致集群陷入数据包风暴。

另一个问题是决策的传播。在正常情况下，一个简单的 `Decision` 消息广播就可以解决这个问题。但是，如果消息丢失，节点可能永远不知道该决策，并且无法为以后的时隙进行状态机转换。因此，需要实现某种机制来共享已决策的提议。

我们使用的分布式状态机带来了另一个有趣的挑战：启动。当一个新节点启动时，它需要获取集群之前的所有状态。尽管它可以通过追踪所有时隙的决策来实现这一点，但是一个成熟的集群可能涉及数百万个时隙。另外，我们还需要一些方法来初始化一个新的集群。

理论和算法的讨论已经够多了，下面让我们看看代码。

## Cluster 介绍

本文中的 cluster 库实现了 Multi-Paxos 的一种简单形式。它被设计成一个库来为更大的应用程序提供一致性服务。

这个库的用户将依赖于它的正确性，所以对代码的构建非常重要，这样我们就可以查看并测试它与标准规范的对应关系。复杂的协议可能会出现复杂的故障，因此我们将对再现和调试罕见故障提供支持。

本文是概念证明代码：足以证明核心概念的实用性，但不具备生产中使用的条件。代码的核心结构已经构建好所以其它内容可以稍后添加，从而对核心实现进行最小的更改。

让我们开始。

### 类型和常量

集群协议使用了15种不同的消息类型，每种类型都定义为一个 Python 命名元组。

```py
Accepted = namedtuple('Accepted', ['slot', 'ballot_num'])
Accept = namedtuple('Accept',['slot', 'ballot_num', 'proposal'])
Decision = namedtuple('Decision', ['slot', 'proposal'])
Invoked = namedtuple('Invoked', ['client_id', 'output'])
Invoke = namedtuple('Invoke', ['caller', 'client_id', 'input_value'])
Join = namedtuple('Join', [])
Active = namedtuple('Active', [])
Prepare = namedtuple('Prepare', ['ballot_num'])
Promise = namedtuple('Promise', ['ballot_num', 'accepted_proposals'])
Propose = namedtuple('Propose', ['slot', 'proposal'])
Welcome = namedtuple('Welcome', ['state', 'slot', 'decisions', 'leader']) # 添加leader，解决新加入的节点无法知道leader的问题
Decided = namedtuple('Decided', ['slot'])
Preempted = namedtuple('Preempted', ['slot', 'preempted_by'])
Adopted = namedtuple('Adopted', ['ballot_num', 'accepted_proposals'])
Accepting = namedtuple('Accepting', ['leader'])
Conflict = namedtuple("Conflict", ["slot", "max_slot", "proposal"])
```

使用命名元组来描述每种消息类型可以保持代码的整洁，并有助于避免一些简单的错误。如果指定的属性不正确，命名元组的构造函数将引发一个异常，从而使错误更容易被发现。元组可以在日志消息中很好地格式化，另一个额外的好处是它不会使用字典那么多的内存。

创建一个消息：

```py
msg = Accepted(slot=10, ballot_num=30)
```

可以访问消息的字段：

```py
got_ballot_num = msg.ballot_num
```

我们将在下面了解这些消息的含义。代码还引入了一些常量，其中大多数用来定义各种消息的超时：

```py
JOIN_RETRANSMIT = 0.7
CATCHUP_INTERVAL = 0.6
ACCEPT_RETRANSMIT = 1.0
PREPARE_RETRANSMIT = 1.0
INVOKE_RETRANSMIT = 0.5
LEADER_TIMEOUT = 1.0
NULL_BALLOT = Ballot(-1, -1)  # 排序在所有真实选票之前
NOOP_PROPOSAL = Proposal(None, None, None)  # 没有操作填充其它空时隙
```

最后，Cluster 使用了两个命名数据类型来和协议描述相对应：

```py
Proposal = namedtuple('Proposal', ['caller', 'client_id', 'input'])
Ballot = namedtuple('Ballot', ['n', 'leader'])
```

### 组件模型

由于记忆力有限，我们不能一次推理整个集群的实现——这太多了，所以很容易遗漏细节。因此大型的代码库很难测试：测试用例必须操纵许多移动的代码块，而且很脆弱，几乎对代码的任何更改都会导致失败。

为了提高可测试性并保持代码可读性，我们将 Cluster 分解为几个与协议中描述的角色相对应的类。每个都是 `Role` 类的子类。

```py
class Role(object):

    def __init__(self, node):
        self.node = node
        self.node.register(self)
        self.running = True
        self.logger = node.logger.getChild(type(self).__name__)

    def set_timer(self, seconds, callback):
        return self.node.network.set_timer(self.node.address, seconds,
                                           lambda: self.running and callback())

    def stop(self):
        self.running = False
        self.node.unregister(self)
```

集群节点所拥有的角色由表示网络中单个节点的 `Node` 类联系在一起。`Role` 在执行过程中从节点添加和移除。到达节点的消息通过调用一个命名方式为在消息类型后边带有 `do_` 前缀的方法将消息转发给所有活动角色。这些 `do_` 方法接收消息的属性作为关键字参数，以便于访问。`Node` 类出于便利还提供了一个 `send` 方法，使用 `functools.partial` 为 `Network` 类的相同方法提供一些参数。

```py
class Node(object):
    unique_ids = itertools.count()

    def __init__(self, network, address):
        self.network = network
        self.address = address or 'N%d' % self.unique_ids.next()
        self.logger = SimTimeLogger(
            logging.getLogger(self.address), {'network': self.network})
        self.logger.info('starting')
        self.roles = []
        self.send = functools.partial(self.network.send, self)

    def register(self, roles):
        self.roles.append(roles)

    def unregister(self, roles):
        self.roles.remove(roles)

    def receive(self, sender, message):
        handler_name = 'do_%s' % type(message).__name__

        for comp in self.roles[:]:
            if not hasattr(comp, handler_name):
                continue
            comp.logger.debug("received %s from %s", message, sender)
            fn = getattr(comp, handler_name)
```

### 应用程序接口

应用程序在每个集群成员上创建并启动一个 `Member` 对象，它提供每个应用程序特定的状态机和一系列的对等节点。`Member` 对象在它加入一个已存在集群的时候添加一个引导角色，或者在它创建一个新集群的时候提供种子。然后它在一个单独线程运行协议（通过 `Network.run` 方法）。

应用程序通过 `invoke` 方法与集群交互，该方法就状态转换进行提议。一旦提议被决定并且状态机运行起来，`invoke` 将返回状态机的输出。该方法使用一个简单的同步队列来等待来自协议线程的结果。

```py
class Member(object):

    def __init__(self, state_machine, network, peers, seed=None,
                 seed_cls=Seed, bootstrap_cls=Bootstrap):
        self.network = network
        self.node = network.new_node()
        if seed is not None:
            self.startup_role = seed_cls(self.node, initial_state=seed, peers=peers,
                                      execute_fn=state_machine)
        else:
            self.startup_role = bootstrap_cls(self.node,
                                      execute_fn=state_machine, peers=peers)
        self.requester = None

    def start(self):
        self.startup_role.start()
        self.thread = threading.Thread(target=self.network.run)
        self.thread.start()

    def invoke(self, input_value, request_cls=Requester):
        assert self.requester is None
        q = Queue.Queue()
        self.requester = request_cls(self.node, input_value, q.put)
        self.requester.start()
        output = q.get()
        self.requester = None
        return output
```

### 角色类

让我们依次查看库中的每个角色类。

#### Acceptor

`Acceptor` 类实现协议中的 Acceptor 角色，因此它必须存储代表它的最近承诺的投票编号，以及每个时隙的的一组已接受的提议。然后它根据协议响应 `Prepare` 和 `Accept` 信息。结果是一个容易与协议进行比较的短类。

对于 Acceptor 来说，Multi-Paxos 算法很像在消息中添加了时隙号的朴素 Paxos 算法。

```py
class Acceptor(Role):

    def __init__(self, node):
        super(Acceptor, self).__init__(node)
        self.ballot_num = NULL_BALLOT
        self.accepted_proposals = {} # 格式为 {slot: (ballot_num, proposal)}

    def do_Prepare(self, sender, ballot_num):
        '''接收到 Prepare 消息'''
        if ballot_num > self.ballot_num:
            self.ballot_num = ballot_num
            # 它可能是下一个 Leader
            self.node.send([self.node.address], Accepting(leader=sender))

        self.node.send([sender], Promise(ballot_num=self.ballot_num, accepted_proposals=self.accepted_proposals))

    def do_Accept(self, sender, ballot_num, slot, proposal):
        '''响应 Accept 消息'''
        if ballot_num >= self.ballot_num:
            self.ballot_num = ballot_num
            acc = self.accepted_proposals
            if slot not in acc or acc[slot][0] < ballot_num:
                acc[slot] = (ballot_num, proposal)

        self.node.send([sender], Accepted(
            slot=slot, ballot_num=self.ballot_num
        ))
```

#### Replica

Replica 类是最复杂的角色类，它有一些密切相关的功能：

- 提出新的提议；
- 在提议被通过的时候调用本地状态机；
- 追踪当前的 Leader；
- 将新启动的节点添加到集群。

Replica 创建新的提议来响应从客户端调用的消息，选择一个它认为没有使用的时隙向当前的 Leader 发送一个 `Propose` 消息。如果所选时隙被一致认为属于不同的提议，那么 Replica 必须使用新的时隙重新提议。

![](/cluster/markdown/img/replica.png)

`Decision` 消息代表集群已经达成共识的时隙。此处，Replica 存储新决策，然后运行状态机，直到到达未决策的时隙。Replica 从本地状态机已处理的已提交时隙中区分集群已经达成一致的决策时隙。当时隙没有按顺序被决策的时候，提交的提议可能会滞后，等待下一个时隙进行决策。当一个时隙被提交，每个 Replica 都会返回一个 `Invoked` 消息连同操作结果给请求者。

在某些情况下，有可能一个时隙既没有活跃的提议也没有决策。状态机需要一个接一个的执行每个时隙，因此集群需要就填充时隙的内容达成共识。为了避免这种可能性，Replica 在遇到时隙时会提出“禁止操作”的提议。如果最终决定了这样的提议，则状态机对该时隙不执行任何操作。

同样，同一提议有可能被决策两次。对于任何此类重复的提议，Replica 将跳过调用状态机，而不会对该时隙进行任何过渡。

Replica 需要知道哪个节点是活跃的 Leader 才能向其发送 `Propose` 消息。要做到这一点，需要大量细节，我们将在后面看到。每个 Replica 使用三个信息源跟踪活动的 Leader。

当 Leader 变活跃时，它会向同一个节点上的 Replica 发送 `Adopted` 消息。

![](/cluster/markdown/img/adopted.png)

当 Acceptor 角色向新的 Leader 发送 `Promise` 时，它会向其本地 Replica 发送 `Accepting` 消息。

![](/cluster/markdown/img/accepting.png)

活跃的 Leader 发送 `Active` 消息作为心跳，如果在 `LEADER_TIMEOUT` 到期之前没有收到这个消息，Replica 将假定该 Leader 已经死亡并移动到下一个 Leader。在这种情况下，所有 Replica 选择相同的新 Leader 很重要，我们通过对成员进行排序并在列表中选择下一个成员来完成这项工作。

![](/cluster/markdown/img/active.png)

最终，当节点加入网络时，Bootstrap 角色将发送一条 `Join` 消息。Replica 以包含最新状态的 `Welcome` 消息进行响应，从而使新节点能够快速地跟上进度。

![](/cluster/markdown/img/bootstrap.png)

```py

class Replica(Role):

    def __init__(self, node, execute_fn, state, slot, decisions, peers, leader=None):
        super(Replica, self).__init__(node)
        self.execute_fn = execute_fn
        self.state = state
        self.slot = slot
        self.decisions = decisions
        self.peers = peers
        self.proposals = {}
        self.next_slot = slot
        self.latest_leader_timeout = None
        if leader:
            self.latest_leader = leader
            self.leader_alive()
        else:
            self.latest_leader = None
        

    def do_Conflict(self, sender, slot, max_slot, proposal):
        if slot in self.proposals and self.proposals[slot] == proposal:
            self.logger.info("receiving conflict from leader at slot %d" % slot)
            del self.proposals[slot]
            self.next_slot = max(self.next_slot, max_slot + 1)

    # 进行提议

    def do_Invoke(self, sender, caller, client_id, input_value):
        proposal = Proposal(caller, client_id, input_value)
        slot = next((s for s, p in self.proposals.items() if p == proposal), None)
        self.propose(proposal, slot)

    def propose(self, proposal, slot=None):
        '''发送（或者重新发送，如果明确了时隙）提议给 Leader '''
        if not slot:
            slot, self.next_slot = self.next_slot, self.next_slot + 1
        self.proposals[slot] = proposal
        # 寻找一个有效的Leader
        # 要么是已知最新的，要么是自己（这会触发一个 scout 使我们成为 Leader）
        leader = self.latest_leader or self.node.address
        self.logger.info("proposing %s at slot %d to leader %s" % (proposal, slot, leader))
        self.node.send([leader], Propose(slot=slot, proposal=proposal))

    # 处理已通过的提议

    def do_Decision(self, sender, slot, proposal):
        assert not self.decisions.get(self.slot, None), "next slot to commit is already decided"
        if slot in self.decisions:
            assert self.decisions[slot] == proposal, "slot %d already decided with %r!" % (slot, self.decisions[slot])
            return
        self.decisions[slot] = proposal
        self.next_slot = max(self.next_slot, slot + 1)

        # 如果提议丢失在一个新时隙重新提议
        our_proposal = self.proposals.get(slot)
        if our_proposal is not None and our_proposal != proposal and our_proposal.caller:
            self.propose(our_proposal)

        # 执行待定的、通过的提议
        while True:
            commit_proposal = self.decisions.get(self.slot)
            if not commit_proposal:
                break # 还未通过
            commit_slot, self.slot = self.slot, self.slot + 1

            self.commit(commit_slot, commit_proposal)

    def commit(self, slot, proposal):
        """实际提交一个已通过且在序列中的提议"""
        decided_proposals = [p for s, p in self.decisions.items() if s < slot]
        if proposal in decided_proposals:
            self.logger.info("not committing duplicate proposal %r at slot %d", proposal, slot)
            return # 重复
        
        self.logger.info("committing %r at slot %d" % (proposal, slot))
        if proposal.caller is not None:
            # 执行客户端操作
            self.state, output = self.execute_fn(self.state, proposal.input)
            self.node.send([proposal.caller], Invoked(client_id=proposal.client_id, output=output))

    # 追踪 Leader

    def do_Adopted(self, sender, ballot_num, accepted_proposals):
        self.latest_leader = self.node.address
        self.leader_alive()

    def do_Accepting(self, sender, leader):
        self.latest_leader = leader
        self.leader_alive()

    def do_Active(self, sender):
        if sender != self.latest_leader:
            return
        self.leader_alive()

    def leader_alive(self):
        if self.latest_leader_timeout:
            self.latest_leader_timeout.cancel()

        def reset_leader():
            idx = self.peers.index(self.latest_leader)
            self.latest_leader = self.peers[(idx + 1) % len(self.peers)]
            self.logger.debug("leader timed out; tring the next one, %s", self.latest_leader)
        self.latest_leader_timeout = self.set_timer(LEADER_TIMEOUT, reset_leader)

    # 添加新集群成员

    def do_Join(self, sender):
        if sender in self.peers:
            self.node.send([sender], Welcome(
                state=self.state, slot=self.slot, decisions=self.decisions, leader=self.latest_leader
            ))
```

#### Leader，Scout 和 Commander

Leader 的主要任务是发送 `Propose` 消息要求进行新的投票并做出决定。成功完成协议的 `Prepare`/`Promise` 部分后，Leader 将处于“活跃状态”。活跃的领导者可以立即发送 `Accept` 消息以响应 `Propose` 消息。

为了与每个角色一个类的模型保持一致，Leader 委派 Scout 和 Commander 角色来执行协议的每个部分。

```py

class Leader(Role):

    def __init__(self, node, peers, commander_cls=Commander, scout_cls=Scout):
        super(Leader, self).__init__(node)
        self.ballot_num = Ballot(0, node.address)
        self.active = False
        self.proposals = {}
        self.commander_cls = commander_cls
        self.scout_cls = scout_cls
        self.scouting = False
        self.peers = peers

    def start(self):
        def active():
            if self.active:
                self.node.send(self.peers, Active())
            self.set_timer(LEADER_TIMEOUT / 2.0, active)
        active()

    def spawn_scout(self):
        assert not self.scouting
        self.scouting = True
        self.scout_cls(self.node, self.ballot_num, self.peers).start()

    def do_Adopted(self, sender, ballot_num, accepted_proposals):
        self.scouting = False
        self.proposals.update(accepted_proposals)
        self.logger.info("leader becoming active")
        self.active = True

    def spawn_commander(self, ballot_num, slot):
        proposal = self.proposals[slot]
        self.commander_cls(self.node, ballot_num, slot, proposal, self.peers).start()

    def do_Preempted(self, sender, slot, preempted_by):
        if not slot:
            self.scouting = False
        self.logger.info("leader preempted by %s", preempted_by.leader)
        self.active = False
        self.ballot_num = Ballot((preempted_by or self.ballot_num).n + 1, self.ballot_num.leader)

    def do_Propose(self, sender, slot, proposal):
        if slot not in self.proposals:
            if self.active:
                self.proposals[slot] = proposal
                self.logger.info("spawning commander for slot %d" % (slot,))
                self.spawn_commander(self.ballot_num, slot)
            else:
                if not self.scouting:
                    self.logger.info("got PROPOSE when not active - scouting")
                    self.spawn_scout()
                else:
                    self.logger.info("got PROPOSE while scouting; ignored")
        else:
            self.logger.info("got PROPOSE for a slot %d already being proposed (%s)" % (slot, self.proposals[slot]))
            if self.proposals[slot].input != proposal.input: # 添加提议slot冲突后的处理
                max_slot = max(self.proposals.keys())
                self.node.send([sender], Conflict(slot=slot, max_slot=max_slot, proposal=proposal))

```

当 Leader 希望变为活跃状态时它会创建一个 Scout 角色，以响应其处于非活跃状态时收到 `Propose`。Scout 发送（并在必要时重新发送） `Prepare` 消息，并收集 `Promise` 答复，直到收到大多数对等端点的回复或被抢占为止。 它分别回复 Leader `Adopted` 或 `Preempted`。

![](/cluster/markdown/img/leaderscout.png)

```py
class Scout(Role):

    def __init__(self, node, ballot_num, peers):
        super(Scout, self).__init__(node)
        self.ballot_num = ballot_num
        self.accepted_proposals = {}
        self.acceptors = set([])
        self.peers = peers
        self.quorum = len(peers) // 2 + 1
        self.retransmit_timer = None

    def start(self):
        self.logger.info("scout starting")
        self.send_prepare()

    def send_prepare(self):
        self.node.send(self.peers, Prepare(ballot_num=self.ballot_num))
        self.retransmit_timer = self.set_timer(PREPARE_RETRANSMIT, self.send_prepare)

    def update_accepted(self, accepted_proposals):
        acc = self.accepted_proposals
        for slot, (ballot_num, proposal) in accepted_proposals.items():
            if slot not in acc or acc[slot][0] < ballot_num:
                acc[slot] = (ballot_num, proposal)

    def do_Promise(self, sender, ballot_num, accepted_proposals):
        if ballot_num == self.ballot_num:
            self.logger.info("got matching promise, need %d" % self.quorum)
            self.update_accepted(accepted_proposals)
            self.acceptors.add(sender)
            if len(self.acceptors) >= self.quorum:
                accepted_proposals = dict((s, p) for s, (b, p) in self.accepted_proposals.items())
                self.node.send([self.node.address],
                    Adopted(ballot_num=ballot_num, accepted_proposals=accepted_proposals))
                self.stop()
        else:
            self.node.send([self.node.address], Preempted(slot=None, preempted_by=ballot_num))
            self.stop()
```

Leader 会为每个有活动提案的时隙创建一个 Commander 角色。像 Scout 一样，Commander 会发送或重新发送 `Accept` 消息，并等待大多数 Acceptor 的 `Accepted` 回复，或对其抢占的消息，提议被接受后，Commander 将 `Decision` 消息广播到所有节点。 它以 `Decided` 或 `Preempted` 回复领导者。

![](/cluster/markdown/img/leadercommander.png)

```py

class Commander(Role):

    def __init__(self, node, ballot_num, slot, proposal, peers):
        super(Commander, self).__init__(node)
        self.ballot_num = ballot_num
        self.slot = slot
        self.proposal = proposal
        self.acceptors = set([])
        self.peers = peers
        self.quorum = len(peers) // 2 + 1 # 多余一半同意即可

    def start(self):
        self.node.send(set(self.peers) - self.acceptors, Accept(
            slot=self.slot, ballot_num=self.ballot_num, proposal=self.proposal
        ))
        self.set_timer(ACCEPT_RETRANSMIT, self.start)

    def finished(self, ballot_num, preempted):
        if preempted:
            self.node.send([self.node.address], Preempted(slot=self.slot, preempted_by=ballot_num))
        else:
            self.node.send([self.node.address], Decided(slot=self.slot))
        self.stop()

    def do_Accepted(self, sender, slot, ballot_num):
        if slot != self.slot:
            return
        if ballot_num == self.ballot_num:
            self.acceptors.add(sender)
            if len(self.acceptors) < self.quorum:
                return
            self.node.send(self.peers, Decision(slot=self.slot, proposal=self.proposal))
            self.finished(ballot_num, False)
        else:
            self.finished(ballot_num, True)

```

顺便说，在开发过程中这里会出现一个bug。网络仿真器在一个节点的消息上引入数据包丢失，当所有的 `Decision` 消息丢失时，协议将没有办法继续。Replica 继续重新发送 `Propose` 消息，但是 Leader 会忽略它们，因为它已经对该时隙进行过提议。由于没有 Replica 知道决策，所以 Replica 的处理找不到结果。解决方案是确保始终传递本地消息，就像真实网络堆栈一样。

#### Bootstrap

在节点加入集群之前它必须确定集群的状态。Bootstrap 角色通过依次向每个对等节点发送 `Join` 消息直到接收到 `Welcome` 来处理此问题。Bootstrap 引导类的通信图如上中所示。

该实现的早期版本是赋予每个节点全部的角色集（Replica、Leader 和 Acceptor），每个角色都从“启动”阶段开始，等待 `Welcome` 消息。这样将初始化逻辑分散在了每个角色上，需要对每个角色进行单独的测试。最终设计是添加一个 Bootstrap 角色，一旦启动完成，便将其它角色添加到节点，并将初始状态传递给它们的构造函数。

```py
class Bootstrap(Role):

    def __init__(self, node, peers, execute_fn,
        replica_cls=Replica, acceptor_cls=Acceptor, leader_cls=Leader,
        commander_cls=Commander, scout_cls=Scout):
        super(Bootstrap, self).__init__(node)
        self.execute_fn = execute_fn
        self.peers = peers
        self.peers_cycle = itertools.cycle(peers)
        self.replica_cls = replica_cls
        self.acceptor_cls = acceptor_cls
        self.leader_cls = leader_cls
        self.commander_cls = commander_cls
        self.scout_cls = scout_cls

    def start(self):
        self.join()

    def join(self):
        '''依次向每个对等节点发送 join 消息'''
        self.node.send([next(self.peers_cycle)], Join())
        self.set_timer(JOIN_RETRANSMIT, self.join)

    def do_Welcome(self, sender, state, slot, decisions, leader):
        '''接收 Welcome 消息，完成启动'''
        self.acceptor_cls(self.node)
        self.replica_cls(self.node, execute_fn=self.execute_fn, peers=self.peers,
            state=state, slot=slot, decisions=decisions, leader=leader)
        self.leader_cls(self.node, peers=self.peers, commander_cls=self.commander_cls,
            scout_cls=self.scout_cls).start()
        self.stop()
```

#### Seed

在正常操作中，当一个节点加入集群时，它期望找到已经在运行的集群并且其中至少有一个节点愿意响应 `Join` 消息。 但是群集如何开始？一个选项是 Bootstrap 角色在尝试联系所有其它节点之后，确定它是集群中的第一个节点。但这有两个问题。首先，对于大型集群意味着每个 `Join` 超时都需要很长等待时间。更重要的是，在发生网络分区的情况下，新节点可能无法联系其它任何节点，也无法启动新集群。

网络分区是群集应用程序最具挑战性的失败案例。在网络分区中，所有群集成员均保持活动状态，但某些成员之间会通信失败。例如，如果一个具有柏林和台北节点的群集网络连接失败，网络将被分区。如果群集的两个部分在分区期间继续运行，则在恢复网络连接后重新加入这些部分可能会很困难。在 Multi-Paxos 中，修复后的网络将会成为两个群集，这些群集针对相同的时隙号具有不同的决策。

为避免此结果，创建新群集是用户指定的操作。集群中恰好有一个节点充当 Seed 角色，其他节点照常运行 Bootstrap 程序。Seed 等到收到来自大多数对等节点的 `Join` 消息。然后发送带有状态机初始状态和空决策集的`Welcome` 消息。接下来 Seed 角色将自行停止，并启动 Bootstrap 角色以加入新集群。

Seed 角色模拟了 Bootstrap/Replica 角色交互的 `Join`/`Welcome` 部分，因此其通讯图与 Replica 角色相同。

```py

class Seed(Role):

    def __init__(self, node, initial_state, execute_fn, peers, bootstrap_cls=Bootstrap):
        super(Seed, self).__init__(node)
        self.initial_state = initial_state
        self.execute_fn = execute_fn
        self.peers = peers
        self.bootstrap_cls = bootstrap_cls
        self.seen_peers = set([])
        self.exit_timer = None

    def do_Join(self, sender):
        self.seen_peers.add(sender)
        if len(self.seen_peers) <= len(self.peers) / 2:
            return

        # cluster is ready - welcome everyone
        self.node.send(self.seen_peers, Welcome(
            state=self.initial_state, slot=1, decisions={}, leader=None
        ))

        # stick around for long enough that we don't hear any new JOINs from
        # the newly formed cluster
        if self.exit_timer:
            self.exit_timer.cancel()
        self.exit_timer = self.set_timer(JOIN_RETRANSMIT * 2, self.finish)

    def finish(self):
        bs = self.bootstrap_cls(self.node, peers=self.peers, execute_fn=self.execute_fn)
        bs.start()
        self.stop()
```

### Requester

Requester 角色管理对分布式状态机的请求。角色类仅向本地 Replica 发送 `Invoke` 消息，直到它收到 `Invoked` 响应。有关该角色的通信图，请参见上面的“Replica”部分。

```py
class Requester(Role):

    client_ids = itertools.count(start=10000)

    def __init__(self, node, n, callback):
        super(Requester, self).__init__(node)
        self.client_id = next(self.client_ids)
        self.n = n
        self.output = None
        self.callback = callback

    def start(self):
        self.node.send([self.node.address], Invoke(caller=self.node.address,
            client_id=self.client_id, input_value=self.n))
        self.invoke_timer = self.set_timer(INVOKE_RETRANSMIT, self.start)

    def do_Invoked(self, sender, client_id, output):
        if client_id != self.client_id:
            return
        self.logger.debug("received output %r" % (output, ))
        self.invoke_timer.cancel()
        self.callback(output)
        self.stop()
```

### 总结

概括地说，集群的角色包括：

- Acceptor——做出承诺并接受提议
- Replica——管理分布式状态机：提交提议，提交决策，响应请求者
- Leader——领导 Multi-Paxos 算法的轮次
- Scout——为 Leader 执行 Multi-Paxos 算法的 `Prepare`/`Promise` 部分
- Commander——为 Leader 执行 Multi-Paxos 算法的 `Accept`/`Accepted` 部分
- Bootstrap——将新节点引入现有集群
- Seed——创建一个新集群
- Requester——请求分布式状态机操作

使 Cluster 运行还有一个条件：网络中的所有节点可以通信。

## 网络

任何网络协议都需要具备发送和接收消息以及将来拥有调用函数方法的能力。

`Network` 类提供了具有这些功能的简单模拟网络，还模拟了数据包丢失和消息传播延迟。

计时器使用 Python 的 `heapq` 模块处理，可有效选择下一个事件。设置计时器会将 `Timer` 对象放到堆上。由于从堆中删除项效率很低，因此取消的计时器会保留在原处，但标记为取消。

消息传输使用计时器功能随机模拟的延迟来安排在每个节点上延迟消息的传递。我们再次使用 `functools.partial` 来设置一个对目标节点带有适当参数的 `receive`方法的未来调用。

运行模拟网络仅涉及从堆中弹出计时器，并且如果尚未取消计时器并且目标节点仍处于活动状态，则执行它们。

```py

class Timer(object):
    '''计时器类'''

    def __init__(self, expires, address, callback):
        self.expires = expires
        self.address = address
        self.callback = callback
        self.cancelled = False

    # Python3中不再支持__cmp__
    #def __cmp__(self, other):
    #    return cmp(self.expires, other.expires)

    def __eq__(self, other):
        return self.expires == other.expires

    def __lt__(self, other):
        return self.expires < other.expires

    def cancel(self):
        self.cancelled = True

class Network(object):
    PROP_DELAY = 0.03 # 延迟
    PROP_JITTER = 0.02 # 抖动
    DROP_PROB = 0.05 # 丢包概率

    def __init__(self, seed):
        self.nodes = {}
        self.rnd = random.Random(seed)
        self.timers = []
        self.now = 1000.0

    def new_node(self, address=None):
        node = Node(self, address=address)
        self.nodes[node.address] = node
        return node

    def run(self):
        while self.timers:
            next_timer = self.timers[0]
            if next_timer.expires > self.now:
                self.now = next_timer.expires
            heapq.heappop(self.timers)
            if next_timer.cancelled:
                continue
            if not next_timer.address or next_timer.address in self.nodes:
                next_timer.callback()

    def stop(self):
        self.timers = []

    def set_timer(self, address, seconds, callback):
        timer = Timer(self.now + seconds, address, callback)
        heapq.heappush(self.timers, timer) # 将计时器放到堆上
        return timer

    def send(self, sender, destination, message):
        sender.logger.debug("sending %s to %s", message, destination)
        # 通过为每个 dest 创建一个包含深度复制的消息的闭包来避免别名
        def sendto(dest, message):
            if dest == sender.address:
                # 发送给自己的消息不考虑丢包
                self.set_timer(sender.address, 0, lambda: sender.receive(sender.address, message))
            elif self.rnd.uniform(0, 1.0) > self.DROP_PROB:
                # 发送给其它节点，不发生丢包才发送成功
                # 通过抖动生成一个延迟时间
                delay = self.PROP_DELAY + self.rnd.uniform(-self.PROP_JITTER, self.PROP_JITTER)
                self.set_timer(dest, delay, functools.partial(self.nodes[dest].receive,
                    sender.address, message))
        for dest in (d for d in destination if d in self.nodes):
            sendto(dest, copy.deepcopy(message))
```

尽管此实现中未体现，但是组件模型允许我们替换为真实的网络实现，并在真实网络中的实际服务器之间进行通信，而无需更改其它组件。我们可以使用模拟网络进行测试和调试，并在实际网络硬件下的生产环境上使用该库。

## 调试支持

在开发像本项目一样的复杂系统时，bug 会在细节中产生，像一个简单的 `NameError`，并在几分钟的（模拟）协议操作后变为故障导致失败。查找这样的错误需要从错误明显的地方开始进行反向工作。交互式调试器在这里是无用的，因为它们只能前进。

Cluster 中最重要的调试特性是确定性模拟器。与真实的网络不同，它在每次运行时的行为方式完全相同，因为随机数生成器的种子相同。这意味着我们可以向代码中添加额外的调试检查或输出，然后重新运行模拟，以便更详细地查看相同的故障。

当然，大部分细节都在群集中节点交换的消息中，因此这些消息将自动完整记录。包括角色类发送或接收的消息的日志通过 `SimTimeLogger` 类记录，并包含注入的模拟时间戳。

```py
class SimTimeLogger(logging.LoggerAdapter):

    def process(self, msg, kwargs):
        return "T=%.3f %s" % (self.extra['network'].now, msg), kwargs

    def getChild(self, name):
        return self.__class__(self.logger.getChild(name),
                              {'network': self.extra['network']})
```

诸如此类的弹性协议在触发 bug 后通常可以运行很长时间。例如，在开发期间，数据混叠错误导致所有 Replica 共享同一 `decisions` 字典。这意味着一旦在一个节点上做了决定，其他所有节点都将其视为已决定。即使存在这个严重的错误，集群在死锁之前也可以为多个事务产生正确的结果。

断言是及早发现此类错误的重要工具。断言应包括算法设计中的所有不变量，当代码未如我们预期的那样工作时，断言我们的期望值是查看代码在什么地方出错的好办法。

```py
    assert not self.decisions.get(self.slot, None), \
            "next slot to commit is already decided"
    if slot in self.decisions:
        assert self.decisions[slot] == proposal, \
            "slot %d already decided with %r!" % (slot, self.decisions[slot])
```

在阅读代码时识别我们所做的正确假设是调试技术的一部分。在 `Replica.do_Decision` 的代码中的问题是将忽略下一个时隙提交的 `Decision`，因为它已经在 `self.decisions` 中。违反的基本假设是要提交的下一个时隙尚未进行决策。在 `do_Decision` 的开头对此断言能鉴别错误并迅速修复。同样，其他 bug 也会导致在同一时隙确定不同提议的情况，这是一个严重的错误。

在协议的开发过程中添加了许多其他断言，但是出于空间的考虑，仅保留了一部分。

### 测试

在过去的十年中，没有测试的编码就像没有安全带的驾驶一样疯狂。没有测试的代码可能是不正确的，并且在无法查看其行为是否已更改的情况下修改代码是极其冒险的。

当代码被组织好拥有很高的可测试性时，测试是最有效的。在这方面有一些活跃的思想流派，我们采用的方法是将代码分成可以对其进行单独测试的小的连接单元。这与角色模型非常吻合，在角色模型中，每个角色都有特定的用途，并且可以与其他角色隔离运行，是一个紧凑的，自给自足的类。

集群的编写是为了最大程度地实现这种隔离：除了创建新角色之外角色之间的所有通信都是通过消息进行的。在大多数情况下，可以通过向角色发送消息并观察其响应来测试角色。

#### 单元测试

Cluster 的单元测试简单而短小：

```py
class Tests(utils.ComponentTestCase):
    def test_propose_active(self):
        """A PROPOSE received while active spawns a commander."""
        self.activate_leader()
        self.node.fake_message(Propose(slot=10, proposal=PROPOSAL1))
        self.assertCommanderStarted(Ballot(0, 'F999'), 10, PROPOSAL1)
```

此方法测试单个单元（`Leader` 类）的单个行为（Commander 生成）。它遵循众所周知的“安排，行动，断言”模式：设置活动的 Leader，向其发送消息，然后检查结果。

#### 依赖注入

我们使用一种称为“依赖注入”的技术来处理新角色的创建。每个向网络添加其它角色的角色类都将一个类对象列表作为构造函数参数，默认为实际的类。例如，`Leader` 的构造函数如下所示：

```py
class Leader(Role):
    def __init__(self, node, peers, commander_cls=Commander, scout_cls=Scout):
        super(Leader, self).__init__(node)
        self.ballot_num = Ballot(0, node.address)
        self.active = False
        self.proposals = {}
        self.commander_cls = commander_cls
        self.scout_cls = scout_cls
        self.scouting = False
        self.peers = peers
```

`spawn_scout` 方法（以及类似的 `spawn_commander`）使用 `self.scout_cls` 创建新的角色对象：

```py
class Leader(Role):
    def spawn_scout(self):
        assert not self.scouting
        self.scouting = True
        self.scout_cls(self.node, self.ballot_num, self.peers).start()
```

这项技术的神奇之处在于，在测试中可以为 `Leader` 类提供伪造类，从而与 `Scout` 和 `Commander` 分开进行测试。

#### 接口正确性

关注小型单元的一个问题是它不测试单元之间的接口。例如，用于 Acceptor 角色的单元测试将验证 `Promise` 消息的 `accepted` 属性的格式，而用于 Scout 角色的单元测试将为该属性提供格式正确的值。但是两项测试均未检查这些格式是否匹配。

解决此问题的一种方法是使接口自增强。在 Cluster 项目中，使用命名元组和关键字参数可以避免对消息属性的分歧。因为角色类之间的交互都是通过消息进行的，所以这会涵盖接口的很大一部分。

对于诸如 `accepted_proposals` 格式之类的特定问题，可以使用同一个函数（在本案例为 `verifyPromiseAccepted`）来验证真实数据和测试数据。对 Acceptor 的测试使用此方法来验证每个返回的 `Promise`，而对 Scout的测试使用它来验证每个伪造的 `Promise`。

#### 集成测试

针对接口问题和设计错误的最后一道防线是集成测试。集成测试将多个单元组装在一起，并测试它们的组合效果。在我们的案例中，这意味着建立一个由多个节点组成的网络，向其中注入一些请求，并验证结果。如果存在单元测试中未发现的接口问题，则会导致集成测试迅速失败。

因为该协议旨在妥善处理节点故障，所以我们还测试了一些故障场景，包括活跃的 Leader 时机不对引发的故障。

集成测试比单元测试更难编写，因为它们的隔离度较低。对于 Cluster 项目而言，这在测试失败的 Leader 时最为明显，因为任何节点都可以是活跃的 Leader。即使使用确定的网络，一条消息的更改也会改变随机数生成器的状态，因此无法预测地更改后续事件。相比对 Leader 进行硬编码，测试代码对每个 Leader 的内部状态进行挖掘，以找到认为自己是活跃的 Leader 的方式更加合适。

#### 模糊测试

测试弹性代码非常困难：它可能对自己的 bug 有一定可恢复性，因此集成测试有时无法检测到非常严重的错误，也很难想象和构造针对每种可能故障模式的测试场景。

解决此类问题的常用方法是“模糊测试”：使用随机更改的输入重复运行代码，直到出现问题为止。当发生故障时，所有调试支持都变得至关重要：如果无法重现故障，并且日志记录信息不足以查找错误，那么你将无法修复它！

我在开发过程中对集群进行了一些手动的模糊测试，但是完整的模糊测试结构超出了本项目的范围。

## 权力争夺

一个包含许多活跃的 Leader 的集群会非常混乱，Scout 向 Acceptor 发送越来越多的选票，但是没有选票被决策出来。没有活跃的 Leader 的集群会很安静，但同样无法正常工作。平衡实现以使集群几乎总是能在一个 Leader 身上达成一致非常困难。

要避免 Leader 争斗很简单：被抢占时，Leader 只是接受其新的不活跃状态。但是这很容易导致没有活跃的 Leader 的情况，因此不活跃的 Leader 将在每次收到 `Propose` 消息时尝试变得活跃。

如果整个集群不同意哪个成员是活跃的 Leader，就会有问题：不同的 Replica 将 `Propose` 消息发送给不同的 Leader，导致与 Scout 冲突。因此 Leader 选举尽快产生结果，并让所有小组成员尽快找到很重要。

Cluster通过尽快检测到 Leader 变更来处理此问题：当 Acceptor 发送  `Promise` 时，被承诺的成员很有可能将成为下一个 Leader。这里使用心跳协议检测故障。

## 后续扩展

当然，我们有很多方法可以扩展和改进此实现。

### 追赶

在“纯粹的” Multi-Paxos 中，无法接收消息的节点可能落后群集其余部分许多时隙。只要除了通过状态机状态转换之外没有办法改变分布式状态机的状态，该设计就可以起作用。为了从状态中读取，客户端请求状态转换实际上不会更改状态，仅返回希望的值。转换在集群范围内执行，确保根据提议的时隙所在的状态向所有位置返回相同的值。

即使在最佳情况下，这也会很慢，需要多次往返才能读取一个值。如果分布式对象存储对每个对象访问都发出了这样的请求，则其性能将很糟糕。但是，当节点接收到的请求滞后时，请求延迟会大大增加，因为该节点在提出成功的建议之前必须追赶上集群的其余部分。

一种简单的解决方案是实施闲话风格的协议，每个 Replica 定期与其它 Replica 联系来分享它知道的最高时隙并请求它不知道的时隙的信息。这样即使丢失了 `Decision` 消息，Replica 也能从它的对等节点之一找到决策的信息。

### 一致的内存使用

群集管理库在存在不可靠组件的情况下提供可靠性。它不应该增加自身的不可靠性。不幸的是，由于不断增加的内存使用和消息大小，群集无法长时间运行而不产生故障。

在协议定义中，Acceptor 和 Replica 构成协议的“内存”，因此它们需要记住所有内容。这些类从不知道何时会收到旧时隙的请求，可能是来自滞后的 Replica 或 Leader。为了保持正确性，自群集启动以来，它们会保留所有决策的清单。更糟糕的是，这些决策随着 `Welcome` 消息在副本之间传输，从而在长期存在的群集中使这些消息变得巨大。

解决此问题的一种技术是定期“检查”每个节点的状态，同时保留有限数量的决策信息。当节点过时以至于它们尚未将所有时隙提交到检查点时，它们必须通过离开并重新加入集群来“重置”自身。

#### 永久储存

虽然少数集群成员失败是被允许的，但一个 Acceptor “忘记”它接受或承诺的任何值也是不可接受的。

不幸的是，这恰恰是集群成员失败并重新启动时发生的情况：新初始化的 Acceptor 实例没有其前任做出的承诺记录。因为新启动的实例替代了旧实例。

有两种方法可以解决此问题。简单点的解决方案是包括将 Acceptor 状态写入磁盘并在启动时重新读取该状态。稍复杂的解决方案是从群集中删除失败的群集成员，将新成员添加到群集中。这种集群成员的动态调整称为“视图更改”。

#### 视图更改

运营工程师需要能够调整群集的大小以满足负载和可用性要求。一个简单的测试项目可能始于三个节点的最小集群，其中任何一个节点都可能失败而不会造成影响。但是，当该项目“上线”时，额外的负载将需要更大的群集。

Cluster项目，像前面写的那样，如果不重启整个集群是没有办法更改集群中对等节点的集合的。理想情况下，集群将能够对其成员达成共识，就像状态机转换一样。这意味着可以通过特殊的视图更改提议来更改集群成员（视图）的集合。 但是 Paxos 算法依赖集群中成员的通用协议，因此我们必须为每个时隙定义视图。

Lamport 在“ Paxos Made Simple”的最后一段中解决了这一挑战：

*通过让执行第$i$个状态机命令后的状态指定的共识算法的 $i+\alpha$ 实例被一群服务器执行，我们可以允许领导者提前获取$\alpha$命令。(Lamport, 2001)*

这个想法是，每个 Paxos 实例（时隙）都使用$\alpha$时隙之前的视图。这样允许群集最多一次在$\alpha$个时隙上工作，因此当$\alpha$的值很小时会限制并发，而$\alpha$的值很大时会使视图的更改生效缓慢。

在此实现的早期草案中（其完整保留在git历史中！），我实现了对视图更改的支持（使用$\alpha$代替3）。这个看似简单的更改带来了很多复杂性：

- 跟踪最后$\alpha$个提交的时隙的视图，并与新节点正确共享该视图。
- 忽略没有时隙可用的提议。
- 检测故障节点。
- 正确序列化多个视图更改。
- 在 Leader 和 Replica 之间传递视图信息。

这些内容对于本书来说太多了！

## 参考文献

除了最初的 Paxos 论文和 Lamport 后续的“Paxos Made Simple”[^Simple]之外，我们的实现还添加了一些其它资源提供的扩展。角色名取自“Paxos Made Moderately Complex”[^Complex]。“Paxos Made Live”[^Live]对于快速学习尤其有用，“Paxos Made Practical”描述了视图更改（虽然不是这里描述的类型）。Liskov 的“From Viewstamped Replication to Byzantine Fault Tolerance”[^Tolerance]提供了视图更改的另一个视角。最后，一个Stack Overflow的 Discussion 有助于了解如何在系统中添加和删除成员。

[^Simple]: L. Lamport, "Paxos Made Simple," ACM SIGACT News (Distributed Computing Column) 32, 4 (Whole Number 121, December 2001) 51-58.

[^Complex]: R. Van Renesse and D. Altinbuken, "Paxos Made Moderately Complex," ACM Comp. Survey 47, 3, Article 42 (Feb. 2015) 。

[^Live]: T. Chandra, R. Griesemer, and J. Redstone, "Paxos Made Live - An Engineering Perspective," Proceedings of the twenty-sixth annual ACM symposium on Principles of distributed computing (PODC '07). ACM, New York, NY, USA, 398-407。

[^Tolerance]: B. Liskov, "From Viewstamped Replication to Byzantine Fault Tolerance," In Replication, Springer-Verlag, Berlin, Heidelberg 121-149 (2010)。







