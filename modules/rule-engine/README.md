# 独立行情规则引擎

Python 包 `moomoo-rule-engine`，不依赖 Qt、Swift、OpenD SDK 或 AI SDK。输入标准化日线，输出可以让两个桌面客户端或 Codex 读取的 JSON。第一版只有确定性扫描；尚未接入真实 OpenD 数据、自动每日任务、新闻、模型调用或下单。

## 运行

```sh
python3 -m pip install ./modules/rule-engine
moomoo-scan modules/rule-engine/examples/daily-bars.json --output /tmp/scan.json
# 规则单独存放，不必改动或重新安装引擎
moomoo-scan /path/to/daily-bars.json --rules /path/to/my-rules-1.1.0.json --output /tmp/scan.json
```

示例是明确标注的合成数据，不能用于投资判断。Python API：

```python
from moomoo_rules import load_rules, scan
report = scan(dataset, load_rules('/path/to/rules.json'))
```

## 输入与指标

输入顶层：`schema: 1`、`as_of: YYYY-MM-DD`（最近已完成交易日，不是运行时日期）、`series: [...]`。每条序列含 `symbol`、`source`、`interval: 1d`、`adjustment: qfq`、`session: regular` 和 `bars`。每根日线包含 `date/open/high/low/close/volume/complete`。完整示例见 `examples/daily-bars.json`。

至少需要 200 根严格按日期升序排列的完整日线；末根日期必须等于 as_of。拒绝重复、未来、未完成、非法数值或不一致的 OHLC。适配器仍需检查官方交易日历、停牌/缺失交易日、真实行情权限和拆股复权；本模块不能仅凭日期确定这些事实。不同市场应分别使用各自的已完成交易日扫描。

- MA20/50/200：最后 N 个交易日收盘价的简单平均。
- 距均线百分比：`100 × (close / MA - 1)`。
- MA50 五日斜率：`100 × (当前 MA50 / 五根日线之前的 MA50 - 1)`，不是每日斜率。
- 量比：最新日线成交量 / 前 20 个交易日平均成交量，分母不含当日。
- RSI14：Wilder 平滑，首 14 个价格变动初始化；全平时返回 50，全涨 100，全跌 0。
- ATR14：真实波幅的 Wilder 平滑，首根因无前收盘价不参与初始化。为了可复查，应固定历史起点；递归平滑结果可能随历史起点不同而变化。

## 规则与单独更新

内置规则在 `src/moomoo_rules/rules/trend.json`，引擎版本和规则版本各自独立。规则只能引用允许的指标和比较操作，禁止执行 Python 表达式或脚本。每条规则含阈值、正权重和 required 标志。所有 required 条件通过才进入候选排名；分数为命中权重占全部权重的百分比，相同分数按股票代码排序。分数不是预期收益或上涨概率。

更新阈值时复制 JSON、提高 version、运行测试，再通过 `--rules` 选择新文件，无需重新打包 Mac 界面。新增指标或新规则语法仍要升级引擎代码。第一版不从网络自动激活规则；外部 JSON 在使用时经过格式和兼容性验证。结果含规则内容与行情内容 SHA-256、版本、日期、原始数值和每条规则证据；修改文件但忘记提高版本，也能由指纹识别。

每只股票数据错误会标记 `invalid_data`，不参与排名。全局输入/规则格式错误终止扫描。所有候选都可能不合格，此时输出空列表。AI 使用方式见 [AI_ANALYSIS.md](AI_ANALYSIS.md)。

## 测试与独立构建

```sh
PYTHONPATH=modules/rule-engine/src python3 -m unittest discover -s modules/rule-engine/tests -v
python3 -m pip install build
python3 -m build modules/rule-engine
```

`.github/workflows/rule-engine.yml` 单独测试 Python 3.10/3.14，构建 wheel/sdist，在干净虚拟环境安装 wheel 后重新跑测试和示例扫描，输出独立下载 artifact。它不向 PyPI 发布，不需要安装 OpenD 或提供账号。该模块尚未打进两版 Mac 应用，可作为独立进程通过 JSON 文件调用，后续接入统一的数据采集服务。
