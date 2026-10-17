# 筛选卖出 Put

目标是在明确的硬边界内，返回当前排序下的 Top 5/10/20。候选不足时返回实际数量；结果为空时解释原因。

## 1. 先确定边界和排序

Filter 决定可接受的范围，Sort 决定范围内的顺序。推荐模式的基础示例边界为7–90天、行权价不高于股价、绝对 Delta≤0.30、Bid≥$0.10、买盘数量≥1、价差≤15%、同交易日报价。标准100股、未停牌及必要数据校验始终执行。

趋势、财报、最低 Delta、成交量和未平仓量默认提供证据或风险提示，可以显式启用为硬限制。上述阈值是未校准研究预设；个人预算和可接受风险需要另行指定。

| 排序值 | 优先返回 |
| --- | --- |
| `duration` | 距离到期自然日更少的合约 |
| `cost` | 行权价×100的担保现金更少的合约 |
| `return` | 日均权利金毛收益率更高的合约 |
| `risk` | 当前模型风险分更低的合约 |
| `balanced` | 当前收益与风险综合分更高的合约 |

详细阈值、并列规则和公式见[独立规则说明](../../modules/put-screener/README.md)及[评分说明](../put-scoring.md)。

## 2. 完整抓取，再分析

```sh
./moomoo collect AVGO --months 3 --output artifacts/put-screen/input.json
./moomoo analyze artifacts/put-screen/input.json --rank-by return --top 10 \
  --output artifacts/put-screen/return.json
./moomoo analyze artifacts/put-screen/input.json --rank-by risk --top 10 \
  --output artifacts/put-screen/risk.json
```

两份报告使用同一份输入和 Filter，便于比较不同排序。Top 数量只限制最终输出，不把采集或过滤范围缩成前10份。桌面 / 研究入口每股有界选 Top 20，再归并全局 Top N；`recommendations` 对应所保留 `ranked` 的前 N 项，不为分散到期日替换更高排名者。独立默认报告仍提供完整排序。

## 3. 添加自己的范围

把以下示例保存为 `artifacts/put-screen/filters.json`：

```json
{
  "schema": 1,
  "filters": {
    "min-cost": {"enabled": true, "threshold": 10000},
    "max-cost": {"enabled": true, "threshold": 40000},
    "min-daily-return": {"enabled": true, "threshold": 0.03},
    "max-risk": {"enabled": true, "threshold": 75},
    "expiry-before": {"enabled": true, "threshold": "2026-12-01"}
  }
}
```

日期按实际需求填写；示例门槛不代表个人风险建议。成本比较为严格 `>` / `<`，收益0.03代表0.03%/天，日期截止不包含当天。

```sh
./moomoo analyze artifacts/put-screen/input.json \
  --config artifacts/put-screen/filters.json --rank-by balanced --top 10 \
  --output artifacts/put-screen/filtered.json
```

引擎先计算必要指标与分数，再检查全部已启用 Filter，最后排序取 Top。若启用 `max-risk`，修改评分参数也可能改变候选集合。未指定配置项继承推荐基础预设。

## 4. 审查结果或空结果

检查 `best_recommendation`、`recommendations`、各项 `reasons` / `tradeoffs` / `risk_notes` 和到期情景。日均毛收益是 Bid 权利金÷全额担保本金÷自然日，假设完整保留权利金，未扣费用；它不是每天实际到账或预期净收益。

无结果时看 `results[].failed_rules`、`filter_impact`、`relaxation_preview`。预览只说明改变条件后的数量，不自动应用；各项排除数可能重叠。财报未知不等于没有财报。

桌面「候选列表」使用原生 Qt 表格；Top 数量和排序选择在主界面，也可以点击各数据列表头切换升降序。股票按字母、日期按日历顺序、数值按大小排序；财报日期缺失时始终排末尾，未验证提示保留。每次都对完整缓存重排后取Top；表格不会只排序已显示的几行。选中合约后点击「查看所选合约」或双击行，在「合约详情 / 筛选依据」查看对应证据；趋势结果在「走势分析」页签。

已有结果时，在「Filter / 评分设置」修改并应用，会对完整缓存离线重算。主查询按钮盘中抓取保存、盘后读取 SQLite；主动点击「更新行情」可在盘后更新。切换股票或端口会丢弃界面输入，数据库历史仍保留。完整输出见[结构参考](../reference/output-schemas.md)，缓存策略见[数据库说明](database.md)。

`--scan-only` 是旧的全条件严格扫描，默认条件与日常推荐不同；只有需要该模式时才显式使用。
