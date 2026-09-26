# online-stats

在线统计（均值、样本方差、合并），只用 Python 标准库。

```
python3 -m onlinestats.cli --values 100000001,100000002,100000003
python3 -m onlinestats.cli --values 1,1,1,100 --merge
python3 -m unittest discover -s tests -v
```

## 口径（README 为准）

- 用 **Welford 递推**算方差（或等价的稳定公式），不许用 `Σx² - (Σx)²/n`：
  `--values 100000001,100000002,100000003` 的样本方差按口径是 `1.0`，
  现在因为浮点相消算成 `0.0`。
- **合并要按样本数加权**（Chan 公式：`mean = (n1*m1 + n2*m2)/(n1+n2)`，`m2` 也要合并），
  不是两个均值的算术平均：`--values 1,1,1,100 --merge` 的均值按口径是 `25.75`，现在给 `25.5`。
- 方差是**样本方差**（除以 `n-1`），`n < 2` 时为 0；空输入均值为 0。
- 不变量：`merge(a, b)` 与「把两批数据一次喂完」得到同样的 count/mean/variance；
  合并满足交换律（在浮点误差内）；同一输入重复统计结果相同。
- 规模：1000 万个数在线统计，内存 O(1)（不许把数值全存下来再算）；合并 O(1)。

## 现在的行为

- `variance` 用 `total_squares - total²/n`：大数下相消严重，
  `100000001,100000002,100000003` 给 `variance=0.0`（正解 1.0）。
- `merge` 把两边均值算术平均再乘总个数：`1,1,1,100` 合并（1 个 1 与 2 个 1+100? 按奇偶分两半）后给
  `mean=25.5`，按口径应该是 `25.75`；`m2` 也没有按 Chan 公式合并，方差更不可信。
- 没有保存 `m2` 之类的中间量，只留了 `total` 与 `total_squares`。

## 计划新增的能力

```
--values 列表    逗号分隔的数值
--merge          分成两半分别统计再合并
```

## 输出

```
{"count": …, "mean": …, "variance": …}
```

## 目录

```
onlinestats/stats.py   在线均值/方差与合并
onlinestats/cli.py     命令行入口
tests/                 unittest 用例
```
