
import random

import flow

################
## 启发式算法 ##
################

################################################################
## 启发式算法从给定的候选集合中返回一个候选项。启发式方法也会
## 访问问题数据以便计算哪一个候选对象更好。

def heur_hillclimbing(data, candidates):
    # 返回列表中的最好候选项
    scores = [(flow.makespan(data, perm), perm) for perm in candidates]
    return sorted(scores)[0][1]

def heur_random(data, candidates):
    # 返回一个随机候选项
    return random.choice(candidates)

def heur_random_hillclimbing(data, candidates):
    # 返回一个概率与其等级成比例的候选项
    scores = [(flow.makespan(data, perm), perm) for perm in candidates]
    i = 0
    while (random.random() < 0.5) and (i < len(scores) -1):
        i += 1
    return sorted(scores)[i][1]