# 分析股票趋势

趋势分析基于已完成的常规时段前复权日线，输出未来5–20个交易日的条件判断。桌面输入股票后点击「分析走势」即可，无需 MCP 或外部 AI Key。

## 1. 获取研究结果

macOS 从仓库根目录执行：

```sh
mkdir -p artifacts/trend
apps/python/.venv/bin/python -m moopython.research_cli trend AVGO \
  --output artifacts/trend/avgo.json
```

Windows：

```powershell
New-Item -ItemType Directory -Force artifacts/trend
& .\apps\python\.venv\Scripts\python.exe -X utf8 -m moopython.research_cli trend AVGO --output artifacts/trend/avgo.json
```

该入口不会自动创建输出父目录。运行成功后读取 `trend`，其中 `outlook` 是独立规则生成的文字判断。根目录启动器没有 `trend` 子命令。

## 2. 检查数据是否适用

确认股票、采集时间和 `trend.as_of`。盘中只能使用上一已完成交易日；采集按交易日历处理假日、半日市，并在收盘后留5分钟。指标计算至少需要205根有效日线；缺失或过期数据应保留错误。

MCP 的 `get_daily_bars` 只返回日线与元数据，不直接给趋势结论。通过 MCP 获取后，分析仍应复用独立 `put_rules.py` 的 `trend()` 和 `describe_trend()`；Python 组合接口见[架构参考](../reference/architecture.md)。

## 3. 用证据解释判断

- 位置与方向：收盘价相对 MA20/50/200，MA50及短期均线的斜率。
- 动量：RSI14、MACD(12,26,9)柱及变化。
- 价位：此前20/60日低点、近期高低点结构、ATR14。
- 量：当日成交量相对前20日均量。

报告说明哪些指标支持当前判断、哪些相互矛盾，再给出关键价位和改判条件。例如价格重新站上对应均线且动量改善，可以作为重新审查的条件；超卖本身不证明止跌。

默认五项趋势参考与计算初始化见[独立规则说明](../../modules/put-screener/README.md)。规则未通过项数也参与 Put 风险评分，但不是下跌概率。关闭趋势 Filter 只取消硬拦截，风险证据和趋势描述继续保留。

历史 `cutoff` 只限制日线可用时点，不能还原当时的全部财报、公告或复权版本，因此不能直接当成历史策略回测。
