# 文档导航

第一次使用按安装、连接、查询的顺序阅读；已经能运行时，直接选择任务指南。所有命令从仓库根目录执行，股票代码只是示例。

## 开始使用

| 文档 | 解决的问题 |
| --- | --- |
| [安装与 OpenD](getting-started/installation.md) | macOS / Windows 安装、登录和连接验证 |
| [快速上手](getting-started/quickstart.md) | 打开界面，或完成一次采集和离线分析 |

## 按任务操作

| 文档 | 解决的问题 |
| --- | --- |
| [Agent 工作流](guides/agent-workflows.md) | agent 如何检查环境、调用工具、解析结果并交付 |
| [筛选卖出 Put](guides/put-screening.md) | 先 Filter、再 Sort、最后取 Top 5/10/20 |
| [分析股票趋势](guides/trend-analysis.md) | 获取已完成日线，解释走势证据和改判条件 |
| [配置 MCP](guides/mcp-server.md) | 接入本地 stdio 服务，分别验证配置、发现和调用 |
| [测试与真实行情验证](guides/functional-testing.md) | 哪些检查离线运行，哪些需要已登录 OpenD |
| [GitHub、CI 与交付](guides/github-workflows.md) | 本地批量开发、检查 PR、区分构建和发布 |
| [排查问题](guides/troubleshooting.md) | 安装失败、连接失败、空结果、旧数据和打包问题 |

## 查参数与实现

| 文档 | 内容 |
| --- | --- |
| [CLI 参考](reference/cli.md) | 实际命令、参数、输出位置与退出码 |
| [配置参考](reference/configuration.md) | Filter / Sort / 评分、端口、桌面设置和构建版本 |
| [输出结构](reference/output-schemas.md) | 原始数据、分析报告、研究包装结果与错误 |
| [架构与扩展位置](reference/architecture.md) | 抓取、规则、MCP、界面、存储如何分工 |
| [抓取 Python API 与数据时点](market-data.md) | 共享基础接口、限流及未来存储约定 |
| [收益 / 风险评分公式](put-scoring.md) | 各维度、权重、单位、组合分及模型边界 |
| [独立规则文件](../modules/put-screener/README.md) | 默认条件、完整计算和单文件运行 |

## 修改仓库或文档

- [贡献与文档写法](contributing/README.md)：修改位置、验证范围和文档维护约定。
- [任务指南模板](contributing/templates/how-to.md)、[接口参考模板](contributing/templates/reference.md)、[故障排查模板](contributing/templates/troubleshooting.md)、[变更说明模板](contributing/templates/change-notes.md)。
- [agent.md](../agent.md) 是 agent 的约束与安装入口，[README](../README.md) 是用户入口。

任务指南中的步骤说明当前已实现的操作；数据库、自动清理等后续设想会明确标为未实现。现有规则与评分文档保留为详细依据，其他页面通过链接引用，避免维护多套公式。
