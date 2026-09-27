import contextlib
import io
import json
import unittest

from onlinestats import cli


def run_cli(*argv):
    stdout, stderr = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        code = cli.main(list(argv))
    return code, stdout.getvalue(), stderr.getvalue()


class CliTest(unittest.TestCase):
    def test_default_output_format_unchanged(self):
        code, output, _ = run_cli("--values", "1,2,3")
        self.assertEqual(code, 0)
        payload = json.loads(output)
        self.assertEqual(set(payload), {"count", "mean", "variance"})
        self.assertEqual(payload, {"count": 3, "mean": 2.0, "variance": 1.0})

    def test_large_numbers(self):
        code, output, _ = run_cli("--values", "100000001,100000002,100000003")
        self.assertEqual(json.loads(output)["variance"], 1.0)

    def test_merge_mean_25_75(self):
        code, output, _ = run_cli("--values", "1,1,1,100", "--merge")
        self.assertEqual(code, 0)
        payload = json.loads(output)
        self.assertEqual(payload["mean"], 25.75)

    def test_merge_matches_single_pass(self):
        values = "1,1,1,100"
        _, merged, _ = run_cli("--values", values, "--merge")
        _, direct, _ = run_cli("--values", values)
        self.assertEqual(json.loads(merged), json.loads(direct))

    def test_empty_input(self):
        code, output, _ = run_cli("--values", "")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(output), {"count": 0, "mean": 0.0, "variance": 0.0})

    def test_weights(self):
        code, output, _ = run_cli("--values", "1:2,3")
        self.assertEqual(code, 0)
        payload = json.loads(output)
        self.assertEqual(payload["count"], 2)
        self.assertAlmostEqual(payload["mean"], 5 / 3)
        self.assertAlmostEqual(payload["variance"], 4 / 3)

    def test_default_weight_is_one(self):
        _, with_colon, _ = run_cli("--values", "2:1,4:1")
        _, without_colon, _ = run_cli("--values", "2,4")
        self.assertEqual(json.loads(with_colon), json.loads(without_colon))

    def test_fractional_weight(self):
        code, output, _ = run_cli("--values", "0:0.5,10:0.5")
        payload = json.loads(output)
        self.assertAlmostEqual(payload["mean"], 5.0)

    def test_invalid_weight_reports_index(self):
        cases = (
            ("1,2:0,3", "第 2 个"),
            ("1:-3", "第 1 个"),
            ("1:abc", "第 1 个"),
            ("1,2,3:-0.1", "第 3 个"),
        )
        for values, needle in cases:
            with self.subTest(values=values):
                code, _, stderr = run_cli("--values", values)
                self.assertEqual(code, 2)
                self.assertIn(needle, stderr)

    def test_invalid_value_reports_index(self):
        code, _, stderr = run_cli("--values", "1,oops,3")
        self.assertEqual(code, 2)
        self.assertIn("第 2 个", stderr)

    def test_quantiles(self):
        values = ",".join(str(value) for value in range(1, 102))
        code, output, _ = run_cli("--values", values, "--quantiles", "50,90,99")
        self.assertEqual(code, 0)
        payload = json.loads(output)
        self.assertEqual(set(payload["quantiles"]), {"50", "90", "99"})
        self.assertAlmostEqual(payload["quantiles"]["50"], 51.0)
        self.assertAlmostEqual(payload["quantiles"]["90"], 91.4)
        self.assertAlmostEqual(payload["quantiles"]["99"], 100.49)

    def test_quantiles_with_merge(self):
        values = ",".join(str(value) for value in range(1, 1001))
        _, merged, _ = run_cli("--values", values, "--quantiles", "50", "--merge")
        _, direct, _ = run_cli("--values", values, "--quantiles", "50")
        self.assertAlmostEqual(
            json.loads(merged)["quantiles"]["50"],
            json.loads(direct)["quantiles"]["50"],
            places=3,
        )

    def test_invalid_quantile(self):
        code, _, stderr = run_cli("--values", "1,2,3", "--quantiles", "110")
        self.assertEqual(code, 2)
        self.assertIn("分位数", stderr)


if __name__ == "__main__":
    unittest.main()
