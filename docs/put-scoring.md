# Put Top 10 与收益 / 风险评分

先执行用户启用的 Filter，随后对所有通过者评分、排序，严格返回当前排序的前10份合约。不为分散到期日跳过更高名次，也不为凑满数量自动放宽边界。`--top` 可改变 CLI 返回数量，桌面默认10。收益、低风险和综合三种排序共用同一个候选集合。

本版是 **可解释但尚未回测、校准的研究评分**，下面的权重和数值为原型参数，不是客观确定的风险或个人投资建议。风险分包括观测风险与缺失信息惩罚，不是亏损、行权或指派概率。

## 收益分

日均毛收益率（百分数值）= `100 × 每张Bid权利金 / 全额担保本金 / 剩余自然日`。本金为 `行权价 ×100股`。期限以输入 `session_date` 为基准，旧数据离线重算保留原始日期。

`收益分 = min(100, 100 × 日均毛收益率 / daily_return_target_pct)`

默认 `daily_return_target_pct=0.1`，即0.1%/天对应100分，0.05%/天对应50分。此处0.1是**百分数值**，不是10%。超过参考目标后收益分封顶，综合排序更重视风险差异；纯收益排序仍按未封顶的日均毛收益率比较。目标是可调尺度，不是可实现的收益承诺。使用固定尺度可避免因增加其他候选而改变一份合约的分数。

这是假设完整保留权利金的比较指标，尚未扣除费用，不是每天实际到账的盈利，也不是考虑亏损概率后的预期回报。

## 风险分

每项0–100，越高越危险。`clip(x)` 表示把数值限制在0–100。

| 维度 | 初始权重 | 计算与参数 |
| --- | ---: | --- |
| Delta 敏感度 | 25% | `clip(100 × abs_delta / delta_high)`，默认参考值0.5；不是指派概率 |
| 下跌情景亏损 | 25% | 到期股价下跌 `stress_drop_pct=20%`，算费用前净亏损占全额担保本金百分比，再用 `stress_loss_high_pct=20%` 映射满分；有盈利时本项为0 |
| 股票趋势 | 20% | `100 × 默认趋势参考未通过项数 / 参考项数`；当前为MA50位置/方向、20日破位、RSI、MACD五项。使用独立规则文件的参考条件，不随 Filter 开关变化 |
| 流动性 | 15% | `50% × 价差分 + 25% × 未平仓量不足分 + 25% × 买盘数量不足分` |
| 财报事件 | 15% | 财报在到期当天或之前为100分；到期后间隔≥`earnings_buffer_days=3`天为0分；中间线性变化 |

流动性子分：

- 价差分：`clip(100 × spread_pct_of_mid / spread_high_pct)`；参考价差15%。
- 未平仓量不足分：`clip(100 × (1 − open_interest / open_interest_target))`；参考目标200。
- 买盘数量不足分：`clip(100 × (1 − bid_size / bid_size_target))`；参考目标10张。盘口显示数量不保证成交。

缺少可验证趋势或下一次财报/完整日历时，该项使用 `unknown_risk_score`，初始100分，不将未知当成安全；同时保留 `known=false`、缺失维度和有数据支持的权重覆盖率。用户可修改该惩罚参数，相关未知状态仍保留。风险维度可设0权重；不允许所有风险权重为0。

`风险分 = Σ(维度分 × 维度权重) / Σ权重`

同一个股票的趋势分通常相同；不同到期日的财报分可能不同。Delta、情景亏损和趋势有相关性，不能当成独立风险相加的统计模型。仅在所选下跌情景没有亏损，不代表没有更严重下跌或其他风险。

## 综合分

`综合分 = return_weight × 收益分 + (1 − return_weight) × (100 − 风险分)`

`return_weight` 初始0.5，即收益、安全各占50%。例如收益分80、风险分30，综合分为 `0.5×80 + 0.5×70 = 75`。保守试算可将收益权重设0.3；重视收益可设0.7。权重是偏好，而不是通过数学推导得出的唯一答案。

不直接把原始日收益率和风险分相加，也不把收益率除以这个主观风险分当作统计意义的风险调整收益。三个分数同时保留，用户可以看到综合排名的取舍；没有额外评分淘汰门槛，只有 Filter 会排除合约。

## 使用与复现

```sh
./moomoo analyze input.json --rank-by return --output returns.json
./moomoo analyze input.json --rank-by risk --output lower-risk.json
./moomoo analyze input.json --rank-by balanced --top 10 --config scoring.json \
  --output balanced.json --csv-output balanced.csv
```

`--rank-by` 覆盖该次运行的排序，不修改配置文件或 Filter。桌面主界面可选择三种排序；「Filter / Sort 设置」的「收益 / 风险评分」页修改权重和尺度，已有数据会离线重算。

示例 `scoring.json`：

```json
{
  "scoring": {
    "weights": {"delta": 25, "stress_loss": 25, "trend": 20, "liquidity": 15, "earnings": 15},
    "parameters": {
      "stress_drop_pct": 20,
      "stress_loss_high_pct": 20,
      "daily_return_target_pct": 0.1,
      "return_weight": 0.5,
      "unknown_risk_score": 100
    }
  }
}
```

未指定参数继承规则文件的默认值。全部定义在独立 `modules/put-screener/put_rules.py` 的 `RISK_WEIGHTS` / `SCORING_PARAMETERS`。新增维度需要修改同一文件并提高版本。抓取层和 MCP 无须重写；它们仍只提供数据。

JSON 的 `recommendations` 严格对应 `ranked[:top_n]`；每项包含 `return_score`、`risk_score`、`composite_score`、三种独立排名和 `scoring.components` 的分数、权重、贡献、缺失状态及解释。`ranking_views` 提供三种预设排序的Top代码；完整候选仍在 `ranked`。`expiration_comparisons` 另存每个到期日的最优候选，不参与强制替换Top结果。CSV包含三种分数、情景亏损率、证据覆盖率和各风险子分。

输入、实际配置和引擎指纹保留。调整评分只改变分数/顺序，不改变 Filter 或原始采集时间。支持 `--budget` 的全额接股现金硬限制；未提供预算就标为未检查，不猜测个人账户资金。

## 当前边界与以后验证

模型未覆盖IV分位、Gamma/临近到期非线性、提前指派时机、新闻跳空、发行人财务、估值、组合相关性或账户集中度。到期情景也不是提前平仓的市值损失模型，不按不同期限调整发生概率。覆盖率只针对参与评分的维度，不是“已掌握全部风险”的比例。

下一步若要证明评分有用，需要历史期权快照及当时可用的日线/财报，避免未来数据；分训练与样本外区间，对比不同权重的实际净收益、亏损尾部、指派及资金占用。本版没有这些验证，不声称分数更高必然更值得投资。

指标含义来源：[OIC Delta](https://www.optionseducation.org/advancedconcepts/delta)、[OIC 现金担保Put](https://www.optionseducation.org/strategies/all-strategies/cash-secured-put)、[OIC 成交与流动性](https://www.optionseducation.org/referencelibrary/faq/trade-entry-execution)。这些资料支持基本概念和损益计算，不支持本项目自定的权重或阈值。
