
- 原文作者：  Dustin J. Mitchell
- 项目： Cluster
- 需求：
  - Python 3.8+


此项目使用Paxos算法保简单实现了一个复制状态机。

目标：

每个程序员都应该知道如何在网络上达成共识。
每个程序员都应该知道网络协议是如何实现、测试和调试的。

对原项目的优化：

1. Welcome消息添加leader信息，这样新加入的节点能直接获取节点信息。

2. leader 接收 Propose 消息发现冲突后会返回给发起者一个 Conflict 消息。
。