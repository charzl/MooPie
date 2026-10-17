# 独立卖 Put 规则文件

规则、阈值、计算、排序和 JSON/CSV 输出都在 **`put_rules.py`**。这是单个独立 Python 文件，只依赖标准库，直接复制它即可运行；无需安装 Qt、moomoo SDK 或 `modules/rule-engine`。开发和 CI 使用 Python 3.14。

Filter 决定保留哪些合约，Sort 独立决定保留者的顺序。`TREND_RULES`、`RULES`、`SORT_ORDER` 是可编辑的默认值；每次运行可通过 JSON `configuration` 覆盖开关、阈值和排序，不改变默认值。已启用的 Filter 必须全部通过；关闭的条件不再排除，但相关风险仍保留。标准100股/未停牌和计算所需基础数据检查始终执行。报告记录实际配置、指纹和输入数据指纹，便于复现。

可选范围Filter为 `min-cost`（成本>下限）、`max-cost`（成本<上限）、`min-daily-return`（日均毛收益率>门槛）、`max-risk`（风险分<上限）、`expiry-before`（到期日<ISO日期，不含当天）。它们默认关闭；成本为美元金额，收益门槛0.05表示0.05%/天。全部条件在完整候选上检查，再排序截取所选Top 5/10/20；风险分限制使用当前评分模型。组合配置示例见[评分说明](../../docs/put-scoring.md)。

新增指标或修改默认规则时仍只编辑同一 `put_rules.py`，提高 `RULESET_VERSION`。日常入口是 `recommend(dataset, budget=None, configuration=None, top_n=10)`，CLI 和桌面均使用它。基础边界由同一文件的 `RECOMMENDATION_BOUNDARIES` 定义；`recommendation_configuration()` 返回该配置。旧的 `scan()` / CLI `--scan-only` 保留原全部条件启用的默认配置，用于单独审查和兼容。

规则引擎直接返回：

- `decision` / `decision_summary`：边界内是否有候选；没有时保留空结果。
- `best_recommendation`：总体排序第一名的日期、行权价、权利金、担保本金、日均毛收益率及盈亏平衡。
- `recommendations`：严格返回当前排序的Top N，桌面可选5/10/20，默认10；不足所选数量返回实际数量。先对完整候选排序再截取，不限制抓取范围。`overall_rank` 与完整 `ranked` 一致，不为分散到期日跳过更高名次。
- 每个推荐的 `reasons`、`tradeoffs`、`risk_notes`、`scenarios`：选择依据、Delta/价差/最大亏损、未知信息及到期时股价不变或下跌10/20/30/100%的损益（费用前）。UI 直接展示这些结果。
- `expiration_comparisons`：每个到期日的最优合约；`comparison_basis`：公式、实际排序和选择策略；实际配置与原始指纹仍保留。
- `return_score` / `risk_score` / `composite_score`：收益分、风险分和综合分；`scoring.components` 有每项风险权重、贡献、证据和未知状态，`ranking_views` 提供到期时长、担保成本、收益、风险、综合五种排序的Top代码。评分初版为可修改的研究假设，不是概率或预期损失模型。[完整公式与配置](../../docs/put-scoring.md)。

默认排名为 **日均权利金毛收益率 = 每张 Bid 权利金 ÷ 全额现金担保本金 ÷ 剩余自然日 × 100%**。假设完整保留权利金，不是每天实际盈利，也不是扣除风险后的预期回报。例：$200 / $10,000 / 30 ×100%=0.0667%/天。硬边界限定允许承担的风险后，才比较该指标；没有额外软分数门槛。

## 采集与运行

在仓库根目录运行，先在官方 OpenD 登录。只有采集步骤需要已安装 SDK 的客户端 Python 环境：

```sh
apps/python/.venv/bin/python scripts/collect-put-data.py NVDA AVGO AAPL \
  --output artifacts/put-screen/input.json

python3.14 modules/put-screener/put_rules.py artifacts/put-screen/input.json \
  --output artifacts/put-screen/ranking.json \
  --csv-output artifacts/put-screen/ranking.csv

# 资金上限针对一份合约被指派时的全部接股现金
python3.14 modules/put-screener/put_rules.py artifacts/put-screen/input.json \
  --budget 25000 --output artifacts/put-screen/budget-ranking.json
```

`scripts/collect-put-data.py` 是 `MarketDataService` 的兼容 CLI 入口（[基础接口和 MCP](../../docs/market-data.md)），只采集数据，不排序：查询未来三个月全部挂牌 Put，补充 Bid/Ask、Delta、IV、成交量、未平仓量、财报日历和约 550 个自然日内的复权日线。支持 `--months` 和 `--port`。当前筛选器只支持美元计价的标准美股/ETF Put，读取 SDK 报价，不查询账户或执行订单。缺失报价在 `missing_quote_codes` 中列出；财报日历失败在 `calendar_errors` 中列出，不填造数据。

把上面的 `input.json` 交给规则文件即可独立重跑，修改规则无需再次联网，也无需重新打包客户端。单独复制引擎文件时，输入字段参考 `example.json`；该示例完全是合成数据。

例如用户明确选择启用最小未平仓量、关闭趋势过滤并改为低 Delta 优先时，将下面保存为 `filters.json`（演示配置，不是策略建议）：

```json
{
  "schema": 1,
  "filters": {
    "open-interest": {"enabled": true, "threshold": 100},
    "underlying-trend": {"enabled": false}
  },
  "sort_order": [["abs_delta", "asc"], ["spread_pct_of_mid", "asc"]]
}
```

运行 `./moomoo analyze input.json --config filters.json --output ranking.json`。未指定项继承推荐基础预设，字段拼错、重复排序或最小值高于最大值会报错。趋势子条件用 `trend_filters`，例如 `{"rsi-floor":{"enabled":false}}`，总开关 `underlying-trend` 需启用才作硬限制。财报默认只提示；若显式启用任一财报条件，未知日期可能被拦截；关闭前者而保留间隔检查，未知日期仍无法通过。

## 股票趋势证据与可选硬限制

先计算每个股票的日线趋势，再分析其 Put。推荐模式默认将趋势作为风险提示；用户可将 `underlying-trend` 显式启用为硬限制，再选择下面的子条件。`scan()` 兼容模式默认要求全部通过。这五个条件定义在独立文件顶部的 `TREND_RULES`，只是待验证的初始研究假设，不是经过回测的收益优势：

| 条件 | 初始阈值 |
| --- | --- |
| 相对位置 | 收盘价 ≥ MA50 |
| 均线方向 | MA50 相对 5 个交易日前的变化 ≥0 |
| 破位 | 收盘价不低于此前 20 根日线的最低价（不包含当日） |
| 动量水平 | Wilder RSI14 ≥40 |
| 动量变化 | MACD(12,26,9) 柱值不比前一天恶化 |

同时输出 MA20/50/200、MA20 斜率、ATR14、此前 20/60 日低点、最近两个不重叠五日窗口的高低点变化、当日成交量 / 此前 20 日均量。`strike_below_20d_low_atr` 是 `(此前20日低点−行权价)/ATR14`，仅供参考，不是支撑位必然有效的假设，也不参与默认排序。成交量和 MA200 目前只提供证据，未额外设硬门槛。

MA 使用简单平均；EMA 使用 SMA 初值；RSI 和 ATR 使用 Wilder 平滑。浮点误差范围内的 MACD 柱变化取 12 位小数。不同软件因初始化、复权和数据长度，结果可能略有差异。RSI 超卖不能独立证明止跌；趋势通过也不代表未来不会下跌，不输出未经校准的下跌概率。

采集只使用常规时段、前复权、已完成日线；按美股交易日历处理周末、假期和半日市，收盘后留 5 分钟。至少需要205根日线；无效日线会阻止启用趋势 Filter 时的候选。关闭趋势 Filter 后，错误仍显示，但可继续其他过滤。盘中只能使用上一已完成交易日；报价采集时间之前尚未收盘的日线不可用于该次分析。`underlyings` 保存实际筛选检查和默认趋势参考；关闭某项 Filter 不改变趋势描述。

已有报价文件可单独补日线，保留原报价采集时间并以该时间为可用数据截止点：

```sh
apps/python/.venv/bin/python scripts/collect-put-data.py \
  --enrich artifacts/put-screen/input.json --output artifacts/put-screen/trend-input.json
```

指标参考：[Fidelity MACD](https://www.fidelity.com/learning-center/trading-investing/technical-analysis/technical-indicator-guide/macd)、[Fidelity RSI](https://www.fidelity.com/learning-center/trading-investing/technical-analysis/technical-indicator-guide/RSI)、[Schwab 技术指标误区](https://www.schwab.com/learn/story/technical-indicators-3-trading-traps-to-avoid)。这些资料解释指标含义，不为本项目的阈值或组合提供回测证明。

## 合约条件与排序

假设为现金担保卖 Put，并愿意接受指派后持股。尚未确认个人适合程度、估值和组合集中度。

| 条件 | 初始阈值 |
| --- | --- |
| 合约 | 标准 100 股、未停牌、合约表与快照标的/日期/行权价/股数一致 |
| 数据 | 正数且未倒挂的 Bid/Ask；快照属于最新交易日；Put Delta 合法 |
| 期限 | 7–90 个自然日 |
| 价外空间 | `(股价−行权价)÷股价 ≥0%` |
| Delta | 绝对值 ≤0.30；不设置最低Delta门槛 |
| 买盘 | Bid ≥$0.10、买盘数量 ≥1 |
| 流动性 | 未平仓量和成交量展示；最低阈值默认不拦截，可选启用 |
| 价差 | `(Ask−Bid)÷((Ask+Bid)/2) ≤15%` |
| 财报 | 默认未知或跨财报提示风险；可选启用“日期已知”和“至少提前3天到期” |
| 股票趋势 | 默认参考及风险提示；启用硬限制后需通过所选趋势条件 |
| 预算 | 可选：行权价×100 不超过传入预算；未提供时明确标记未检查 |

上述数值是研究示例，不是用户已认可的个人风险上限。标准合约/未停牌和基础数据校验始终执行；其他边界可显式调整，任何已启用条件都不能为凑结果而自动放宽。原兼容 `scan()` 默认仍为21–60天、价外≥5%、Delta0.15–0.30、未平仓量≥200、成交量≥10、财报与趋势全部通过。

通过全部已启用 Filter 后，默认按 `Bid÷行权价÷剩余天数×100%` 从高到低排序，并列时比较价差、绝对Delta，最后按合约代码固定顺序。用户可独立修改 `sort_order`；Sort 不改变候选集合。日均毛收益率乘365等于简单年化，排序相同；该比较未经回测，不代表预期或可重复收益。

期限、日均和年化统一以输入的 `session_date` 为报价基准日。周末重跑上一个交易日的输入，得到的仍是该交易日的研究排名。

每份合约的计算：

- 权利金毛收入 / 最大期权收益：`Bid×股数`，使用买方报价估算，不能保证成交。
- 现金担保：`行权价×股数`，不以券商杠杆保证金代替。
- 到期盈亏平衡价：`行权价−Bid`。
- 最大损失：`(行权价−Bid)×股数`，对应股票价值降至零。
- 股价下跌 20% 时到期损益：`Bid×股数−max(行权价−当前股价×0.8, 0)×股数`。

全部金额和回报均未扣手续费、滑点、税费，也未计入现金利息。Delta 是敏感度，不能当作精确指派概率。`iv_pct` 只展示当时 IV，未计算 IV Rank 或历史分位，也未把高 IV 自动视为卖出优势。接口返回 IV=0 时按未知值处理，不因这一可选字段缺失直接排除；Delta、报价和其他必要条件仍需通过。

## 合格与待确认名单

`ranked` 只包含基础校验和全部已启用 Filter 通过的合约。推荐模式默认财报未知不拦截，但 `warnings` 保留未验证状态，`live_review_ready=false`。启用财报硬限制后，未知日期仍是 `eligible=false`；其余条件通过时进入 `earnings_unverified_watchlist`。已知财报冲突同样不会因关闭 Filter 而消除提示。

`filter_impact` 显示单项排除数与仅关闭该项后的候选数；`relaxation_preview` 模拟关闭趋势、财报或两者后的数量。计数可重叠，这些模拟不修改配置。桌面可用已采集数据离线重新筛选；时间仍是原始采集时点，不表示刷新了报价。

财报来自 moomoo 日历，不表示发行人已经确认。未列出日期属于未知，不能推断无财报；即使日历列出日期，交易前仍应核对最新公告。当前采集结果若在收盘后获取，排序仅用于研究；`live_review_ready` 只有在常规市场开放且快照时间未超过 15 分钟时才可能为 true。快照更新时间也不能保证 Bid 的真实时效，该标志不表示可以自动下单。

原始采集 JSON、全部规则证据和每个排除原因都保留。规则引擎本身不联网，不含订单 API，不修改输入或自动调整阈值。

计算依据：[OIC 现金担保 Put](https://www.optionseducation.org/strategies/all-strategies/cash-secured-put)。字段依据：[moomoo 市场快照](https://openapi.moomoo.com/moomoo-api-doc/quote/get-market-snapshot.html)。

## 验证

```sh
python3.14 -m unittest discover -s modules/put-screener/tests -v
python3.14 -I modules/put-screener/put_rules.py modules/put-screener/example.json \
  --output /tmp/synthetic-put-report.json
```

测试覆盖 Bid 估值、现金与损失公式、排序和并列、预算边界、硬规则、未知/跨期财报、过期/倒挂/陈旧报价、数据身份、规则指纹和隔离环境中的单文件执行。另覆盖均线、EMA 初值、Wilder RSI、ATR、急跌/单边下跌、历史数据缺口、半日收盘与避免使用未来日线。CI 使用合成数据，不登录 OpenD，不保存真实报价。
