# Agent 工作流

先读根目录 [agent.md](../../agent.md)。本页把一次任务拆为检查、执行、解析和交付，命令参数见 [CLI 参考](../reference/cli.md)。

## 1. 建立环境状态

在仓库根目录执行：

```sh
git status --short
git branch --show-current
./moomoo --help
```

检查项目解释器是否存在，再决定是否运行安装脚本。复用已登录 OpenD，不清理用户修改或启动重复实例。Windows 使用 [PowerShell 入口](../getting-started/installation.md)。

需要真实行情时执行 `./moomoo doctor`。需要 MCP 时检查宿主配置、工具发现、真实调用三个阶段；记录实际完成到哪里。`doctor` 成功与 MCP 配置存在都不能代替工具调用成功。

## 2. 按任务选择入口

| 请求 | 执行流程 |
| --- | --- |
| 某股票未来三个月行权价 | `options SYMBOL --months 3 --type PUT`，返回挂牌信息 |
| 找值得研究的卖 Put | `collect` 保存完整输入，再 `analyze` 应用明确的 Filter / Sort |
| 调整阈值、评分或 Top 数量 | 对同一原始输入离线重算，保留原采集时间 |
| 判断趋势 | 研究 CLI 的 `trend` 动作，或 MCP 日线工具加独立规则 |
| 接入 agent 宿主 | 按 [MCP 指南](mcp-server.md)注册本地 stdio 服务 |

MCP 目前只暴露四个行情工具，没有分析或自动选合约工具。完整 Put 采集通常优先保存为文件，避免把几千条快照直接灌入对话。

## 3. 执行可重放的研究

```sh
./moomoo collect AVGO --months 3 --output artifacts/agent/input.json
./moomoo analyze artifacts/agent/input.json --rank-by risk --top 10 \
  --output artifacts/agent/ranking.json
```

先检查退出码，再按[输出结构](../reference/output-schemas.md)读取文件。不同入口的 stdout / stderr 和错误格式不同，不能假定所有命令都输出 JSON。

Python 调用采集和分析入口时，可以使用文件边界：

```python
import json
import subprocess
from pathlib import Path

repo = Path.cwd()  # 必须是实际仓库根目录
report_path = repo / 'artifacts/agent/ranking.json'
subprocess.run([
    str(repo / 'moomoo'), 'analyze', 'artifacts/agent/input.json',
    '--rank-by', 'risk', '--top', '10', '--output', str(report_path),
], cwd=repo, check=True)
report = json.loads(report_path.read_text(encoding='utf-8'))
recommendations = report['recommendations']
```

这个示例使用 macOS 入口。Windows 的 subprocess 参数应以 `powershell.exe -NoProfile -ExecutionPolicy Bypass -File` 加绝对 `moomoo.ps1` 路径开头。

## 4. 解释结果

Put 说明当前配置下的排序依据、日期、担保成本、日均毛收益率、风险分和主要未知项。没有预算就说明未检查个人资金。风险分来自可修改的研究模型，不是概率。没有合格候选时报告实际原因，不自动改阈值。

趋势说明使用哪天的已完成日线、MA / RSI / MACD 等证据、关键价位和改变结论的条件。只描述数据支持的条件判断，不把规则命中数换算为涨跌概率。

## 5. 修改与交付

修改策略只编辑独立 `put_rules.py`，更新规则版本和相关说明；修改界面只传配置，不复制公式。使用同一输入比较修改前后结果，按[测试指南](functional-testing.md)选择必要检查。

交付说明实际改动、验证结果、数据时点和未解决问题。开发批次先完成本地改动和验证；按用户安排推送、运行 CI 或发布。原始行情与本机配置放在忽略目录，不随文档或代码提交。
