# 独立卖 Put 规则文件

规则、阈值、计算、排序和 JSON/CSV 输出都在 **`put_rules.py`**。这是单个独立 Python 文件，只依赖标准库，直接复制它即可运行；无需安装 Qt、moomoo SDK 或 `modules/rule-engine`。开发和 CI 使用 Python 3.14。

后续修改时，编辑文件顶部的 `RULES`、`SORT_ORDER`，提高 `RULESET_VERSION`，然后对相同输入重新运行。新增计算指标时，在同一个文件的 `metrics()` 和 `METRICS` 中添加。所有规则都是硬条件，不能通过其他指标的高分抵消。报告记录规则指纹、整个引擎文件指纹和输入数据指纹，便于比较不同版本。

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

`scripts/collect-put-data.py` 只采集数据，不排序：查询未来三个月全部挂牌 Put，补充 Bid/Ask、Delta、IV、成交量、未平仓量和财报日历。支持 `--months` 和 `--port`。当前筛选器只支持美元计价的标准美股/ETF Put，读取 SDK 报价，不查询账户或执行订单。缺失报价在 `missing_quote_codes` 中列出；财报日历失败在 `calendar_errors` 中列出，不填造数据。

把上面的 `input.json` 交给规则文件即可独立重跑，修改规则无需再次联网，也无需重新打包客户端。单独复制引擎文件时，输入字段参考 `example.json`；该示例完全是合成数据。

## 初版条件与排序

假设为现金担保卖 Put，并愿意接受指派后持股。尚未确认个人适合程度、估值和组合集中度。

| 条件 | 初始阈值 |
| --- | --- |
| 合约 | 标准 100 股、未停牌、合约表与快照标的/日期/行权价/股数一致 |
| 数据 | 正数且未倒挂的 Bid/Ask；快照属于最新交易日；Put Delta 合法 |
| 期限 | 21–60 个自然日 |
| 价外空间 | `(股价−行权价)÷股价 ≥5%` |
| Delta | 绝对值 0.15–0.30 |
| 买盘 | Bid ≥$0.10、买盘数量 ≥1 |
| 流动性 | 未平仓量 ≥200、当日成交量 ≥10 |
| 价差 | `(Ask−Bid)÷((Ask+Bid)/2) ≤15%` |
| 财报 | 数据源列出下一次财报，且合约至少提前 3 个自然日到期 |
| 预算 | 可选：行权价×100 不超过传入预算；未提供时明确标记未检查 |

通过所有条件后，按 `Bid÷行权价×365÷剩余天数` 从高到低排序；并列时优先较小的相对价差、较低的绝对 Delta，最后按合约代码固定顺序。这是满足阈值后的简单年化毛权利金比较，未做回测，不代表最优策略、预期收益或可重复年化收益。

期限和年化统一以输入的 `session_date` 为报价基准日。周末重跑上一个交易日的输入，得到的仍是该交易日的研究排名。

每份合约的计算：

- 权利金毛收入 / 最大期权收益：`Bid×股数`，使用买方报价估算，不能保证成交。
- 现金担保：`行权价×股数`，不以券商杠杆保证金代替。
- 到期盈亏平衡价：`行权价−Bid`。
- 最大损失：`(行权价−Bid)×股数`，对应股票价值降至零。
- 股价下跌 20% 时到期损益：`Bid×股数−max(行权价−当前股价×0.8, 0)×股数`。

全部金额和回报均未扣手续费、滑点、税费，也未计入现金利息。Delta 是敏感度，不能当作精确指派概率。`iv_pct` 只展示当时 IV，未计算 IV Rank 或历史分位，也未把高 IV 自动视为卖出优势。

## 合格与待确认名单

`ranked` 只包含所有条件通过的合约。财报未知时，合约保持 `eligible=false`；如果其余报价和风险规则全部通过，则单独进入 `earnings_unverified_watchlist`。已知财报会跨越合约期限的合约不会进入该名单。CSV 通过 `category` 明确区分这两种结果。

财报来自 moomoo 日历，不表示发行人已经确认。未列出日期属于未知，不能推断无财报；即使日历列出日期，交易前仍应核对最新公告。当前采集结果若在收盘后获取，排序仅用于研究；`live_review_ready` 只有在常规市场开放且快照时间未超过 15 分钟时才可能为 true。快照更新时间也不能保证 Bid 的真实时效，该标志不表示可以自动下单。

原始采集 JSON、全部规则证据和每个排除原因都保留。规则引擎本身不联网，不含订单 API，不修改输入或自动调整阈值。

计算依据：[OIC 现金担保 Put](https://www.optionseducation.org/strategies/all-strategies/cash-secured-put)。字段依据：[moomoo 市场快照](https://openapi.moomoo.com/moomoo-api-doc/quote/get-market-snapshot.html)。

## 验证

```sh
python3.14 -m unittest discover -s modules/put-screener/tests -v
python3.14 -I modules/put-screener/put_rules.py modules/put-screener/example.json \
  --output /tmp/synthetic-put-report.json
```

测试覆盖 Bid 估值、现金与损失公式、排序和并列、预算边界、硬规则、未知/跨期财报、过期/倒挂/陈旧报价、数据身份、规则指纹和隔离环境中的单文件执行。CI 使用合成数据，不登录 OpenD，不保存真实报价。
