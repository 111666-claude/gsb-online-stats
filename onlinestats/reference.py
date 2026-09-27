"""参考实现：存全量、两遍算法、排序取分位数。仅用于测试对照。"""

import math


class ReferenceStats:
    """把样本全部存下来，用定义直接算，作为在线实现的基准。"""

    def __init__(self):
        self.samples = []

    def add(self, value, weight=1.0):
        self.samples.append((value, weight))

    @property
    def count(self):
        return len(self.samples)

    @property
    def weight(self):
        return math.fsum(weight for _, weight in self.samples)

    def mean(self):
        if not self.samples:
            return 0.0
        return math.fsum(value * weight for value, weight in self.samples) / self.weight

    def variance(self):
        """两遍样本方差：先算均值，再累计加权离差平方，除以权重和 - 1。"""
        total_weight = self.weight
        if total_weight <= 1.0:
            return 0.0
        mean = self.mean()
        return math.fsum(w * (v - mean) ** 2 for v, w in self.samples) / (total_weight - 1.0)

    def quantile(self, probability):
        """排序后取累计权重达到 p * 总权重的最小值（与在线素描同口径）。"""
        if not self.samples:
            return 0.0
        points = sorted(self.samples)
        target = probability * self.weight
        cumulative = 0.0
        for value, weight in points:
            cumulative += weight
            if cumulative >= target:
                return value
        return points[-1][0]
