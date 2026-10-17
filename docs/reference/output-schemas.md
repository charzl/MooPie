# 输出结构与解析

本页说明当前代码实际输出的结构，完整字段以代码和合成示例为准。关键字段缺失时应报错；读取方可以忽略不需要的新增字段。当前没有独立发布的 JSON Schema 或统一错误信封。

## 原始 Put 输入

`collect` 写出的 JSON 可直接交给独立规则引擎。可运行的合成输入见 [example.json](../../modules/put-screener/example.json)。

| 字段 | 含义 |
| --- | --- |
| `schema`、`source` | 当前格式1及数据来源 |
| `collected_at`、`session_date`、`timezone` | 采集时间、报价基准交易日、市场时区 |
| `symbols`、`coverage` | 请求股票和采集覆盖范围 |
| `contracts` | 合约身份、Bid/Ask、Delta、股价、财报及快照时间等标准化字段 |
| `missing_quote_codes`、`calendar_errors` | 缺失报价和财报查询失败，不能默认为无风险 |
| `daily_series` | 每只股票的已完成日线或明确错误 |
| `trend_as_of`、`trend_decision_cutoff`、`trend_collected_at` | 日线可用日期、决策截止点和获取时间（成功采集时） |

历史补日线保留原报价时点。报价更新时间不保证 Bid 可以按该价格成交。`options` 的合约表与这里的完整输入结构不同，不能直接用于 Put 收益排名。

## 独立引擎报告

`analyze` 的 JSON 顶层就是报告。

| 字段 | 用法 |
| --- | --- |
| `engine_version`、`ruleset_version`、`engine_file_sha256` | 标识所用引擎和文件 |
| `dataset_sha256`、`rules_sha256`、`configuration` | 输入、实际配置指纹及可重放配置 |
| `cash_budget`、`budget_checked` | 本次是否检查个人资金上限 |
| `total_contracts`、`qualified_count` | 原始数量与通过全部已启用 Filter 的数量 |
| `results` | 全部逐合约状态、指标、失败规则与证据 |
| `ranked` | 全部合格者的当前排序 |
| `recommendations`、`best_recommendation` | 日常推荐模式的前 N 项及第一名；空结果保留为空 |
| `top_n_requested`、`ranking_views` | 请求数量与五种预设排序的 Top 合约代码 |
| `expiration_comparisons` | 每个到期日的单独比较，不替换 Top 结果 |
| `filter_impact`、`relaxation_preview` | 排除原因计数和模拟放宽后的数量，不改实际配置 |
| `earnings_unverified_watchlist` | 财报硬条件启用时，其他条件通过但财报未验证者 |

`ranked` 行包含 `metrics`、`failed_rules` 和 `scoring`；推荐项另整理日期、行权价、成本、三种分数、原因、取舍及情景。评分证据和缺失维度在 `scoring.components` 中。`--scan-only` 保留扫描报告，不添加推荐专用字段。

CSV 的 `category` 区分 `qualified` 与 `earnings_unverified`，导出完整名单，不限于 Top N。把待确认名单当成合格结果会绕过硬条件。

## 单股票研究与桌面导出

Put 研究包装结构为：

```text
action: "put"
symbol: "US.AVGO"
collected_at: 原始采集时间
report: 上述独立引擎报告
input_dataset: 原始输入
```

趋势研究结构为 `action: "trend"`、`symbol`、`collected_at`、`trend`；`trend.outlook` 包含文字判断。

桌面「导出结果」会再按动作包装：顶层的 `put` 和 / 或 `trend` 对应上述单股票研究结果。重算桌面 Put 导出时提取 `exported['put']['input_dataset']`；直接保存的研究 CLI Put 结果则提取 `result['input_dataset']`。再把原始 dataset 交给 `analyze` 或研究 CLI `--input`，报告本身不能当作原始数据。

研究 CLI 的已处理运行错误为 `{"error":"..."}`，参数用法错误仍是 argparse stderr；先检查退出码再解析。

## MCP

工具成功返回抓取服务的可 JSON 序列化结果，包含各接口的数据、来源、时间及缺失说明。工具参数校验或 provider 错误通过 MCP tool error 返回；使用 SDK 时检查 `is_error`，成功数据从 `structured_content` 读取。一个成功协议响应中仍可能有逐项数据错误。

四个工具的具体参数见 [MCP 指南](../guides/mcp-server.md)，各 CLI 的通道与退出码见 [CLI 参考](cli.md)。
