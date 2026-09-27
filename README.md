# online-stats

在线统计（均值、样本方差、加权样本、合并、分位数），只用 Python 标准库。

```
python3 -m onlinestats.cli --values 100000001,100000002,100000003
python3 -m onlinestats.cli --values 1,1,1,100 --merge
python3 -m onlinestats.cli --values 1,2:2.5,3:0.5 --quantiles 50,90,99
python3 -m unittest discover -s tests -v
```

## 口径（README 为准）

- 用 **Welford 递推**算方差（加权版本），不许用 `Σx² - (Σx)²/n`：
  `--values 100000001,100000002,100000003` 的样本方差是 `1.0`；
  量级 1e12、个数 10^6 时方差不变负、不丢有效位。
- **合并按样本数加权**（Chan 公式：`mean = (n1*m1 + n2*m2)/(n1+n2)`，M2 同样合并），
  不是两个均值的算术平均：`--values 1,1,1,100 --merge` 的均值是 `25.75`，
  且与一次喂完的结果一致。
- **加权样本**：输入 `值:权重`（缺省权重 1），均值/方差按权重递推，
  合并时把权重当作样本数；权重必须为正数，非法权重要报错并指出第几个输入。
- **分位数**：`--quantiles 50,90,99` 用分层压实素描（compactor sketch）在线估计，
  O(1) 内存、更新 O(1) 摊还；合并两个素描与一次喂完同批数据的误差界相同，
  且合并满足交换律（压实偏移由内容哈希决定，与合并顺序无关）。
- 方差是**样本方差**（除以权重和 - 1），权重和不足 2 时为 0；空输入均值/计数为 0。
- 不变量：`merge(a, b)` 与「把两批数据一次喂完」得到同样的 count/mean/variance
  （相对误差 < 1e-9）；合并满足交换律（在浮点误差内）；同一输入重复统计结果相同。
- 规模：1000 万个数在线统计，内存 O(1)（不许把数值全存下来再算）；合并 O(1)。

## 参数

```
--values 列表       逗号分隔的数值，可带权重：值:权重（缺省权重 1，权重必须为正）
--merge             分成两半分别统计再合并
--quantiles 列表    逗号分隔的分位数（百分制，0 到 100），如 50,90,99
```

## 输出

不带 `--quantiles` 时输出格式与之前一致：

```
{"count": …, "mean": …, "variance": …}
```

带 `--quantiles 50,90,99` 时增加 `quantiles` 字段：

```
{"count": …, "mean": …, "quantiles": {"50": …, "90": …, "99": …}, "variance": …}
```

## 目录

```
onlinestats/stats.py      在线均值/方差（加权 Welford + Chan 合并）与分位数素描
onlinestats/reference.py  参考实现（存全量、两遍算法、排序取分位数），供测试对照
onlinestats/cli.py        命令行入口
tests/                    unittest 用例（含 1000 组随机数据与参考实现比对）
```
