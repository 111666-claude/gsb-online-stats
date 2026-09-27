"""命令行入口：喂一串数值并打印统计量。"""

import argparse
import json
import math
import sys

from .stats import Stats


def build_parser():
    parser = argparse.ArgumentParser(prog="online-stats", description="在线统计")
    parser.add_argument("--values", required=True,
                        help="逗号分隔的数值，可带权重：值:权重（缺省权重 1）")
    parser.add_argument("--merge", action="store_true", help="分成两半分别统计再合并")
    parser.add_argument("--quantiles", help="逗号分隔的分位数（百分制），如 50,90,99")
    return parser


def _parse_samples(text):
    samples = []
    for index, part in enumerate(text.split(","), start=1):
        part = part.strip()
        if not part:
            continue
        raw_value, sep, raw_weight = part.partition(":")
        try:
            value = float(raw_value)
        except ValueError:
            raise ValueError("错误：第 %d 个输入的数值非法：%r" % (index, raw_value))
        if not math.isfinite(value):
            raise ValueError("错误：第 %d 个输入的数值非法：%r" % (index, raw_value))
        weight = 1.0
        if sep:
            try:
                weight = float(raw_weight)
            except ValueError:
                raise ValueError("错误：第 %d 个输入的权重非法：%r（权重必须为正数）"
                                 % (index, raw_weight))
            if not math.isfinite(weight) or weight <= 0.0:
                raise ValueError("错误：第 %d 个输入的权重非法：%r（权重必须为正数）"
                                 % (index, raw_weight))
        samples.append((value, weight))
    return samples


def _parse_quantiles(text):
    specs = []
    for part in text.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            percent = float(part)
        except ValueError:
            raise ValueError("错误：分位数非法：%r（应为 0 到 100 之间的数）" % part)
        if not math.isfinite(percent) or not 0.0 <= percent <= 100.0:
            raise ValueError("错误：分位数非法：%r（应为 0 到 100 之间的数）" % part)
        specs.append((part, percent / 100.0))
    return specs


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        samples = _parse_samples(args.values)
        quantile_specs = _parse_quantiles(args.quantiles) if args.quantiles else []
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 2
    probabilities = [probability for _, probability in quantile_specs]
    if args.merge:
        left = Stats(quantiles=probabilities)
        right = Stats(quantiles=probabilities)
        for index, (value, weight) in enumerate(samples):
            (left if index % 2 == 0 else right).add(value, weight)
        left.merge(right)
        stats = left
    else:
        stats = Stats(quantiles=probabilities)
        for value, weight in samples:
            stats.add(value, weight)
    result = {"count": stats.count, "mean": stats.mean(), "variance": stats.variance()}
    if quantile_specs:
        result["quantiles"] = {label: stats.quantile(probability)
                               for label, probability in quantile_specs}
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
