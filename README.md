# online-stats

在线统计（均值、样本方差、加权样本、分位数、合并），只用 Python 标准库。

```
python3 -m onlinestats.cli --values 100000001,100000002,100000003
python3 -m onlinestats.cli --values 1,1,1,100 --merge
python3 -m onlinestats.cli --values 1:3,100:1 --quantiles 50,90,99
python3 -m unittest discover -s tests -v
```

## 口径（README 为准）

- 方差用 **加权 Welford 递推**（等价于稳定公式），不用 `Σx² - (Σx)²/n`：
  `--values 100000001,100000002,100000003` 的样本方差是 `1.0`；
  量级 1e12、个数 10^6 时方差仍为正、不丢有效位。
- 方差是**样本方差**（除以 `权重和 - 1`），权重和 `< 2` 时为 0；空输入均值为 0、count 为 0。
- **合并按样本数加权（Chan 公式）**：
  `mean = (w1*m1 + w2*m2)/(w1+w2)`，
  `M2 = M2_1 + M2_2 + (m2-m1)² · w1·w2/(w1+w2)`；
  `--values 1,1,1,100 --merge` 的均值是 `25.75`，与一次喂完一致。
- 加权样本：输入支持 `值:权重`（缺省权重 1，权重必须为正，非法权重报错并指出第几个输入）；
  合并时权重和当作样本数。
- 分位数：`--quantiles 50,90,99`，用固定容量的 compactor 素描（P² 的等价在线算法）
  在 O(1) 内存估计；1 万个均匀样本与「存全量排序」的精确分位数相差不超过 1%。
- 分位数合并是确定性的：结果只取决于两批数据元素的多重集合，严格满足交换律，
  合并后的误差界与一次喂完相同。分位数按观测计数（每个输入计 1 个样本）。
- 不变量：`merge(a,b)` 与一次喂完得到同样的 count/mean/variance（相对误差 < 1e-9）；
  同一输入重复统计结果相同。
- 规模：1000 万个数在线统计内存有界（素描约存 `capacity * log2(n)` 个值，
  实测约 7000 个），不保存全量；合并 O(1)，分位数更新 O(1) 摊还。

## 参数

```
--values 列表       逗号分隔的数值，每项可写成 值[:权重]
--merge             按奇偶分成两半分别统计再合并
--quantiles 列表    逗号分隔的百分位，如 50,90,99（0-100）
```

## 输出

不带新参数时格式不变：

```
{"count": …, "mean": …, "variance": …}
```

带 `--quantiles` 时增加 `quantiles` 字段：

```
{"count": …, "mean": …, "variance": …, "quantiles": {"50": …, "90": …, "99": …}}
```

## 对照与测试

`onlinestats/reference.py` 是「存全量、两遍算法 + 排序取分位数」的参考实现；
`tests/` 覆盖样例、1000 组随机数据对照（count/mean/variance 相对误差 < 1e-9，
分位数 < 1%）、加权、合并不变量、交换律与内存上界。

## 目录

```
onlinestats/stats.py      Welford 均值/方差、Chan 合并、分位数素描
onlinestats/reference.py  存全量两遍算法参考实现（仅供测试对照）
onlinestats/cli.py        命令行入口
tests/                    unittest 用例
```
