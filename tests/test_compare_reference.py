"""对照实现：1000 组随机数据，在线实现 vs 存全量两遍算法 + 排序分位数。"""

import random
import unittest

from onlinestats.reference import ReferenceStats
from onlinestats.stats import Stats

PERCENTILES = (0.5, 0.9, 0.99)
DATASET_COUNT = 1000


def rel_close(actual, expected):
    scale = max(1.0, abs(expected))
    return abs(actual - expected) <= 1e-9 * scale


class CompareReferenceTest(unittest.TestCase):
    def test_thousand_random_datasets(self):
        random.seed(20260928)
        for case in range(DATASET_COUNT):
            with self.subTest(case=case):
                # 少量大数据集触发素描压缩，其余为小数据集
                if case % 50 == 49:
                    size = random.randint(2000, 5000)
                else:
                    size = random.randint(0, 200)
                scale = random.choice((1.0, 1e6, 1e12))
                low, high = 1.0, 1000.0
                values = [random.uniform(low, high) * scale for _ in range(size)]
                weighted = case % 2 == 0
                weights = [random.uniform(0.1, 10.0) for _ in range(size)] if weighted else None

                online = Stats(list(PERCENTILES))
                reference = ReferenceStats()
                whole_online = Stats()
                whole_reference = ReferenceStats()
                for index, value in enumerate(values):
                    weight = weights[index] if weighted else 1.0
                    online.add(value, weight)
                    reference.add(value, weight)
                    whole_online.add(value, weight)
                    whole_reference.add(value, weight)

                # count/mean/variance：相对误差 < 1e-9
                self.assertEqual(online.count, reference.count)
                self.assertTrue(rel_close(online.mean(), reference.mean()))
                self.assertTrue(rel_close(online.variance(), reference.variance()))

                # 分位数（等权数据集）：< 1%（以数据极差为基准）
                if not weighted and size >= 2:
                    data_range = max(values) - min(values)
                    tolerance = 0.01 * data_range + 1e-9 * scale
                    for p in PERCENTILES:
                        self.assertLessEqual(
                            abs(online.quantile(p) - reference.quantile(p)),
                            tolerance,
                        )

                # 任意切分后合并，仍与两遍参考实现一致
                if size >= 2:
                    cut = random.randrange(1, size)
                    left, right = Stats(), Stats()
                    for index, value in enumerate(values):
                        weight = weights[index] if weighted else 1.0
                        (left if index < cut else right).add(value, weight)
                    left.merge(right)
                    self.assertEqual(left.count, reference.count)
                    self.assertTrue(rel_close(left.mean(), reference.mean()))
                    self.assertTrue(rel_close(left.variance(), reference.variance()))


if __name__ == "__main__":
    unittest.main()
