# 卖出 Put 的持仓效率

在「分析 → 推荐与候选」右上角点「持仓效率」。可以先选一行合约，工具会带入行权价、到期日、Ask参考回购价和报价所属交易日。开仓日期与开仓权利金必须手动填写，不从候选表推断持仓。没有选中合约时也能手动计算。

当前版本是独立的收益 / 时间指标，忽略风险、费用、利息，采用自然日和固定现金担保本金 `行权价 × 100`。价格输入是每股，按一张标准100股Put计算；保留率与合约数量无关。它不读取真实交易持仓、不改变当前Filter / Put排名，也不下单。手动开仓信息只用于本次窗口，尚不保存为持仓记录。

设开仓权利金为P，当前回购价为B，原始期限为T，剩余天数为D，行权价为K：

```text
开仓最大日均收益率 = P / K / T × 100%
剩余最大日均收益率 = B / K / D × 100%
效率保留率 E = (B / D) / (P / T) × 100%
             = 剩余利润比例 / 剩余时间比例 × 100%
```

本金保持不变才可以在E中约掉；这里不使用随行情变化的融资保证金。

| E | 相对开仓效率的含义 |
| --- | --- |
| >100% | 剩余效率高于开仓时 |
| =100% | 效率与开仓时持平 |
| <100% | 剩余效率下降；不直接等于应当平仓 |

100%是计算基准，不是策略退出阈值。按后续模拟盘的需求，阈值作为独立参数 `exit_threshold_pct` 传入；只在E严格低于它时生成评估买回平仓提示，等于阈值不触发。80%目前只是待测试候选，没有认定为最优值。默认不设置阈值，仅观察指标；不会默认自动平仓。

例如同一个E=80%的盈利仓位：设置60%阈值时不触发，设置80%也不触发，设置100%则触发。未来模拟盘应在每个实验创建时冻结参数，比较不同阈值，而不是随全局界面偏好改变已有实验。

例如90天期权收取每股$10，持有30天后回购价$2：已获利80%，还剩60天，E=30%。如果同样的回购价是在持有85天后出现，E=360%。它可以超过100%，不能当成被限制在0–100的评分。

保留率仅表示相对开仓时的效率变化，不是已验证的最优退出策略，也没有比较当前其他投资机会。未盈利、开仓当天或已经到期，分别显示不适用原因，不因E偏高而鼓励继续持有亏损仓位；剩余天数为0时不计算比率。当前股票模拟器尚未接入Put持仓或此退出条件，配置参数只是为后续模拟盘提供可复用接口。

使用Ask只是保守的回购参考，不能用卖出时的Bid冒充平仓成本。数据日期保持原始报价交易日；需要当前判断时先更新行情并核对实际可成交价格。该指标比较的是持有到期的最大收益上限，不是预期收益，也不等于其他定价因素不变时的Theta。[OIC对Theta的解释](https://www.optionseducation.org/advancedconcepts/theta)

计算模块无Qt、SDK或数据库依赖，可以单独复用：

```python
from moopython.position_efficiency import put_efficiency

result = put_efficiency(
    opening_premium=10, buyback_price=2, strike=100,
    opened_on="2026-09-17", expires_on="2026-12-16", as_of="2026-10-17",
)
assert abs(result["retention_pct"] - 30) < 1e-9
assert result["signal"] == "observe"  # 未指定退出阈值

# 以下80%是实验参数示例，不是已验证的推荐值。
experiment = put_efficiency(
    opening_premium=10, buyback_price=2, strike=100,
    opened_on="2026-09-17", expires_on="2026-12-16", as_of="2026-10-17",
    exit_threshold_pct=80,
)
assert experiment["exit_triggered"] is True
assert experiment["suggested_action"] == "buy_to_close"
```

结果包含版本、输入、日期、原始 / 剩余天数、已获利比例、两种最大日均收益率、保留率、假设和提示。`configuration.exit_threshold_pct`保留本次实验参数；未配置或不适用时 `exit_triggered=null`、`suggested_action=null`。已配置且适用时exit_triggered为布尔值，触发时action为buy_to_close；这些字段仅表达信号，不执行交易。日期、金额或阈值不合法时抛出ValueError。公式只在 `position_efficiency.py` 维护，Qt窗口仅负责展示。
