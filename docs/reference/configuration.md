# 配置参考

项目目前有 Python 依赖、OpenD 连接、分析 JSON 和桌面偏好几类配置，没有统一的数据库或后台任务配置。

## 运行环境

| 配置 | 依据 / 入口 |
| --- | --- |
| Python 版本 | [pyproject.toml](../../apps/python/pyproject.toml)，`>=3.14,<3.15` |
| SDK 版本 | [requirements.txt](../../apps/python/requirements.txt) |
| 可选依赖 | pyproject 的 `mcp`、`desktop` extras；安装脚本默认包含 MCP |
| OpenD 构建参考 | [opend.json](../../runtime/opend.json) 的官方版本、URL、哈希 |
| OpenD 连接 | 本机 `127.0.0.1:11111`；CLI 可传 `--port` |
| MCP 宿主 | 绝对程序路径和参数，见 [MCP 指南](../guides/mcp-server.md) |

Python SDK 不包含 OpenD 登录状态；配置中不需要保存密码或验证码。

## 分析 JSON

`./moomoo analyze INPUT --config CONFIG --output REPORT` 接受以下结构。省略字段继承本次模式的默认值：日常推荐使用基础预设，`--scan-only` 使用旧严格预设。

```json
{
  "schema": 1,
  "filters": {
    "max-cost": {"enabled": true, "threshold": 30000},
    "underlying-trend": {"enabled": false}
  },
  "trend_filters": {
    "rsi-floor": {"enabled": true, "threshold": 40}
  },
  "sort_order": [["daily_gross_return_pct", "desc"], ["risk_score", "asc"]],
  "scoring": {
    "weights": {"delta": 25, "stress_loss": 25, "trend": 20, "liquidity": 15, "earnings": 15},
    "parameters": {"stress_drop_pct": 20, "daily_return_target_pct": 0.1, "return_weight": 0.5}
  }
}
```

这是格式示例。`trend_filters` 只有在总 Filter `underlying-trend` 启用时才作为硬限制；趋势描述和风险参考继续存在。

| 字段 | 约定 |
| --- | --- |
| `schema` | 当前为整数1 |
| `filters` | 按规则 ID 设置 `enabled` 布尔值和可选 `threshold` |
| `trend_filters` | 按趋势规则 ID 设置子条件 |
| `sort_order` | 按先后顺序比较，方向 `asc` / `desc`，指标不能重复 |
| `scoring.weights` | 五个维度各0–100，至少一个大于0；按权重总和归一化 |
| `scoring.parameters` | 指定已支持参数，其余继承默认尺度 |

完整规则 ID、可排序指标和参数范围以 [put_rules.py](../../modules/put-screener/put_rules.py) 的 `RULES`、`TREND_RULES`、`SORTABLE_METRICS`、`SCORING_PARAMETERS` 为准。未知字段、重复排序、不合法日期和冲突上下限会报错；标准合约等必需检查不能禁用。

范围 Filter 的单位和严格边界见 [Put 筛选](../guides/put-screening.md)，评分参数与公式见[评分说明](../put-scoring.md)。`--rank-by` 覆盖本次 `sort_order`，不改文件。

## 桌面偏好与缓存

桌面使用系统 QSettings 保存 `put_recommendation_configuration_v1` 和 `put_top_n` 等偏好。新推荐配置不会自动继承旧的全条件严格配置，也不删除旧记录。

修改设置或切换 Top 数量时，复用当前完整 `input_dataset` 离线重算；刷新主按钮才重新抓取。股票或端口改变后清空缓存。导出保留原始时间和实际配置，偏好文件不能代替行情缓存。

规则默认值只在独立文件维护；源码修改立即生效，wheel / 桌面包需要重新构建。源码加载顺序见[架构](architecture.md)。
