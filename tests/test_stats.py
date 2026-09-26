import unittest

from onlinestats.stats import Stats


class StatsTest(unittest.TestCase):
    def test_empty_mean(self):
        self.assertEqual(Stats().mean(), 0.0)

    def test_empty_variance(self):
        self.assertEqual(Stats().variance(), 0.0)

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
