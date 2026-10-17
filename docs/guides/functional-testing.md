# 测试与真实行情验证

根据改动选择检查。合成测试验证代码行为，真实 OpenD 检查验证本机连接和个人数据权限，两者分别记录。

## 离线与本地模拟检查

| 改动 | 检查入口 | 能证明什么 |
| --- | --- | --- |
| Put 条件、排序、指标、评分 | `modules/put-screener/tests` | 同一输入的公式、边界、证据与顺序 |
| 抓取标准化与研究组合 | `apps/python/tests/unit` | 数据处理、错误保留、研究与配置行为 |
| MCP 适配 | `apps/python/tests/mcp` | 真正的 stdio 发现/调用，使用合成 provider |
| UI 或官方 SDK 交互 | `apps/python/tests/integration` | 本地合成 peer 与界面交互，不使用个人账号 |
| 安装入口 | `tests/unit/test_setup_*.py` | 环境保留、命令转发和平台入口 |
| 文档 | 相对链接、参数 `--help`、离线示例 | 页面能导航，示例符合当前程序 |

在已安装的项目环境执行必要检查：

```sh
apps/python/.venv/bin/python -m unittest discover -s modules/put-screener/tests -v
PYTHONPATH=apps/python apps/python/.venv/bin/python -m unittest discover -s apps/python/tests/unit -v
PYTHONPATH=apps/python apps/python/.venv/bin/python -m unittest discover -s apps/python/tests/mcp -v
PYTHONPATH=apps/python QT_QPA_PLATFORM=offscreen apps/python/.venv/bin/python \
  -m unittest discover -s apps/python/tests/integration -p test_research_ui.py -v
```

最后一项需要桌面依赖。Windows 使用项目解释器 `apps/python/.venv/Scripts/python.exe`；环境变量通过 `$env:PYTHONPATH='apps/python'`、`$env:QT_QPA_PLATFORM='offscreen'` 设置后执行对应命令。

测试路径的名称不能代替检查内容：MCP 协议测试实际启动子进程，但 provider 是合成数据；SDK 集成测试与本地 protobuf peer 通信，也不能证明真实账号有行情权限。

## 离线端到端示例

```sh
./moomoo analyze modules/put-screener/example.json --top 5 --rank-by return \
  --output artifacts/validation/report.json --csv-output artifacts/validation/report.csv
```

检查 `recommendations` 对应 `ranked` 前 N 项，报告保留输入日期和实际配置。规则修改后使用同一输入比较前后行为，避免把行情变化误认为规则效果。

## 真实只读验证

已有官方 OpenD 且已登录时，按需验证：

1. `./moomoo doctor --symbol AVGO` 检查股票报价和连接关闭。
2. `./moomoo options AVGO --months 1 --type PUT` 检查期权挂牌数据。
3. 研究 CLI 的 `trend AVGO` 检查已完成历史日线。
4. 需要完整 Put 验证时执行 `collect`，检查缺失报价与日历错误，再离线分析。
5. 需要宿主接入时，在宿主中调用小批量 MCP 工具。

记录真实数据的日期、权限错误和完成范围。验证只创建行情上下文，不解锁交易或下单；结果放在忽略的 `artifacts/`，不提交真实行情。

## 构建验证

Windows 与 macOS 由[跨平台 CI](../../.github/workflows/client-platforms.yml)分别检查安装、命令、MCP、规则、独立 wheel 和研究界面；Windows 另检查便携 EXE。DMG 在[macOS 打包工作流](../../.github/workflows/package-python.yml)构建。

本地完成必要检查即可，完整 DMG 留给 CI。用户要求先集中修改时，不通过 push 或手动 workflow 触发 CI。仅文档改动通常不需要重跑全部测试。
