import sys, os, time, random

from functools import partial
from collections import namedtuple
from itertools import product

import neighbourhood as neigh
import heuristics as heur

##############
## Settings ##
##############
TIME_LIMIT = 300.0 # 运行求解器的时间（秒）
TIME_INCREMENT = 13.0 # 启发式测量之间的时间（秒）
DEBUG_SWITCH = True # 设为True时显示中间启发式信息
MAX_LNS_NEIGHBOURHOODS = 1000 # #LNS 中要探索的最大邻域数

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

    # 从一个随机排列开始
    perm = list(range(len(data)))
    random.shuffle(perm)

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

    while time.time() < time_limit:
        if time.time() > checkpoint:
            print(" %d %%" % percent_complete)
            percent_complete += 10
            checkpoint += time_delta

        iteration += 1

        # 启发式地选择最佳策略
        strategy = pick_strategy(STRATEGIES, strat_weights)

        old_val = res
        old_time = time.time()

        # 使用当前策略启发式的从策略邻域集中
        # 生成的候选策略中选择下一个排列
        candidates = strategy.neighbourhood(data, perm)
        perm = strategy.heuristic(data, candidates)
        res = makespan(data, perm)

        strat_improvements[strategy] += res - old_val
        strat_time_spent[strategy] += time.time() - old_time
        strat_usage[strategy] += 1

        if res < best_make:
            best_make = res
            best_perm = perm[:]

        # 每隔一段时间，调整可用策略的权重。
        # 这样，搜索可以动态地转向最近证明更有效的策略。
        if time.time() > time_last_switch + TIME_INCREMENT:

            # 将所做的改进依据时间归一化
            results = sorted([(float(strat_improvements[s]) / max(0.001, strat_time_spent[s]), s)
                            for s in STRATEGIES])

            if DEBUG_SWITCH:
                print("\n Computing another switch...")
                print("Best performer: %s (%d)" % (results[0][1].name, results[0][0]))
                print("Worst performer: %s (%d)" % (results[-1][1].name, results[-1][0]))

            # 提升成功策略的权重
            for i in range(len(STRATEGIES)):
                strat_weights[results[i][1]] += len(STRATEGIES) - i

                if results[i][0] == 0:
                    strat_weights[results[i][1]] += len(STRATEGIES)

            time_last_switch = time.time()

            if DEBUG_SWITCH:
                print(results)
                print(sorted([strat_weights[STRATEGIES[i]] for i in range(len(STRATEGIES))]))

            strat_improvements = {strategy: 0 for strategy in STRATEGIES}
            strat_time_spent = {strategy: 0 for strategy in STRATEGIES}

    print(" %d %%\n" % percent_complete)
    print("\nWent through %d iterations." % iteration)

    print("\n(usage) Strategy:")
    results = sorted([(strat_weights[STRATEGIES[i]], i)
                    for i in range(len(STRATEGIES))], reverse=True)

    for (w, i) in results:
        print("(%d) \t%s" % (strat_usage[STRATEGIES[i]], STRATEGIES[i].name))

    return (best_perm, best_make)

def parse_problem(filename, k=1):
    """分析 Taillard 问题文件的 k 个实例。

    Taillard问题文件是针对该问题设置的标准基准
    流程车间调度。他们可以在以下地址在线找到：
    http://mistic.heig-vd.ch/taillard/problemes.dir/ordonnancement.dir/ordonnancement.html
    """

    print("\nParsing...")

    with open(filename, 'r') as f:
        # 标识分隔实例的字符串
        problem_line = '/number of jobs, number of machines, initial seed, upper bound and lower bound :/'

        # 从每行删除空格和换行符
        lines = list(map(str.strip, f.readlines()))

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
        
        # 基于空格拆分每一行，并将每项转换为 int
        data = [list(map(int, line.split())) for line in lines]
    # 我们返回 zip 处理的数据来旋转行和列，使数据中的每项
    # 在任务持续时间内为特定作业
    return list(zip(*data))

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

def makespan(data, perm):
    """计算提供的解决方案的完工时间

    对于调度问题，完工时间指第一个作业开始到最后一个作业
    结束的时间，最小化完工时间就是最小化所有作业消耗的总时间
    """
    return compile_solution(data, perm)[-1][-1] + data[perm[-1]][-1]

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

def print_solution(data, perm):
    """打印计算解决方案的统计信息"""

    sol = compile_solution(data, perm)

    print("\nPermutation: %s\n" % str([i + 1 for i in perm]))
    print("Makespan: %d\n" % makespan(data, perm))

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


if __name__ == '__main__':
    if len(sys.argv) == 2:
        data = parse_problem(sys.argv[1])
    elif len(sys.argv) == 3:
        data = parse_problem(sys.argv[1], int(sys.argv[2]))
    else:
        print("\nUsage: python flow.py <Taillard problem file> [<instance number>]\n")
        sys.exit(0)
        # data = parse_problem("instances/tai20_5.txt")

    (perm, ms) = solve(data)
    print_solution(data, perm)

