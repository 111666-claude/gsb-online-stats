"""命令行入口：喂一串数值并打印统计量。"""

import argparse
import json

from .stats import Stats


def build_parser():
    parser = argparse.ArgumentParser(prog="online-stats", description="在线统计")
    parser.add_argument("--values", required=True, help="逗号分隔的数值，可带权重：值[:权重]")
    parser.add_argument("--merge", action="store_true", help="分成两半分别统计再合并")
    parser.add_argument("--quantiles", help="逗号分隔的百分位，如 50,90,99")
    return parser


def _parse_values(text):
    """解析 值[:权重] 列表（缺省权重 1），返回 (value, weight) 列表。

    非法输入抛出 ValueError，错误信息指出是第几个输入（从 1 开始）。
    """
    items = []
    for index, part in enumerate(text.split(","), start=1):
        part = part.strip()
        if not part:
            continue
        value_text, separator, weight_text = part.partition(":")
        if not separator:
            weight_text = "1"
        try:
            value = float(value_text)
        except ValueError:
            raise ValueError(f"第 {index} 个输入不是数字：{part}") from None
        try:
            weight = float(weight_text)
        except ValueError:
            raise ValueError(f"第 {index} 个输入的权重不是数字：{part}") from None
        if not weight > 0.0:
            raise ValueError(f"第 {index} 个输入的权重必须为正数：{part}")
        items.append((value, weight))
    return items


def _parse_quantiles(text):
    """解析百分位列表，返回 (标签, [0,1] 比例) 列表。"""
    specs = []
    for part in text.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            percent = float(part)
        except ValueError:
            raise ValueError(f"分位数不是数字：{part}") from None
        if not 0.0 <= percent <= 100.0:
            raise ValueError(f"分位数必须在 [0, 100] 内：{part}")
        specs.append(("%g" % percent, percent / 100.0))
    return specs


def main(argv=None):
    import sys

    args = build_parser().parse_args(argv)
    try:
        items = _parse_values(args.values)
        quantile_specs = _parse_quantiles(args.quantiles) if args.quantiles else []
    except ValueError as error:
        print(f"错误：{error}", file=sys.stderr)
        return 2
    quantiles = [fraction for _, fraction in quantile_specs]

    def build():
        return Stats(quantiles)

    if args.merge:
        left, right = build(), build()
        for index, (value, weight) in enumerate(items):
            (left if index % 2 == 0 else right).add(value, weight)
        left.merge(right)
        stats = left
    else:
        stats = build()
        for value, weight in items:
            stats.add(value, weight)

    result = {
        "count": stats.count,
        "mean": stats.mean(),
        "variance": stats.variance(),
    }
    if quantile_specs:
        result["quantiles"] = {label: stats.quantile(p) for label, p in quantile_specs}
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
