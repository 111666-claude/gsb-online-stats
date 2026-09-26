"""命令行入口：喂一串数值并打印统计量。"""

import argparse
import json
import sys

from .stats import Stats


def build_parser():
    parser = argparse.ArgumentParser(prog="online-stats", description="在线统计")
    parser.add_argument("--values", required=True, help="逗号分隔的数值")
    parser.add_argument("--merge", action="store_true", help="分成两半分别统计再合并")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        values = [float(part) for part in args.values.split(",") if part.strip()]
    except ValueError:
        print("错误：数值里有非数字", file=sys.stderr)
        return 2
    if args.merge:
        left, right = Stats(), Stats()
        for index, value in enumerate(values):
            (left if index % 2 == 0 else right).add(value)
        left.merge(right)
        stats = left
    else:
        stats = Stats()
        for value in values:
            stats.add(value)
    print(json.dumps({"count": stats.count, "mean": stats.mean(), "variance": stats.variance()}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
