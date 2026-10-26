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
| `data_access` | 查询来源（`OpenD` / `database`）、快照ID、原始采集时间、时段判定及缓存说明；不修改报价时点 |
| `trend_as_of`、`trend_decision_cutoff`、`trend_collected_at` | 日线可用日期、决策截止点和获取时间（成功采集时） |

历史补日线保留原报价时点。报价更新时间不保证 Bid 可以按该价格成交。`options` 的合约表与这里的完整输入结构不同，不能直接用于 Put 收益排名。

盘后没有对应请求 / 交易日快照时自动采集：`data_access.source=OpenD`、`cache_miss_fetch=true`、`explicit_refresh=false`，后续匹配查询为database。部分股票命中时返回mixed并逐成员保留来源；获取失败返回错误，不生成空数据冒充成功。

`data_access.batch_id` 关联同批原始采集。组合多股票缓存时，`members` 列出每个股票 / 合约的原始ID、批次和采集时间；不存在共同的单个快照ID时，顶层 `snapshot_id` / `batch_id` 为 null，不能据此假设数据同时取得。顶层采集时间是最新成员时间。触发已配置的清理策略时，`data_access.cleanup` 给出截止时间及删除数量，不修改保留行情的原始日期。

## 独立引擎报告

`analyze` 的 JSON 顶层就是报告。

| 字段 | 用法 |
| --- | --- |
| `engine_version`、`ruleset_version`、`engine_file_sha256` | 标识所用引擎和文件 |
| `dataset_sha256`、`rules_sha256`、`configuration` | 输入、实际配置指纹及可重放配置 |
| `cash_budget`、`budget_checked` | 本次是否检查个人资金上限 |
| `total_contracts`、`qualified_count` | 原始数量与通过全部已启用 Filter 的数量 |
| `results` | 全部逐合约状态、指标、失败规则与证据 |
| `ranked` | 独立默认报告为全部合格者；桌面 / 研究 CLI 为有界选择后的全局 Top 20 |
| `recommendations`、`best_recommendation` | 日常推荐模式的前 N 项及第一名；空结果保留为空 |
| `top_n_requested`、`ranking_views` | 请求数量与五种预设排序的 Top 合约代码 |
| `expiration_comparisons` | 每个到期日的单独比较，不替换 Top 结果 |
| `filter_impact`、`relaxation_preview` | 排除原因计数和模拟放宽后的数量，不改实际配置 |
| `earnings_unverified_watchlist` | 财报硬条件启用时，其他条件通过但财报未验证者 |

`ranked` 行包含 `metrics`、`failed_rules` 和 `scoring`；推荐项另整理日期、行权价、成本、三种分数、原因、取舍及情景。评分证据和缺失维度在 `scoring.components` 中。`--scan-only` 保留扫描报告，不添加推荐专用字段。

桌面 / 研究入口调用 `recommend(..., per_symbol_limit=20)`：`qualified_count` 仍是所有合格合约的数量，不能用 `len(ranked)` 代替；`ranked_truncated` 表明是否截短。`ranking_reduction` 给出每股保留数、合并池大小及最终保留数。预设排序的 `ranking_views` 也在全部合格候选上用相同有界选择生成；`auxiliary_rank_scope=top_per_symbol_limit` 时，仅给各预设 Top 20 内的序号，其余辅助序号为 null，不虚构全局名次。`expiration_comparisons_scope=retained_candidates` 只比较保留候选中的日期。完整逐合约 Filter 证据仍在 `results`，完整行情仍在 `input_dataset`。

CSV 的 `category` 区分 `qualified` 与 `earnings_unverified`，导出完整名单，不限于 Top N。把待确认名单当成合格结果会绕过硬条件。

## 单股票研究与桌面导出

Put 研究包装结构为：

```text
action: "put"
symbol: "US.AVGO"
collected_at: 原始采集时间
report: 上述独立引擎报告
input_dataset: 原始输入
price_signals: 按股票代码组织的独立价格位置与择时信号
```

趋势研究结构为 `action: "trend"`、`symbol`、`collected_at`、`trend`；`trend.outlook` 包含文字判断。两种研究结果从共享查询层取得数据时还包含 `data_access`；离线 Put 重算保留输入中原有的来源信息。

两种研究另附 `price_signals`，与 `report` 平级：`version`、`status`（`ok` / `unavailable`）、`ranking_effect=none`、`assessment`、`summary`、`reference`（价格、时间、依据）、`as_of`、`parameters`、`support_zones` / `resistance_zones`、`next_check`、`limitations`。区域包含边界、中心、距离、独立转折数和带确认日期的证据。`order_flow.status=not_verified`、`buy_sell_ratio=null`；不能把历史区域当成当前买卖挂单。缺失日线返回不可用原因，现有排名报告保持原样。单股仅一个代码，Watchlist 包含各股票结果，逐股趋势的 `items[]` 内也保留同一结构。

桌面首页的研究 CLI `overview` 返回 `rows[]`：`symbol`、`name`、`security_type`、`price`、`previous_close`、`change_pct`、`update_time`，以及报价的 `collected_at`、`data_access`。界面只显示股票名、股价和涨跌；缺失价格或昨收时对应数值为 `null`。个股 `trend --depth` 另附 `quote`、`order_book`；有效 `price_signals` 保存到 SQLite 并返回 `price_signal_saved_at`，当前计算失败且存在旧记录时返回 `saved_price_signal`（含 `signal` 和 `calculated_at`）。个股信号还附带 `multi_timeframe`：`version`、`status`、`source`、`decision_cutoff`、`periods.week` / `periods.month`，每个周期含 `as_of`、`bars`、ATR 与支撑阻力区间，数据不足时保留 `reason`。盘口含 `status`、`collected_at`、`bid_server_time`、`ask_server_time`、请求深度 `depth`、实际返回数 `returned_bids` / `returned_asks`，以及最多 60 档 `bids` / `asks`（价、可见数量）。获取失败保留 `unavailable` 原因，不影响可用的趋势或报价。盘口不是 `price_signals.order_flow`，后者仍不声称已验证实际成交方向。

`research_cli radar` 读取相同 Watchlist 报价和 SQLite 已保存价位，返回按关注状态与距支撑区排序的 `rows[]`。每行在首页报价字段外增加 `support_low`、`support_high`、`signal_as_of`、`alert_mode`、`state`、`distance_pct`、`stale_alert`；没有价位或报价时相应字段为 `null`，状态为 `levels_unavailable` 或 `quote_unavailable`。`research_cli alerts` 的记录增加 `confirmation_mode`、`entered_at`、`last_bar_date`；`event` 只在首次进入确认或失效状态时为真。

桌面「导出结果」会再按动作包装：顶层的 `put` 和 / 或 `trend` 对应上述单股票研究结果。重算桌面 Put 导出时提取 `exported['put']['input_dataset']`；直接保存的研究 CLI Put 结果则提取 `result['input_dataset']`。再把原始 dataset 交给 `analyze` 或研究 CLI `--input`，报告本身不能当作原始数据。

研究 CLI 的已处理运行错误为 `{"error":"..."}`，参数用法错误仍是 argparse stderr；先检查退出码再解析。

桌面或研究 CLI 查询整个 Watchlist 时，包装增加 `query_scope: "watchlist"`、`symbols`，`symbol` 为 `"Watchlist"`。Put 的 `input_dataset` 合并全部成功取得的原始合约，`report` 对全部合约统一排序取 Top N；趋势结果使用 `items[]` 保存逐股趋势包装。`collection_errors[]` 保留失败股票及原因，存在失败项时界面明确标记部分结果。各股票的原始采集时间保留在 `data_access.members`，不表示同时报价。

## 股票名单

JSON 股票名单入口的报告另外包含 `precheck`、`results[]`、`summary`；`results[]` 按股票包装上述单股研究结果，`ranking_scope=per_symbol`。完整检查状态、错误行为和字段见[股票列表指南](../guides/watchlists.md)。

## MCP

工具成功返回抓取服务的可 JSON 序列化结果，包含各接口的数据、来源、时间及缺失说明。工具参数校验或 provider 错误通过 MCP tool error 返回；使用 SDK 时检查 `is_error`，成功数据从 `structured_content` 读取。一个成功协议响应中仍可能有逐项数据错误。

四个工具的具体参数见 [MCP 指南](../guides/mcp-server.md)，各 CLI 的通道与退出码见 [CLI 参考](cli.md)。

## 股票模拟盘报告

`paper report ID` 与 create / backtest / update 的成功JSON包含 `id`、`name`、`version`、`mode=forward|backtest`、`start_date`、`as_of`、`config`、`clients`、`history`、`fills`、`skipped_decision_dates`、`limitations`。配置冻结股票池、单股投入、费用、滑点、客户参数和 `engine_sha256`。

`clients[]` 包含NAV、现金、累计注资、净损益、已实现 / 未实现损益、时间加权 `return_pct`、最大回撤、暴露、费用、滑点、成交数、双边成交额 / 平均NAV的换手率，以及 `excess_vs_buy_hold_pct`、`excess_vs_qqq_pct`、`excess_vs_spy_pct`（百分点差）。v1.1默认6客户，含buy_qqq / buy_spy；`benchmark_returns`给两个ETF收益，旧v1.0无对应记录时为null。`config.symbols`是策略池，`market_symbols`是附加ETF后的行情池，每个客户冻结自己的symbols与entry_notional；基准目标投入为完整起始参考资金。`periods[]` 为1 / 3 / 6个月，各有target_date、status、measured_date、return_pct、drawdown_pct；pending数值为null。

`history[]` 按日期 / 客户保存每日估值、持仓、注资、公司行动和当日决策；`fills[]` 保存每次虚拟成交及 `signal_as_of` / `signal_generated_at`。更新另有 `new_valuations` / `new_fills`；同日再次更新两者为0。失败为error字符串，不能当作零收益。专用原始输入由 `paper_data.py` 定义：`daily_series` 必须是none复权、regular时段的已完成1d日线，另有按symbol归属的 `actions[].rows` 公司行动。普通Put数据不可直接用于模拟成交。

模拟盘v1.2：config.initial_capital为新客户默认本金（500000美元），config.clients[].initial_capital冻结各客户实际本金，clients[].initial_capital直接展示实际起点；funding_mode为fixed或auto_deposit。固定资金不补资，history[].execution_events记录现金限制下的缩单；历史版本报告从原config.initial_capital读取起点，保留原模式。
