import math
import random
import unittest

from onlinestats.stats import Stats


def rel_close(actual, expected, rel_tol=1e-9):
    """相对误差 < 1e-9；期望值接近 0 时退化为绝对误差比较。"""
    return math.isclose(actual, expected, rel_tol=rel_tol, abs_tol=1e-12)


class StatsTest(unittest.TestCase):
    def test_empty_mean(self):
        self.assertEqual(Stats().mean(), 0.0)

    def test_empty_variance(self):
        self.assertEqual(Stats().variance(), 0.0)

    def test_empty_count(self):
        self.assertEqual(Stats().count, 0)

    def test_mean(self):
        stats = Stats()
        for value in (1, 2, 3):
            stats.add(value)
        self.assertEqual(stats.count, 3)
        self.assertEqual(stats.mean(), 2.0)

    def test_variance_small_numbers(self):
        stats = Stats()
        for value in (1, 2, 3):
            stats.add(value)
        self.assertAlmostEqual(stats.variance(), 1.0)

    def test_single_value_variance(self):
        stats = Stats()
        stats.add(5)
        self.assertEqual(stats.variance(), 0.0)

    def test_large_numbers_variance_is_one(self):
        """100000001..3 在旧的平方和公式下相消成 0，Welford 必须给 1.0。"""
        stats = Stats()
        for value in (100000001, 100000002, 100000003):
            stats.add(value)
        self.assertEqual(stats.mean(), 100000002.0)
        self.assertEqual(stats.variance(), 1.0)

    def test_large_scale_million_points(self):
        """量级 1e12、个数 1e6：方差为正、不丢有效位。"""
        stats = Stats()
        for index in range(1_000_000):
            stats.add(1e12 + (index % 1000))
        expected = (1000 ** 2 - 1) / 12
        self.assertGreater(stats.variance(), 0.0)
        self.assertLess(abs(stats.variance() - expected) / expected, 1e-6)
        self.assertLess(abs(stats.mean() - (1e12 + 499.5)) / stats.mean(), 1e-12)

    def test_merge_into_empty(self):
        left, right = Stats(), Stats()
        right.add(4)
        right.add(6)
        left.merge(right)
        self.assertEqual(left.count, 2)
        self.assertEqual(left.mean(), 5.0)
        self.assertEqual(left.variance(), 2.0)

    def test_merge_with_empty_other(self):
        left = Stats()
        left.add(1)
        left.merge(Stats())
        self.assertEqual(left.count, 1)

    def test_merge_weighted_mean(self):
        """1,1,1,100 按奇偶两半合并，均值必须是 25.75。"""
        left, right = Stats(), Stats()
        for index, value in enumerate((1, 1, 1, 100)):
            (left if index % 2 == 0 else right).add(value)
        left.merge(right)
        self.assertEqual(left.count, 4)
        self.assertEqual(left.mean(), 25.75)

    def test_merge_equals_single_pass(self):
        """merge(a,b) 与一次喂完的 count/mean/variance 相对误差 < 1e-9。"""
        random.seed(1234)
        for _ in range(100):
            scale = random.choice((1.0, 1e6, 1e12))
            values = [scale * random.uniform(1.0, 1000.0)
                      for _ in range(random.randint(2, 500))]
            weights = [random.uniform(0.1, 10.0) for _ in values]
            cut = random.randrange(1, len(values))

            whole = Stats()
            left, right = Stats(), Stats()
            for index, (value, weight) in enumerate(zip(values, weights)):
                whole.add(value, weight)
                (left if index < cut else right).add(value, weight)
            left.merge(right)

            self.assertEqual(left.count, whole.count)
            self.assertTrue(rel_close(left.mean(), whole.mean()))
            self.assertTrue(rel_close(left.variance(), whole.variance()))

    def test_merge_commutative(self):
        random.seed(4321)
        for _ in range(50):
            values = [1e9 + 1e4 * random.random() for _ in range(200)]
            left_values, right_values = values[::2], values[1::2]

            ab = Stats()
            ba = Stats()
            for value in left_values:
                ab.add(value)
            for value in right_values:
                ba.add(value)
            other_ab, other_ba = Stats(), Stats()
            for value in right_values:
                other_ab.add(value)
            for value in left_values:
                other_ba.add(value)
            ab.merge(other_ab)
            ba.merge(other_ba)

            self.assertEqual(ab.count, ba.count)
            self.assertTrue(rel_close(ab.mean(), ba.mean()))
            self.assertTrue(rel_close(ab.variance(), ba.variance()))

    def test_weighted_samples(self):
        stats = Stats()
        stats.add(1, 2)
        stats.add(3, 1)
        # mean = 5/3，m2 = 8/3，样本方差 = (8/3)/(3-1) = 4/3
        self.assertEqual(stats.count, 2)
        self.assertAlmostEqual(stats.mean(), 5 / 3)
        self.assertAlmostEqual(stats.variance(), 4 / 3)

    def test_weight_merge_treats_weight_as_count(self):
        """权重当样本数：{1 出现 3 次, 100 出现 1 次} 与 1,1,1,100 同口径。"""
        weighted = Stats()
        weighted.add(1, 3)
        weighted.add(100, 1)
        unweighted = Stats()
        for value in (1, 1, 1, 100):
            unweighted.add(value)
        self.assertEqual(weighted.weight_sum, float(unweighted.count))
        self.assertEqual(weighted.mean(), unweighted.mean())
        self.assertEqual(weighted.variance(), unweighted.variance())

    def test_invalid_weight_raises(self):
        stats = Stats()
        for bad in (0, -1, -0.5, float("nan"), float("inf")):
            with self.subTest(weight=bad):
                with self.assertRaises(ValueError):
                    stats.add(1.0, bad)

    def test_repeatable_results(self):
        def run():
            stats = Stats()
            for value in (3, 1, 4, 1, 5, 9, 2, 6):
                stats.add(value)
            return stats.count, stats.mean(), stats.variance()
        self.assertEqual(run(), run())


if __name__ == "__main__":
    unittest.main()
