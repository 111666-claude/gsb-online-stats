"""参考实现：存全量、两遍算法（均值/样本方差）+ 排序取分位数。

不参与在线路径，只供测试对照：count/mean/variance 精确到双精度，
分位数与在线素描用同一插值口径。
"""

from .stats import weighted_quantile


class ReferenceStats:
    def __init__(self):
        self.values = []
        self.weights = []

    def add(self, value, weight=1.0):
        self.values.append(value)
        self.weights.append(weight)

    def merge(self, other):
        self.values.extend(other.values)
        self.weights.extend(other.weights)
        return self

    @property
    def count(self):
        return len(self.values)

    def weight_sum(self):
        return sum(self.weights)

    def mean(self):
        total_weight = sum(self.weights)
        if total_weight <= 0.0:
            return 0.0
        return sum(v * w for v, w in zip(self.values, self.weights)) / total_weight

    def variance(self):
        """两遍算法：先算均值，再累计加权离均差平方和。"""
        total_weight = sum(self.weights)
        if total_weight < 2.0:
            return 0.0
        mean = self.mean()
        m2 = sum(w * (v - mean) ** 2 for v, w in zip(self.values, self.weights))
        return m2 / (total_weight - 1.0)

    def quantile(self, p):
        return weighted_quantile(zip(self.values, self.weights), p)
