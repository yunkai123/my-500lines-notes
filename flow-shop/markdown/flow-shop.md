# 流水车间调度器

## 原文作者

Christian Muise 博士，Christian Muise 博士是麻省理工学院 CSAIL MERS 小组研究员,他对各种主题感兴趣，包括人工智能、数据驱动项目、地图、图论和数据可视化，以及凯尔特音乐、雕刻、足球和咖啡。

## 流水车间调度器

流水车间调度问题是运筹学中最具挑战性和研究最多的问题之一。像许多具有挑战性的优化问题一样，对于实际规模的问题来说，找到最佳解决方案是不可能的。在本文中，我们考虑使用一种称为局部搜索的技术来实现流水车间调度求解器。当无法找到最佳解决方案时，局部搜索允许我们找到“还不错”的解决方案。求解器将尝试在给定的时间内找到问题的新解决方案，并返回找到的最佳解决方案。

局部搜索的思想是通过考虑可能更好的类似解决方案来启发式地改进现有的解决方案。求解器使用各种策略来（1）尝试找到类似的解决方案，（2）选择一个有希望进一步探索的解决方案。该实现用 Python 编写，没有任何外部需求。通过利用 Python 的一些鲜为人知的功能，求解器在求解过程中根据策略的工作效果动态地改变其搜索策略。

首先，我们提供了一些有关流水车间调度问题和局部搜索技术的背景资料。然后，我们将详细研究通用求解器代码以及我们使用的各种启发式和邻域选择策略。接下来，我们考虑求解器用于将所有内容联系在一起的动态策略选择。最后，我们对项目进行总结，并在实施过程中吸取了一些经验教训。

## 背景

### 流水车间调度

流水车间调度问题是一个优化问题，我们必须确定作业中各种任务的处理时间，以使完成该作业所需的总时间最小化。例如，一家汽车制造商拥有一条装配线，汽车的每个零件都是在不同的机器上按顺序完成的。不同的订单可能会有定制的要求，比如说，车身喷漆的任务会因每辆车的不同而有所不同。在我们的示例中，每辆车都是一个新的*作业（job）*，而汽车的每个零件都称为一个*任务（task）*。每个作业都有相同的任务顺序来完成。

流水车间调度的目标是最大程度减少从每个作业到完成所有任务所需的总时间。（通常，这个总时间被称为*完工时间makespan*。）这个问题有很多应用，比如优化生产设施。

每个流水车间问题都由$n$台机器和$m$个作业组成。在我们的汽车示例中，将有$n$个工作站用于该车，并且总共要制造$m$辆车。每个作业都由$n$个任务组成，我们可以假设作业的第$i$个任务必须使用机器$i$，并且需要预定的处理时间：$p（j，i）$是作业$j$的第$i$个任务的处理时间。此外，任何给定作业的任务顺序应遵循可用机器的顺序；对于给定作业，任务$i$必须在任务$i+1$开始之前完成。在我们的汽车例子中，我们不想在车架组装之前就开始油漆汽车。最后一个限制是不能在一台机器上同时处理两个任务。

因为作业中的任务顺序是预先确定的，所以流水车间调度问题的解决方案可以表示为作业的排列。在一台机器上处理的作业顺序对于每台机器来说都是相同的，并且给定一个排列，作业$j$中机器$i$的任务计划被安排为以下两种可能性中的最新一个：

1. 完成作业$j-1$中机器$i$的任务（即，同一机器上最近的任务），或

2. 完成作业$j$中机器$i-1$的任务（即同一作业上最近的任务）

因为我们选择了这两个值中的最大值，所以将为机器$i$或作业$j$创建空闲时间。我们最终想要最小化此空闲时间，因为它会使总的完工时间变大。

由于问题的形式简单，作业的任何排列都是一个有效的解，而最优解对应于某个排列。因此，我们通过改变作业的排列和测量相应的完工时间来寻找改进的解决方案。在下面的内容中，我们将一系列的工作称为*候选对象*。

让我们考虑一个包含两个作业和两台机器的简单示例。第一个作业有任务$\mathbf{A}$和$\mathbf{B}$，分别需要1分钟和2分钟才能完成。第二个作业有任务$\mathbf{C}$和$\mathbf{D}$，分别需要2分钟和1分钟才能完成。回想一下，$\mathbf{A}$必须在$\mathbf{B}$之前，而$\mathbf{C}$必须在$\mathbf{D}$之前。因为有两个工作，我们只有两个排列要考虑。如果我们在作业1之前订购作业2，则完工时间为5；另一方面，如果我们在作业2之前订购作业1，则完工时间只有4。

![](/flow-shop/markdown/img/example1.png)

![](/flow-shop/markdown/img/example2.png)

请注意，没有多余空间可以提前完成任何任务。一个好的排列的指导原则是尽量减少任何机器没有任务处理的时间。

### 局部搜索

局部搜索是在最优解太难计算时解决优化问题的一种策略。直观上，它从一个看起来很好的解决方案转移到另一个看起来更好的解决方案。我们不是把每一个可能的解决方案都看作是下一个重点关注的候选方案，而是定义了所谓的邻域：被认为与当前解决方案类似的一组解决方案。因为作业的任何排列都是一个有效的解决方案，我们可以将任何将作业洗牌的机制视为一个局部搜索过程（这实际上就是我们下面要做的）。

要正式使用局部搜索，我们必须回答几个问题：

1. 我们应该从什么解决方案开始？
2. 给定一个解决方案，我们应该考虑哪些相邻的解决方案？
3. 给定一组候选邻域，我们应该考虑移至哪一个呢？

以下三个部分依次讨论这些问题。

## 通用求解器

在本节中，我们将提供流水车间调度程序的通用框架。首先，我们要有必要的 Python 导入和求解器设置：

```py
import sys, os, time, random

from functools import partial
from collections import namedtuple
from itertools import product

import neighbourhood as neigh
import heuristics as heur

##############
## Settings ##
##############
TIME_LIMIT = 300.0 # Time (in seconds) to run the solver
TIME_INCREMENT = 13.0 # Time (in seconds) in between heuristic measurements
DEBUG_SWITCH = False # Displays intermediate heuristic info when True
MAX_LNS_NEIGHBOURHOODS = 1000 # Maximum number of neighbours to explore in LNS
```

有两个设置需要进一步解释。`TIME_INCREMENT` 设置将用作动态策略选择的一部分，`MAX_LNS_NEIGHBOURHOODS` 设置将用作邻域选择策略的一部分。 两者都在下面更详细地描述。

这些设置可以作为命令行参数显示给用户，但是在此阶段，我们将输入数据作为参数提供给程序。输入问题（来自 Taillard 基准集的问题）被假定为流水车间调度的标准格式。以下代码用作求解器文件的 `__main__` 方法，并根据输入到程序的参数数量调用相应的函数：

```py
if __name__ == '__main__':

    if len(sys.argv) == 2:
        data = parse_problem(sys.argv[1], 0)
    elif len(sys.argv) == 3:
        data = parse_problem(sys.argv[1], int(sys.argv[2]))
    else:
        print("\nUsage: python flow.py <Taillard problem file> [<instance number>]\n")
        sys.exit(0)

    (perm, ms) = solve(data)
    print_solution(data, perm)
```

我们将很快描述 Taillard 问题文件的解析。（这些文件可[在线获取](http://mistic.heig-vd.ch/taillard/problemes.dir/ordonnancement.dir/ordonnancement.html)。）

`solve` 方法希望 `data` 变量是包含每个作业的活动持续时间的整数列表。`solve` 方法首先初始化一组全局策略（如下所述）。关键是我们使用 `strat_*` 变量来维护每种策略的统计数据。这有助于在求解过程中动态选择策略。

```py
def solve(data):
    """解决一个车间调度问题实例"""

    # 我们在这里初始化策略以避免循环导入问题
    initialize_strategies()
    global STRATEGIES 

    # improvements: 该策略改善了的解决方案的数量
    strat_improvements = {strategy: 0 for strategy in STRATEGIES}
    # time_spent: 该策略花费的时间
    strat_time_spent = {strategy: 0 for strategy in STRATEGIES}
    # weights: 与策略多好对应的权重
    strat_weights = {strategy: 0 for strategy in STRATEGIES}
    # usage: 使用策略的次数
    strat_usage = {strategy: 0 for strategy in STRATEGIES}
```

流水车间调度问题的一个吸引人的特性是，每一个排列都是一个有效的解决方案，并且至少有一个具有最佳的完工时间（尽管许多可能有很长的完工时间）。谢天谢地，当从一个排列转换到另一个排列时，这允许我们放弃检查我们是否处于可行解的空间之内，一切都是可行的！

然而，要在排列空间中开始局部搜索，我们必须有一个初始排列。为了简单起见，我们通过随机调整作业列表来进行局部搜索：

```py
    # 从一个随机排列开始
    perm = list(range(len(data)))
    random.shuffle(perm)
```

接下来，我们初始化变量，这些变量允许我们跟踪到目前为止找到的最佳排列，以及提供输出的时序信息。

```py
    # 追踪最优方案
    best_make = makespan(data, perm)
    best_perm = perm
    res = best_make

    # 维护迭代的统计信息和时间信息
    iteration = 0
    time_limit = time.time() + TIME_LIMIT
    time_last_switch = time.time()

    time_delta = TIME_LIMIT / 10
    checkpoint = time.time() + time_delta
    percent_complete = 10

    print("\nSolving...")
```

由于这是一个局部搜索解决方案，只要还没达到限定的时间，我们就可以继续尝试并改进解决方案。我们提供显示求解器进度的输出，并追踪计算的迭代次数：

```py
    while time.time() < time_limit:
        if time.time() > checkpoint:
            print(" %d %%" % percent_complete)
            percent_complete += 10
            checkpoint += time_delta

        iteration += 1
```

下面我们将描述如何选择策略，但现在只需知道策略提供了邻域函数和启发式函数。前者为我们提供了下一组要考虑的候选对象，而后者则从集合中选择最佳候选对象。从这些函数中，我们得到了一个新的排列（`perm`）和一个新的完工时间结果（`res`）：

```py
        # 启发式地选择最佳策略
        strategy = pick_strategy(STRATEGIES, strat_weights)

        old_val = res
        old_time = time.time()

        # 使用当前策略启发式的从策略邻域集中
        # 生成的候选策略中选择下一个排列
        candidates = strategy.neighbourhood(data, perm)
        perm = strategy.heuristic(data, candidates)
        res = makespan(data, perm)
```

计算完工时间的代码非常简单：我们可以通过计算最终作业完成时间来从排列中计算。下面我们将看到 `compile_solution` 是如何工作的，但现在只需知道返回了一个 2D 数组，并且 `[-1][-1]` 处的元素对应于调度中最后一个作业的开始时间：

```py
def makespan(data, perm):
    """计算提供的解决方案的完工时间

    对于调度问题，完工时间指第一个作业开始到最后一个作业
    结束的时间，最小化完工时间就是最小化所有作业消耗的总时间
    """
    return compile_solution(data, perm)[-1][-1] + data[perm[-1]][-1]
```

为了帮助选择策略，我们对以下方面进行统计：（1）该策略改进了解决方案的程度；（2）该策略花费了多少时间来计算信息；（3）该策略被使用了多少次。如果我们偶然发现一个更好的解决方案，我们还将更新变量以获得最佳排列：

```py
        strat_improvements[strategy] += res - old_val
        strat_time_spent[strategy] += time.time() - old_time
        strat_usage[strategy] += 1

        if res < best_make:
            best_make = res
            best_perm = perm[:]
```

定期更新策略使用的统计数据。为了便于阅读，我们删除了相关的代码片段，并在下面详细说明了代码。作为最后一步，一旦 `while` 循环完成（即达到时间限制），我们输出一些有关求解过程的统计信息，并返回最佳排列及其完工时间：

```py
    print(" %d %%\n" % percent_complete)
    print("\nWent through %d iterations." % iteration)

    print("\n(usage) Strategy:")
    results = sorted([(strat_weights[STRATEGIES[i]], i)
                    for i in range(len(STRATEGIES))], reverse=True)

    for (w, i) in results:
        print("(%d) \t%s" % (strat_usage[STRATEGIES[i]], STRATEGIES[i].name))

    return (best_perm, best_make)
```

### 解析问题

作为解析过程的输入，我们提供了可以找到输入的文件名以及应该使用的示例编号。（每个文件包含多个实例。）

```py
def parse_problem(filename, k=1):
    """Parse the kth instance of a Taillard problem file

    The Taillard problem files are a standard benchmark set for the problem
    of flow shop scheduling. 

    print("\nParsing...")
```

我们通过读取文件并标识分隔每个问题实例的行来开始解析：

```py
    with open(filename, 'r') as f:
        # 标识分隔实例的字符串
        problem_line = '/number of jobs, number of machines, initial seed, upper bound and lower bound :/'

        # 从每行删除空格和换行符
        lines = list(map(str.strip, f.readlines()))
```

为了更容易找到正确的实例，我们假设行之间将用“/”字符分隔。这样我们就可以根据出现在每个实例顶部的公共字符串拆分文件，并且在第一行的开头添加“/”字符以使下面的字符串处理工作不管我们选择哪个实例都可以正常进行。我们还检测提供的实例号是否超出了给定文件中实例集合的范围。

```py
        # 准备第一行为以后做准备
        lines[0] = '/' + lines[0]

        # 我们还知道 / 不出现在文件中，因此可以将其用作
        # 为第k个问题实例查找正确行的分隔符
        try:
            lines = '/'.join(lines).split(problem_line)[k].split('/')[2:]
        except IndexError:
            max_instances = len('/'.join(lines).split(problem_line)) - 1
            print("\nError: Instance must be within 1 and %d\n" % max_instances)
            sys.exit(0)
```

我们直接解析数据，将每个任务的处理时间转换为整数并存储在列表中。最后，我们压缩数据以反转行和列，以便格式符合上面的求解代码所期望的内容。（数据中的每一项都应该对应于特定的作业。）

```py
        # 基于空格拆分每一行，并将每项转换为 int
        data = [list(map(int, line.split())) for line in lines]
    # 我们返回 zip 处理的数据来旋转行和列，使数据中的每项
    # 在任务持续时间内为特定作业
    return list(zip(*data))
```

### 编制解决方案

流水车间调度问题的一个解决方案包括对每个作业中的每个任务进行精确的定时。因为我们用作业的排列来隐式地表示一个解，所以我们引入 `compile_solution` 函数来将排列转换为精确的时间。作为输入，该函数接受问题的数据（给出每个任务的持续时间）和一组作业排列。

该函数首先初始化用于存储每个任务的开始时间的数据结构，然后将第一个作业的任务包含在排列中。

```py
def compile_solution(data, perm):
    """在给定作业排列的机器上编译调度"""
    num_machines = len(data[0])

    # 注意，使用 [[]]*m 是不正确的，因为它只是
    # 复制同一个列表m次（而不是创建m个不同的列表）。
    machine_times = [[] for _ in range(num_machines)]

    # 将初始作业分配给机器
    machine_times[0].append(0)
    for mach in range(1, num_machines):
        # 上一个任务完成后，开始作业中的下一个任务
        machine_times[mach].append(machine_times[mach - 1][0] +
                                    data[perm[0]][mach - 1])
```

然后，我们添加剩余作业的所有任务。作业中的第一个任务总是在上一个作业中的第一个任务完成后立即启动。对于剩余的任务，我们尽早安排作业：同一作业中前一个任务的完成时间和同一台机器上前一个任务的完成时间中的最大值。

```py
    # 分配剩余作业
    for i in range(1, len(perm)):

        # 第一个作业没有空闲时间
        job = perm[i]
        machine_times[0].append(machine_times[0][-1] + data[perm[i - 1]][0])

        # 对于其余机器，开始时间是作业中的上一个任务已完成，或
        # 当前机器完成上一个作业的任务。
        for mach in range(1, num_machines):
            machine_times[mach].append(max(machine_times[mach - 1][i] + data[perm[i]][mach - 1],
                            machine_times[mach][i - 1] + data[perm[i - 1]][mach]))
    return machine_times
```

### 打印解决方案

当求解过程完成时，程序以简洁的形式输出有关解决方案的信息。我们输出以下信息，而不是为每个作业提供每个任务的精确时间：

1. 产生最佳完工时间的工作排列
2. 计算排列的完工时间
3. 每台机器的开始时间、结束时间和空闲时间
4. 每个作业的开始时间、完成时间和空闲时间

作业或机器的开始时间对应于作业或机器上第一个任务的开始时间。同样，作业或机器的完成时间对应于作业或机器上最终任务的结束时间。空闲时间是特定作业或机器的任务之间的空闲时间。理想情况下，我们希望减少空闲时间，因为这意味着整个处理时间也将减少。

编译解决方案的代码（即计算每个任务的开始时间）已经讨论过，输出排列和完工时间非常简单：

```py
def print_solution(data, perm):
    """打印计算解决方案的统计信息"""

    sol = compile_solution(data, perm)

    print("\nPermutation: %s\n" % str([i + 1 for i in perm]))
    print("Makespan: %d\n" % makespan(data, perm))
```

接下来，我们使用 Python 中的字符串格式化功能来打印每个机器和作业的开始、结束和空闲时间表。请注意，作业的空闲时间是从作业开始到完成的时间，减去作业中每个任务的处理时间之和。我们用类似的方法计算机器的空闲时间。

```py
   row_format = "{:>15}" * 4
    print(row_format.format('Machine', 'Start Time', 'Finish Time', 'Idle Time'))
    for mach in range(len(data[0])):
        finish_time = sol[mach][-1] + data[perm[-1]][mach]
        idle_time = (finish_time - sol[mach][0]) - sum([job[mach] for job in data])
        print(row_format.format(mach + 1, sol[mach][0], finish_time, idle_time))
        
    results = []
    for i in range(len(data)):
        finish_time = sol[-1][i] + data[perm[i]][-1]
        idle_time = (finish_time - sol[0][i]) - sum([time for time in data[perm[i]]])
        results.append((perm[i] + 1, sol[0][i], finish_time, idle_time))

    print("\n")
    print(row_format.format('Job', 'Start Time', 'Finish Time', 'Idle Time'))
    for r in sorted(results):
        print(row_format.format(*r))

    print("\n\nNote: Idle time does not include initial or final wait time.\n")
```

## 邻域

局部搜索的思想是从一个解决方案本地转移到附近的其它解决方案。我们将给定解决方案的邻域称为该解决方案的其它局部解决方案。在本节中，我们详细介绍了四个潜在的邻域，复杂性从低到高。

第一个邻域产生给定数量的随机排列。这个邻域甚至没有考虑我们开始时所采用的解决方案。这里“邻域”一词扩展了事实。但是，在搜索中包含一些随机性是很好的做法，因为它可以促进搜索空间的探索。

```py
def neighbours_random(data, perm, num = 1):
    # 返回 <num> 个随机作业排列，包括当前的
    candidates = [perm]
    for i in range(num):
        candidate = perm[:]
        random.shuffle(candidate)
        candidates.append(candidate)
    return candidates
```

对于下一个邻域，我们考虑在这个排列中交换任何两个作业。通过使用 `itertools` 包中的 `combinations` 函数，我们可以轻松地遍历每对索引，并创建一个新的排列，对应于交换位于每个索引的作业。从某种意义上说，这个邻域创造的排列与我们开始时的排列非常相似。

```py
def neighbours_swap(data, perm):
    # 返回与交换每对作业相对应的排列
    candidates = [perm]
    for (i,j) in combinations(range(len(perm)), 2):
        candidate = perm[:]
        candidate[i], candidate[j] = candidate[j], candidate[i]
        candidates.append(candidate)
    return candidates
```

我们考虑的下一个邻域使用的是当前问题的特定信息。我们找到空闲时间最多的工作，并考虑尽可能地交换它们。我们接受一个值 `size`，即我们考虑的作业数：前 `size` 个空闲作业。该过程的第一步是计算排列中每个作业的空闲时间：

```py
def neighbours_idle(data, perm, size=4):
    # 返回前 <size> 个空闲作业打乱位置的排列
    candidates = [perm]

    # 计算每个作业的空闲时间
    sol = flow.compile_solution(data, perm)
    results = []

    for i in range(len(data)):
        finish_time = sol[-1][i] + data[perm[i]][-1]
        idle_time = (finish_time - sol[0][i]) - sum([t for t in data[perm[i]]])
        results.append((idle_time, i))
```

接下来，我们计算空闲时间最多的大小作业列表。

```py
    # 获取前 <size> 个空闲的作业
    subset = [job_ind for (idle, job_ind) in reversed(sorted(results))][:size]
```

最后，我们通过考虑我们确定的最空闲的工作的每一种排列来构建邻域。为了找到排列，我们使用 `itertools` 包中的排列函数。

```py
    # 列举空闲作业的排列
    for ordering in permutations(subset):
        candidate = perm[:]
        for i in range(len(ordering)):
            candidate[subset[i]] = perm[ordering[i]]
        candidates.append(candidate)

    return candidates
```

我们考虑的最后一个邻域通常被称为大型邻域搜索（LNS）。直观上，LNS 通过孤立地考虑当前排列的较小子集来工作，找到作业子集的最佳排列将为我们提供 LNS 邻域的候选项。通过对特定大小的几个（或全部）子集重复此过程，我们可以增加邻域中的候选项数量。我们通过 `MAX_LNS_NEIGHBOURHOODS` 参数限制考虑的数量，因为邻域的数量可以快速增长。LNS 计算的第一步是计算作业集的随机列表，我们将考虑使用 `itertools` 包的 `combinations` 函数交换这些作业集：

```py
def neighbours_LNS(data, perm, size=2):
    # 返回大型邻域搜索的结果
    candidates = [perm]

    # 限制邻域的数量防止作业太多 
    neighbourhoods = list(combinations(range(len(perm)), size))
    random.shuffle(neighbourhoods)
```

接下来，我们遍历这些子集，以找到每个子集中作业的最佳排列。我们在上面看到了类似的代码，用于遍历最空闲作业的所有排列。这里的关键区别在于，我们只记录子集的最佳排列，因为通过为所考虑的作业的每个子集选择一个排列可以构建更大的邻域。

```py
    for subset in neighbourhoods[:flow.MAX_LNS_NEIGHBOURHOODS]:

        # 追踪每个邻域的最佳候选项
        best_make = flow.makespan(data, perm)
        best_perm = perm

        # 列举所选邻域的每个排列
        for ordering in permutations(subset):
            candidate = perm[:]
            for i in range(len(ordering)):
                candidate[subset[i]] = perm[ordering[i]]
            res = flow.makespan(data, candidate)
            if res < best_make:
                best_make = res 
                best_perm = candidate

            # 记录最佳候选项作为更大邻域的一部分
            candidates.append(best_perm)
```

如果我们将 `size` 参数设置为等于作业数，那么将考虑每个排列并选择最佳的排列。然而，在实践中，我们需要将子集的大小限制在3或4左右；更大的值会导致 `neighbours_LNS` 函数花费过多的时间。

## 启发式

启发式方法从一组提供的候选项中返回单个候选排列。启发式算法还可以访问问题数据，以评估哪个候选对象可能是首选。

我们考虑的第一个启发式算法是 `heur_random`。这种启发式方法从列表中随机选择一个候选项，而不评估哪一个可能是首选：

```py
def heur_random(data, candidates):
    # 返回一个随机候选项
    return random.choice(candidates)
```

下一个启发式的 `heur_hillclimbing` 使用另一个极端。它不是随机选择一个候选项，而是选择具有最佳完工时间的候选对象。注意，列表 `scores` 将包含形式为 `(make,perm)` 的元组，其中 `make` 是排列 `perm` 的完工时间值。对这样的列表进行排序会将最佳完工时间的元组放在列表的开头；从这个元组返回排列。

```py
def heur_hillclimbing(data, candidates):
    # 返回列表中的最好候选项
    scores = [(flow.makespan(data, perm), perm) for perm in candidates]
    return sorted(scores)[0][1]
```

最后一个启发式方法，`heur_random_hillclimbing`，结合了上面的随机和`hillclimbing` 启发式方法。当执行局部搜索时，你可能并不总是希望随机选择一个候选对项，甚至是最好的一个。`heur_random_hillclimbing` 启发式方法通过以概率 0.5 选择最佳候选项，然后以概率 0.25 选择次优候选项，返回“相当好”的解决方案，依此类推。while 循环在每次迭代时都会掷硬币，看看它是否应该继续增加索引（限制列表的大小）。最终选择的索引对应于启发式选择的候选对象。

```py
def heur_random_hillclimbing(data, candidates):
    # 返回一个概率与其等级成比例的候选项
    scores = [(flow.makespan(data, perm), perm) for perm in candidates]
    i = 0
    while (random.random() < 0.5) and (i < len(scores) -1):
        i += 1
    return sorted(scores)[i][1]
```

因为完工时间是我们试图优化的标准，`hillclimbing` 将引导局部搜索过程，以获得更好的完工时间解决方案。引入随机性可以让我们探索邻域，而不是在每一步都盲目地寻找看起来最佳的解决方案。

## 动态策略选择

局部搜索寻找一个好的排列的核心是使用一个特定的启发式方法和邻域函数从一个解决方案跳到另一个解决方案。我们如何选择一组选项而不是另一组？在实践中，在搜索过程中切换策略往往是有回报的。我们使用的动态策略选择将在启发式方法和邻域函数的组合之间切换，以尝试动态地转向那些最有效的策略。对我们来说，策略是启发式方法和邻域函数（包括它们的参数值）的特殊配置。

首先，我们的代码构建了我们在求解过程中要考虑的策略范围。在策略初始化中，我们使用 `functools` 包中的 `partial` 函数为每个邻域部分分配参数。另外，我们构造了一个启发式函数的列表，最后使用乘积运算符将邻域和启发式函数的每一个组合相加作为一种新的策略。

```py
################
## Strategies ##
#################################################
##  策略是邻域生成器（用来计算下一组候选者）和
##  启发计算（用来选择最佳候选者）的特殊配置。

STRATEGIES = []

Strategy = namedtuple('Strategy', ['name', 'neighbourhood', 'heuristic'])

def initialize_strategies():

    global STRATEGIES

    # 定义我们要使用的邻域（和参数）
    neighbourhoods = [
        ('Random Permutation', partial(neigh.neighbours_random, num=100)),
        ('Swapped Pairs', neigh.neighbours_swap),
        ('Large Neighbourhood Search (2)', partial(neigh.neighbours_LNS, size=2)),
        ('Large Neighbourhood Search (3)', partial(neigh.neighbours_LNS, size=3)),
        ('Idle Neighbourhood (3)', partial(neigh.neighbours_idle, size=3)),
        ('Idle Neighbourhood (4)', partial(neigh.neighbours_idle, size=4)),
        ('Idle Neighbourhood (5)', partial(neigh.neighbours_idle, size=5))
    ]

    # 定义我们要使用的启发式方法
    heuristics = [
        ('Hill climbing', heur.heur_hillclimbing),
        ('Random Selection', heur.heur_random),
        ('Blased Random Selection', heur.heur_random_hillclimbing)
    ]

    # 结合每个邻域和启发式策略
    for (n, h) in product(neighbourhoods, heuristics):
        STRATEGIES.append(Strategy("%s / %s" % (n[0], h[0]), n[1], h[1]))

```

一旦策略被定义，我们不一定要在搜索过程中坚持单一的选项。相反，我们随机选择任何一种策略，但要根据策略的执行情况对选择进行加权。我们在下面描述权重，但是对于 `pick_strategy` 函数，我们只需要一个策略列表和一个相应的相对权重列表（任何数字都可以）。为了选择具有给定权重的随机策略，我们在 0 和所有权重之和之间均匀地选取一个数。随后，我们找到最低的指数$i$，以使小于$i$的指数的所有权重之和大于我们选择的随机数。这种技术，有时也被称为轮盘赌选择，会随机为我们选择一个策略，并给那些权重更高的策略提供更大的机会。

```py
def pick_strategy(strategies, weights):
    # 根据权重随机选择一个策略：轮盘赌选择
    # 我们没有完全随机地选择策略，而是偏向
    # 于选择过去表现好的策略（根据权重值）
    total = sum([weights[Strategy] for Strategy in strategies])
    pick = random.uniform(0, total)
    count = weights[strategies[0]]

    i = 0
    while pick > count:
        count += weights[strategies[i + 1]]
        i += 1

    return strategies[i]
```

剩下的就是描述在寻找解的过程中如何增加权重。这在求解器的主 while 循环中以固定的时间间隔（用 `TIME_INCREMENT` 变量定义）发生：

```py
        # 每隔一段时间，调整可用策略的权重。
        # 这样，搜索可以动态地转向最近证明更有效的策略。
        if time.time() > time_last_switch + TIME_INCREMENT:

            time_last_switch = time.time()
```

回想一下，`strat_improvements` 存储了一个策略所做的所有改进的总和，而 `strat_time_used` 存储的是上一个时间间隔内给出的策略的时间。我们将每个策略所花费的总时间所做的改进标准化，以衡量每个策略在上一个时间间隔内的执行效果。因为一个策略可能根本没有机会运行，所以我们选择少量时间作为默认值。

```py
            # 将所做的改进依据时间归一化
            results = sorted([(float(strat_improvements[s]) / max(0.001, strat_time_spent[s]), s)
                            for s in STRATEGIES])
```

现在我们已经对每个策略的执行情况进行了排名，我们在最佳策略的权重上加上$k$（假设我们有$k$个策略），下一个最佳策略加$k-1$，等等。每个策略的权重都会增加，而列表中最差的策略只会增加1。

```py
            # 提升成功策略的权重
            for i in range(len(STRATEGIES)):
                strat_weights[results[i][1]] += len(STRATEGIES) - i
```

作为一个额外的措施，我们人为地增加了所有未使用的策略。这样做是为了让我们不会完全忘记策略。虽然一种策略在开始时可能表现不佳，但在后来的搜索中，它可能会被证明是非常有用的。

```py
                # Additionally boost the unused strategies to avoid starvation
                if results[i][0] == 0:
                    strat_weights[results[i][1]] += len(STRATEGIES)
```

最后，我们输出一些关于策略排名的信息（如果设置了 DEBUG_SWITCH 标志），并在下一个时间间隔内重置 `strat_improvements` 和 `strat_time_spent` 变量。

```py
            if DEBUG_SWITCH:
                print(results)
                print(sorted([strat_weights[STRATEGIES[i]] for i in range(len(STRATEGIES))]))

            strat_improvements = {strategy: 0 for strategy in STRATEGIES}
            strat_time_spent = {strategy: 0 for strategy in STRATEGIES}
```

## 讨论

在本文中，我们看到了用相对较少的代码就可以解决复杂的流水车间调度优化问题。对于像流水车间这样的大型优化问题，很难找到最佳的解决方案。在这种情况下，我们可以使用近似技术，例如局部搜索来计算一个足够好的解。通过局部搜索，我们可以从一个解决方案转移到另一个方案，目标是找到一个质量好的解决方案。

局部搜索背后的一般思想可以应用于各种问题。我们着重于（1）从一个候选解生成一个问题的相关解的邻域，（2）建立评估和比较解决方案的方法。有了这两个组成部分，我们就可以使用局部搜索范式在最佳方案太难计算时找到有价值的解决方案。

我们没有使用单一策略来解决问题，而是看到了如何在解决过程中动态地选择一种策略来改变。这种简单而强大的技术使程序能够针对手头的问题混合和匹配部分策略，这也意味着开发人员不必手工定制策略。

































