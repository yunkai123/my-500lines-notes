import random
from itertools import combinations, permutations

import flow

##############################
##      邻域生成器           ##
##############################

def neighbours_random(data, perm, num=1):
    # 返回 <num> 个随机作业排列，包括当前的
    candidates = [perm]
    for i in range(num):
        candidate = perm[:]
        random.shuffle(candidate)
        candidates.append(candidate)
    return candidates

def neighbours_swap(data, perm):
    # 返回与交换每对作业相对应的排列
    candidates = [perm]
    for (i, j) in combinations(range(len(perm)), 2):
        candidate = perm[:]
        candidate[i], candidate[j] = candidate[j], candidate[i]
        candidates.append(candidate)
    return candidates

def neighbours_LNS(data, perm, size=2):
    # 返回大型邻域搜索的结果
    candidates = [perm]

    # 限制邻域的数量防止作业太多 
    neighbourhoods = list(combinations(range(len(perm)), size))
    random.shuffle(neighbourhoods)

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

    return candidates

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

    # 获取前 <size> 个空闲的作业
    subset = [job_ind for (idle, job_ind) in reversed(sorted(results))][:size]

    # 列举空闲作业的排列
    for ordering in permutations(subset):
        candidate = perm[:]
        for i in range(len(ordering)):
            candidate[subset[i]] = perm[ordering[i]]
        candidates.append(candidate)

    return candidates
         
