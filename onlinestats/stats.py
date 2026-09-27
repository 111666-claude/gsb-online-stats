"""在线统计。只用标准库。

- 均值/方差：加权 Welford 递推，合并用 Chan 公式（权重当作样本数）。
- 分位数：确定性分层压实素描（compactor sketch），O(1) 内存、
  更新 O(1) 摊还、合并 O(1) 且满足交换律。
"""

import math


class _Compactor:
    """分层压实素描：每层容量固定，满了就排序后两两压实并向上晋升。

    压实偏移由压实内容的哈希决定（与历史无关），合并前会排序，
    因此 merge(a, b) 与 merge(b, a) 结果逐位相同。
    """

    def __init__(self, capacity=1024):
        self._capacity = capacity
        self._levels = [[]]
        self.weight = 0.0

    def add(self, value, weight=1.0):
        self._levels[0].append((value, weight))
        self.weight += weight
        self._compact()

    def merge(self, other):
        while len(self._levels) < len(other._levels):
            self._levels.append([])
        for level, items in enumerate(other._levels):
            self._levels[level].extend(items)
        self.weight += other.weight
        self._compact()

    def _compact(self):
        level = 0
        while level < len(self._levels):
            items = self._levels[level]
            if len(items) <= self._capacity:
                level += 1
                continue
            items.sort(key=lambda pair: pair[0])
            offset = hash(tuple(items)) & 1
            survivors = items[:offset]
            if level + 1 == len(self._levels):
                self._levels.append([])
            promoted = self._levels[level + 1]
            index = offset
            pair = 0
            while index + 1 < len(items):
                first, second = items[index], items[index + 1]
                kept = first if pair & 1 == 0 else second
                promoted.append((kept[0], first[1] + second[1]))
                index += 2
                pair += 1
            if index < len(items):
                survivors.append(items[index])
            self._levels[level] = survivors
            level += 1

    def stored_items(self):
        return sum(len(items) for items in self._levels)

    def quantile(self, probability):
        points = sorted(pair for items in self._levels for pair in items)
        if not points:
            return 0.0
        target = probability * self.weight
        cumulative = 0.0
        for value, weight in points:
            cumulative += weight
            if cumulative >= target:
                return value
        return points[-1][0]


class Stats:
    """在线均值/样本方差（加权 Welford）+ 可选的在线分位数。"""

    def __init__(self, quantiles=()):
        self.count = 0
        self.weight = 0.0
        self._mean = 0.0
        self._m2 = 0.0
        self._sketch = _Compactor() if quantiles else None

    def add(self, value, weight=1.0):
        if not math.isfinite(weight) or weight <= 0.0:
            raise ValueError("权重必须为正数，得到 %r" % (weight,))
        self.count += 1
        self.weight += weight
        delta = value - self._mean
        self._mean += weight * delta / self.weight
        self._m2 += weight * delta * (value - self._mean)
        if self._sketch is not None:
            self._sketch.add(value, weight)

    def mean(self):
        if self.count == 0:
            return 0.0
        return self._mean

    def variance(self):
        """样本方差：M2 / (权重和 - 1)；权重和不足 2 时为 0。"""
        if self.weight <= 1.0:
            return 0.0
        return self._m2 / (self.weight - 1.0)

    def quantile(self, probability):
        if self._sketch is None:
            raise ValueError("未配置分位数：请用 Stats(quantiles=[...]) 创建")
        return self._sketch.quantile(probability)

    def merge(self, other):
        """Chan 公式合并均值/M2；分位数素描一并合并。"""
        if (self._sketch is None) != (other._sketch is None):
            raise ValueError("合并双方的分位数配置不一致")
        if other.count == 0:
            return self
        if self.count == 0:
            self.count = other.count
            self.weight = other.weight
            self._mean = other._mean
            self._m2 = other._m2
            if self._sketch is not None:
                self._sketch.merge(other._sketch)
            return self
        total_weight = self.weight + other.weight
        delta = other._mean - self._mean
        self._mean += delta * other.weight / total_weight
        self._m2 += other._m2 + delta * delta * self.weight * other.weight / total_weight
        self.weight = total_weight
        self.count += other.count
        if self._sketch is not None:
            self._sketch.merge(other._sketch)
        return self
