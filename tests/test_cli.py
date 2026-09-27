import contextlib
import io
import json
import unittest

from onlinestats.cli import main


def run_cli(argv):
    stdout, stderr = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        code = main(argv)
    return code, stdout.getvalue(), stderr.getvalue()


class CliTest(unittest.TestCase):
    def test_large_numbers_variance(self):
        code, out, _ = run_cli(["--values", "100000001,100000002,100000003"])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["variance"], 1.0)

    def test_merge_mean(self):
        code, out, _ = run_cli(["--values", "1,1,1,100", "--merge"])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["mean"], 25.75)

    def test_output_shape_unchanged_without_new_flags(self):
        code, out, _ = run_cli(["--values", "1,2,3"])
        self.assertEqual(code, 0)
        self.assertEqual(sorted(json.loads(out)), ["count", "mean", "variance"])

    def test_empty_values(self):
        code, out, _ = run_cli(["--values", ""])
        self.assertEqual(code, 0)
        payload = json.loads(out)
        self.assertEqual(payload["count"], 0)
        self.assertEqual(payload["mean"], 0.0)
        self.assertEqual(payload["variance"], 0.0)

    def test_weighted_values(self):
        code, out, _ = run_cli(["--values", "10:2,20"])
        self.assertEqual(code, 0)
        payload = json.loads(out)
        self.assertAlmostEqual(payload["mean"], 40.0 / 3.0)
        self.assertAlmostEqual(payload["variance"], 100.0 / 3.0)

    def test_invalid_weight_reports_index(self):
        code, _, err = run_cli(["--values", "1,2:0,3"])
        self.assertEqual(code, 2)
        self.assertIn("第 2 个输入", err)

    def test_invalid_weight_text_reports_index(self):
        code, _, err = run_cli(["--values", "1,2:abc"])
        self.assertEqual(code, 2)
        self.assertIn("第 2 个输入", err)

    def test_invalid_value_reports_index(self):
        code, _, err = run_cli(["--values", "1,oops,3"])
        self.assertEqual(code, 2)
        self.assertIn("第 2 个输入", err)

    def test_quantiles_output(self):
        values = ",".join(str(i) for i in range(1, 101))
        code, out, _ = run_cli(["--values", values, "--quantiles", "50,90,99"])
        self.assertEqual(code, 0)
        payload = json.loads(out)
        self.assertEqual(sorted(payload["quantiles"]), ["50", "90", "99"])
        self.assertAlmostEqual(payload["quantiles"]["50"], 51, delta=1)
        self.assertAlmostEqual(payload["quantiles"]["90"], 91, delta=1)
        self.assertAlmostEqual(payload["quantiles"]["99"], 100, delta=1)

    def test_quantiles_merge_matches_single_pass(self):
        values = ",".join(str(i * 7 % 101) for i in range(1, 201))
        _, single_out, _ = run_cli(["--values", values, "--quantiles", "50,90,99"])
        _, merged_out, _ = run_cli(["--values", values, "--merge", "--quantiles", "50,90,99"])
        single = json.loads(single_out)
        merged = json.loads(merged_out)
        self.assertEqual(single["count"], merged["count"])
        self.assertAlmostEqual(single["mean"], merged["mean"])
        self.assertAlmostEqual(single["variance"], merged["variance"])
        for label in ("50", "90", "99"):
            self.assertAlmostEqual(single["quantiles"][label],
                                   merged["quantiles"][label], delta=2.0)

    def test_invalid_quantile(self):
        code, _, err = run_cli(["--values", "1,2", "--quantiles", "abc"])
        self.assertEqual(code, 2)
        self.assertIn("分位数非法", err)


if __name__ == "__main__":
    unittest.main()
