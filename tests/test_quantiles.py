import math
import random
import unittest

from onlinestats.reference import ReferenceStats
from onlinestats.stats import Stats

PERCENTILES = (0.5, 0.9, 0.99)


def build_stats():
    return Stats(list(PERCENTILES))


class QuantileTest(unittest.TestCase):
    def test_uniform_ten_thousand_within_one_percent(self):
        """1 万个均匀样本：在线分位数与排序精确分位数相差不超过 1%。"""
        random.seed(7)
        data = [random.random() for _ in range(10_000)]
        online, reference = build_stats(), ReferenceStats()
        for value in data:
            online.add(value)
            reference.add(value)
        for p in PERCENTILES:
            estimate = online.quantile(p)
            exact = reference.quantile(p)
            self.assertLessEqual(
                abs(estimate - exact) / exact,
                0.01,
                msg=f"p={p} estimate={estimate} exact={exact}",
            )

    def test_merged_quantiles_within_one_percent(self):
        """合并两半后的分位数误差界与一次喂完相同。"""
        random.seed(11)
        data = [random.random() for _ in range(10_000)]
        reference = ReferenceStats()
        first, second = build_stats(), build_stats()
        for index, value in enumerate(data):
            reference.add(value)
            (first if index % 2 == 0 else second).add(value)
        first.merge(second)
        for p in PERCENTILES:
            estimate = first.quantile(p)
            exact = reference.quantile(p)
            self.assertLessEqual(abs(estimate - exact) / exact, 0.01)

    def test_quantile_merge_is_commutative(self):
        random.seed(13)
        data = [random.random() for _ in range(4096)]
        left_values, right_values = data[::2], data[1::2]

        ab_first, ab_second = build_stats(), build_stats()
        ba_first, ba_second = build_stats(), build_stats()
        for value in left_values:
            ab_first.add(value)
            ba_second.add(value)
        for value in right_values:
            ab_second.add(value)
            ba_first.add(value)
        ab_first.merge(ab_second)
        ba_first.merge(ba_second)

        for p in PERCENTILES:
            self.assertEqual(ab_first.quantile(p), ba_first.quantile(p))

    def test_memory_bounded(self):
        """不把全量存下来：存储量有界于 capacity * log2(n)。"""
        stats = build_stats()
        n = 200_000
        random.seed(17)
        for _ in range(n):
            stats.add(random.random())
        self.assertEqual(stats._sketch.count, n)
        bound = stats._sketch.capacity * (n.bit_length() + 1)
        self.assertLess(stats._sketch.stored(), bound)
        self.assertLess(stats._sketch.stored(), 0.1 * n)

    def test_quantile_update_is_constant_amortized(self):
        sketch = build_stats()._sketch
        for index in range(50_000):
            sketch.add(index)
        # 层的数量与每层长度都与数据量无关
        self.assertLessEqual(len(sketch._levels), (50_000).bit_length() + 1)
        for level in sketch._levels:
            self.assertLessEqual(len(level), sketch.capacity)

    def test_empty_quantile(self):
        self.assertEqual(build_stats().quantile(0.5), 0.0)


if __name__ == "__main__":
    unittest.main()
