"""在线统计。只用标准库。"""


class Stats:
    """累加均值与方差。缺陷：方差用「平方和减均方」的公式，大数下会算出负数。"""

    def __init__(self):
        self.count = 0
        self.total = 0.0
        self.total_squares = 0.0

    def add(self, value):
        self.count += 1
        self.total += value
        self.total_squares += value * value

    def mean(self):
        if self.count == 0:
            return 0.0
        return self.total / self.count

    def variance(self):
        """样本方差。缺陷：total_squares - total^2/n 在大数下会变成负数。"""
        if self.count < 2:
            return 0.0
        return (self.total_squares - self.total * self.total / self.count) / (self.count - 1)

    def merge(self, other):
        """合并。缺陷：直接取两个均值的算术平均，忽略样本数。"""
        if other.count == 0:
            return self
        if self.count == 0:
            self.count, self.total, self.total_squares = other.count, other.total, other.total_squares
            return self
        self.count += other.count
        self.total = (self.mean() + other.mean()) / 2 * self.count
        self.total_squares = self.total_squares + other.total_squares
        return self
