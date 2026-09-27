"""在线统计：Welford 加权递推（均值/样本方差）+ 可合并分位数素描。只用标准库。"""

import copy
import heapq
import math


def weighted_quantile(entries, p):
    """加权分位数（中点 CDF 线性插值，与 numpy 的 type-7 在等权时一致）。

    entries: (value, weight) 可迭代；空输入返回 0.0。
    """
    if not 0.0 <= p <= 1.0:
        raise ValueError("分位数必须在 [0, 1] 内")
    points = sorted((value, weight) for value, weight in entries)
    if not points:
        return 0.0
    total = 0.0
    mids = []
    for value, weight in points:
        mids.append((total + weight / 2.0, value))
        total += weight
    if total <= 0.0:
        return 0.0
    target = p * total
    if target <= mids[0][0]:
        return mids[0][1]
    if target >= mids[-1][0]:
        return mids[-1][1]
    for index in range(1, len(mids)):
        mid, value = mids[index]
        if target <= mid:
            prev_mid, prev_value = mids[index - 1]
            fraction = (target - prev_mid) / (mid - prev_mid)
            return prev_value + fraction * (value - prev_value)
    return mids[-1][1]


class QuantileSketch:
    """分位数素描（compactor，P² 的等价在线算法）：固定容量、可合并、确定性。

    - 第 ``level`` 层是一个有序列表，每个元素代表 ``2**level`` 个原始观测；
    - 层溢出时确定性压缩（保留偶数位）并进入上一层，不保存全量数据，
      存储量有界于 ``capacity * log2(n)``，``add`` 摊还 O(1)，``merge`` O(1)；
    - 合并结果只取决于两边元素的多重集合，严格满足交换律。
    """

    def __init__(self, capacity=1024):
        if capacity < 2:
            raise ValueError("capacity 至少为 2")
        self.capacity = capacity
        self.count = 0
        self._buffer = []
        self._levels = []

    def add(self, value):
        self.count += 1
        self._buffer.append(value)
        if len(self._buffer) >= self.capacity:
            self._flush()

    def _flush(self):
        if self._buffer:
            self._buffer.sort()
            self._absorb(self._buffer, 0)
            self._buffer = []

    def _absorb(self, values, level):
        """把权重为 2**level 的有序列表合并进来，必要时逐层压缩上移。"""
        while True:
            while level >= len(self._levels):
                self._levels.append([])
            existing = self._levels[level]
            if existing:
                merged = list(heapq.merge(existing, values))
                self._levels[level] = []
            else:
                merged = values
            if len(merged) <= self.capacity:
                self._levels[level] = merged
                return
            values = merged[0::2]
            level += 1

    def quantile(self, p):
        entries = [(value, 1) for value in self._buffer]
        for level, values in enumerate(self._levels):
            weight = 1 << level
            entries.extend((value, weight) for value in values)
        return weighted_quantile(entries, p)

    def merge(self, other):
        """合并另一个素描；结果只由两边元素的多重集合决定（与顺序无关）。"""
        if other is self:
            raise ValueError("不能与自身合并")
        pooled = {}

        def collect(sketch):
            if sketch._buffer:
                pooled.setdefault(0, []).append(sorted(sketch._buffer))
            for level, values in enumerate(sketch._levels):
                if values:
                    pooled.setdefault(level, []).append(values)

        collect(self)
        collect(other)
        self._buffer = []
        self._levels = []
        for level in sorted(pooled):
            self._absorb(list(heapq.merge(*pooled[level])), level)
        self.count += other.count
        return self

    def stored(self):
        """当前实际保存的元素个数（用于验证内存有界）。"""
        return len(self._buffer) + sum(len(values) for values in self._levels)


class Stats:
    """在线均值/样本方差（加权 Welford 递推，Chan 公式合并）与可选分位数。

    quantiles: 需要的分位数（[0, 1] 内的比例），为空则不维护分位数素描。
    """

    def __init__(self, quantiles=()):
        self.count = 0
        self.weight_sum = 0.0
        self._mean = 0.0
        self._m2 = 0.0
        self._sketch = QuantileSketch() if quantiles else None

    def add(self, value, weight=1.0):
        """加入一个加权样本，权重必须为正。"""
        if not weight > 0.0 or math.isinf(weight):
            raise ValueError("权重必须为正数")
        self.count += 1
        self.weight_sum += weight
        delta = value - self._mean
        self._mean += weight * delta / self.weight_sum
        self._m2 += weight * delta * (value - self._mean)
        if self._sketch is not None:
            self._sketch.add(value)

    def mean(self):
        if self.count == 0:
            return 0.0
        return self._mean

    def variance(self):
        """样本方差：除以 (权重和 - 1)，权重和 < 2 时为 0。"""
        if self.weight_sum < 2.0:
            return 0.0
        return self._m2 / (self.weight_sum - 1.0)

    def quantile(self, p):
        if self._sketch is None:
            raise ValueError("未启用分位数统计")
        return self._sketch.quantile(p)

    def merge(self, other):
        """按样本数（权重和）加权合并，m2 用 Chan 公式。结果与一次喂完一致。"""
        if other.count == 0:
            return self
        if self.count == 0:
            self.count = other.count
            self.weight_sum = other.weight_sum
            self._mean = other._mean
            self._m2 = other._m2
            self._sketch = copy.deepcopy(other._sketch)
            return self
        if (self._sketch is None) != (other._sketch is None):
            raise ValueError("两侧分位数设置不一致，无法合并")
        total_weight = self.weight_sum + other.weight_sum
        delta = other._mean - self._mean
        self._mean = (
            self.weight_sum * self._mean + other.weight_sum * other._mean
        ) / total_weight
        self._m2 += (
            other._m2
            + delta * delta * self.weight_sum * other.weight_sum / total_weight
        )
        self.weight_sum = total_weight
        self.count += other.count
        if self._sketch is not None:
            self._sketch.merge(other._sketch)
        return self
