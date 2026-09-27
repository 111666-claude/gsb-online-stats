import math
import random
import unittest

from onlinestats.reference import ReferenceStats
from onlinestats.stats import Stats

PROBABILITIES = (0.5, 0.9, 0.99)


def make_stats(samples, quantiles=PROBABILITIES):
    stats = Stats(quantiles=quantiles)
    for sample in samples:
        if isinstance(sample, tuple):
            stats.add(*sample)
        else:
            stats.add(sample)
    return stats


def split_merge(samples, quantiles=PROBABILITIES):
    left = Stats(quantiles=quantiles)
    right = Stats(quantiles=quantiles)
    for index, sample in enumerate(samples):
        (left if index % 2 == 0 else right).add(*(sample if isinstance(sample, tuple) else (sample,)))
    left.merge(right)
    return left


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

    def test_merge_into_empty(self):
        left, right = Stats(), Stats()
        right.add(4)
        right.add(6)
        left.merge(right)
        self.assertEqual(left.count, 2)
        self.assertEqual(left.mean(), 5.0)

    def test_merge_with_empty_other(self):
        left = Stats()
        left.add(1)
        left.merge(Stats())
        self.assertEqual(left.count, 1)


class WelfordTest(unittest.TestCase):
    def test_large_numbers_variance(self):
        stats = Stats()
        for value in (100000001, 100000002, 100000003):
            stats.add(value)
        self.assertAlmostEqual(stats.variance(), 1.0, places=12)

    def test_huge_scale_stays_positive_and_precise(self):
        stats = Stats()
        count = 10 ** 6
        for index in range(count):
            stats.add(1e12 + index % 1000)
        variance = stats.variance()
        self.assertGreater(variance, 0.0)
        # 0..999 重复 1000 次：总体方差 (1000^2 - 1) / 12，样本方差再乘 n/(n-1)
        # 10^6 次递推的浮点积累误差约 1e-8 量级，1e-6 的门槛仍保证有效位不丢
        expected = (1000 ** 2 - 1) / 12 * count / (count - 1)
        self.assertTrue(math.isclose(variance, expected, rel_tol=1e-6))

    def test_repeated_runs_identical(self):
        first = make_stats([3.5, 1.5, 9.5, 7.5])
        second = make_stats([3.5, 1.5, 9.5, 7.5])
        self.assertEqual(first.mean(), second.mean())
        self.assertEqual(first.variance(), second.variance())


class MergeTest(unittest.TestCase):
    def test_merge_weights_by_count(self):
        merged = split_merge([1, 1, 1, 100], quantiles=())
        self.assertEqual(merged.count, 4)
        self.assertEqual(merged.mean(), 25.75)

    def test_merge_matches_single_pass(self):
        one_pass = make_stats([1, 1, 1, 100], quantiles=())
        merged = split_merge([1, 1, 1, 100], quantiles=())
        self.assertEqual(merged.count, one_pass.count)
        self.assertAlmostEqual(merged.mean(), one_pass.mean())
        self.assertAlmostEqual(merged.variance(), one_pass.variance())

    def test_merge_commutative(self):
        left = make_stats([1.0, 2.0, 3.0], quantiles=())
        right = make_stats([10.0, 20.0], quantiles=())
        forward = make_stats([1.0, 2.0, 3.0], quantiles=()).merge(right)
        backward = make_stats([10.0, 20.0], quantiles=()).merge(left)
        self.assertEqual(forward.count, backward.count)
        self.assertTrue(math.isclose(forward.mean(), backward.mean(), rel_tol=1e-12))
        self.assertTrue(math.isclose(forward.variance(), backward.variance(), rel_tol=1e-12))

    def test_merge_quantile_config_mismatch_raises(self):
        with self.assertRaises(ValueError):
            Stats(quantiles=[0.5]).merge(Stats())


class WeightedTest(unittest.TestCase):
    def test_weighted_mean_and_variance(self):
        stats = Stats()
        stats.add(10, weight=2)
        stats.add(20, weight=1)
        self.assertEqual(stats.count, 2)
        self.assertAlmostEqual(stats.weight, 3.0)
        self.assertAlmostEqual(stats.mean(), 40.0 / 3.0)
        # M2 = 2*(10-40/3)^2 + 1*(20-40/3)^2 = 200/3，样本方差 = M2/(3-1)
        self.assertAlmostEqual(stats.variance(), 100.0 / 3.0)

    def test_default_weight_is_one(self):
        plain = Stats()
        weighted = Stats()
        for value in (1.5, 2.5, 3.5):
            plain.add(value)
            weighted.add(value, 1.0)
        self.assertEqual(plain.mean(), weighted.mean())
        self.assertEqual(plain.variance(), weighted.variance())

    def test_non_positive_weight_raises(self):
        stats = Stats()
        for bad in (0.0, -1.5, float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                stats.add(1.0, weight=bad)

    def test_weighted_merge_uses_weights_as_counts(self):
        left = Stats()
        left.add(0.0, weight=3.0)
        right = Stats()
        right.add(10.0, weight=1.0)
        left.merge(right)
        self.assertAlmostEqual(left.mean(), 2.5)
        # M2 = 3*(0-2.5)^2 + 1*(10-2.5)^2 = 75，样本方差 = 75/(4-1)
        self.assertAlmostEqual(left.variance(), 25.0)


class QuantileTest(unittest.TestCase):
    def test_empty_quantile_is_zero(self):
        self.assertEqual(Stats(quantiles=[0.5]).quantile(0.5), 0.0)

    def test_quantile_without_config_raises(self):
        with self.assertRaises(ValueError):
            Stats().quantile(0.5)

    def test_uniform_10k_within_one_percent(self):
        random.seed(20260928)
        data = [random.random() for _ in range(10000)]
        stats = make_stats(data)
        reference = ReferenceStats()
        for value in data:
            reference.add(value)
        for probability in PROBABILITIES:
            exact = reference.quantile(probability)
            estimate = stats.quantile(probability)
            self.assertLessEqual(abs(estimate - exact), 0.01 * abs(exact))

    def test_merged_quantiles_same_bound_and_commutative(self):
        random.seed(7)
        first_half = [random.random() for _ in range(5000)]
        second_half = [random.random() for _ in range(5000)]
        reference = ReferenceStats()
        for value in first_half + second_half:
            reference.add(value)
        forward = make_stats(first_half).merge(make_stats(second_half))
        backward = make_stats(second_half).merge(make_stats(first_half))
        for probability in PROBABILITIES:
            exact = reference.quantile(probability)
            estimate = forward.quantile(probability)
            self.assertLessEqual(abs(estimate - exact), 0.01 * abs(exact))
            self.assertEqual(estimate, backward.quantile(probability))

    def test_memory_is_constant(self):
        stats = Stats(quantiles=PROBABILITIES)
        random.seed(3)
        for _ in range(200000):
            stats.add(random.random())
        self.assertLess(stats._sketch.stored_items(), 20000)


class ReferenceComparisonTest(unittest.TestCase):
    def test_1000_random_datasets(self):
        random.seed(105)
        for _ in range(1000):
            size = random.randint(1, 60)
            base = 10.0 ** random.randint(0, 9)
            weighted = random.random() < 0.5
            samples = []
            for _ in range(size):
                value = base + random.uniform(-1, 1) * base
                samples.append((value, random.uniform(0.1, 10.0)) if weighted else value)
            stats = make_stats(samples)
            merged = split_merge(samples)
            reference = ReferenceStats()
            for sample in samples:
                reference.add(*(sample if isinstance(sample, tuple) else (sample,)))
            self.assertEqual(stats.count, reference.count)
            self.assertTrue(math.isclose(stats.mean(), reference.mean(),
                                         rel_tol=1e-9, abs_tol=1e-12))
            self.assertTrue(math.isclose(stats.variance(), reference.variance(),
                                         rel_tol=1e-9, abs_tol=1e-12))
            for candidate in (merged,):
                self.assertEqual(candidate.count, reference.count)
                self.assertTrue(math.isclose(candidate.mean(), reference.mean(),
                                             rel_tol=1e-9, abs_tol=1e-12))
                self.assertTrue(math.isclose(candidate.variance(), reference.variance(),
                                             rel_tol=1e-9, abs_tol=1e-12))
            values = [s[0] if isinstance(s, tuple) else s for s in samples]
            spread = max(values) - min(values)
            for probability in PROBABILITIES:
                exact = reference.quantile(probability)
                self.assertLessEqual(abs(stats.quantile(probability) - exact),
                                     0.01 * spread + 1e-12)
                self.assertLessEqual(abs(merged.quantile(probability) - exact),
                                     0.01 * spread + 1e-12)

    def test_large_random_datasets_with_compaction(self):
        random.seed(99)
        for _ in range(30):
            size = 20000
            data = [random.uniform(1.0, 100.0) for _ in range(size)]
            stats = make_stats(data)
            merged = split_merge(data)
            reference = ReferenceStats()
            for value in data:
                reference.add(value)
            self.assertTrue(math.isclose(stats.mean(), reference.mean(), rel_tol=1e-9))
            self.assertTrue(math.isclose(stats.variance(), reference.variance(), rel_tol=1e-9))
            self.assertTrue(math.isclose(merged.mean(), reference.mean(), rel_tol=1e-9))
            self.assertTrue(math.isclose(merged.variance(), reference.variance(), rel_tol=1e-9))
            spread = max(data) - min(data)
            for probability in PROBABILITIES:
                exact = reference.quantile(probability)
                self.assertLessEqual(abs(stats.quantile(probability) - exact), 0.01 * spread)
                self.assertLessEqual(abs(merged.quantile(probability) - exact), 0.01 * spread)


if __name__ == "__main__":
    unittest.main()
