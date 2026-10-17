# Agent 安装与使用指南

目标：以最少步骤把仓库安装为可验证的行情工具。macOS 日常入口是 `./setup.sh` 和 `./moomoo`，Windows 为 `setup.ps1` 和 `moomoo.ps1`，人类使用说明见 [README.md](README.md)。

## 1. 先检查，不重复安装

从实际仓库根目录检查：

```sh
pwd
git status --short
git branch --show-current
command -v uv
./setup.sh --help
./moomoo --help
```

保留现有修改和已经可用的环境。默认使用最新 `main`，确认当前分支有 `setup.sh`、`moomoo` 和 `apps/python/moopython/market_mcp.py`。开发分支保留用户已有工作，不为安装强制清空工作区或覆盖其他配置。

项目要求 Python `>=3.14,<3.15`。默认安装 CLI/MCP，桌面是可选功能。不修改系统 Python，不要求用户手动激活虚拟环境。以 `apps/python/pyproject.toml` 和 `requirements.txt` 为依赖依据，更新版本时同步检查构建依赖。

Windows 使用 PowerShell；不要把 Bash 脚本作为 Windows 原生入口。Windows 虚拟环境解释器为 `apps/python/.venv/Scripts/python.exe`，macOS 为 `.venv/bin/python`。

## 2. 安装

缺少 uv 时，Mac 可用 `brew install uv`；其他环境使用 [uv 官方安装说明](https://docs.astral.sh/uv/getting-started/installation/)。然后：

```sh
./setup.sh
```

Windows 缺少 uv 时用 `winget install --id=astral-sh.uv -e`，重开终端后运行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\setup.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\moomoo.ps1 doctor
```

使用局部子进程执行策略，不修改全局 PowerShell 策略。日常命令参数与 macOS 一致；Windows 桌面安装使用 `setup.ps1 -Desktop`。

脚本准备或复用 `apps/python/.venv`，由 uv 找到/下载 Python 3.14，并安装本项目及 MCP 依赖。优先复用已安装/缓存的依赖，缓存不足再联网。已有错误版本的虚拟环境会保留并报错，不自动删除重建。

用户需要图形界面时才运行 `./setup.sh --desktop`。普通抓取和 MCP 不需要 Qt。源码模块会安装为 editable，修改规则无需重新安装。

依赖失败时区分包源 DNS、证书和 HTTP 403，不把它误报成 OpenD 抓取失败。保留错误，不关闭 TLS 校验或输出凭据。已确认默认镜像不可用时，可显式使用官方 PyPI及系统证书：

```sh
uv --system-certs pip install --default-index https://pypi.org/simple \
  --python apps/python/.venv/bin/python -e './apps/python[mcp]'
```

若已安装主项目、SDK，仅缺 MCP 依赖，成功的 `Validate market data MCP` CI 提供 `mcp-dependencies-macos-arm64` artifact；确认 Apple Silicon / Python 3.14 匹配后，可下载到 `artifacts/mcp-dependencies` 并使用 `uv pip install --no-index --find-links ... 'mcp>=2.3,<3'`。它不是完整 SDK 安装包，Actions artifact 也会过期，不固定旧运行 ID。

## 3. OpenD 安装、登录和连接

先运行 `lsof -nP -iTCP:11111 -sTCP:LISTEN` 检查是否已有实例。复用运行且兼容的 OpenD，不终止用户进程、不启动多个副本。

没有 OpenD 时，从[官方 OpenAPI 下载页](https://www.moomoo.com/download/OpenAPI)下载对应平台的 **moomoo OpenD GUI** 并安装。以 `runtime/opend.json` 的版本、官方 URL 和哈希为可复现参考，不猜测升级下载地址。SDK 或普通交易客户端不代替 OpenD。

让用户在官方 OpenD 窗口登录并完成必要验证；密码和验证码不进入仓库、命令、MCP 配置或日志。已经登录时不重新要求登录。保持本机未加密 API `127.0.0.1:11111`，其他本机端口使用用户实际配置，不擅自开放远程访问。

源码安装脚本安装工具依赖，不自动安装/登录 OpenD；打包 MooPie 有单独的官方 OpenD 管理器。需要人工登录时，明确报告这一具体阻塞，并继续完成不依赖账号的验证。

## 4. 用 doctor 验证真实可用性

```sh
./moomoo doctor
# 用户使用其他端口/验证标的时：
./moomoo doctor --port 11111 --symbol AVGO
```

成功标准：Python 和三个包可定位，quote context 正常关闭，返回请求标的的有效价格及更新时间。失败时分别排查安装、OpenD 启动、登录、端口和权限。股票报价成功不等于期权或历史日线权限都可用；收盘后报价时间可能属于最近交易时段。

仅创建 quote context。安装和行情验证不需要交易解锁、交易上下文或下单。

## 5. 配置 MCP 宿主

当前服务是本仓库自建的 **`moomoo-market-data`**。协议库为官方 `mcp>=2.3,<3`，使用 `mcp.server.MCPServer`，传输为 stdio。共享抓取实现是 `market_collection.py`，通过官方 `moomoo-api` SDK 读取 OpenD。

只要求写文档时不修改用户宿主配置。用户要求实际接入 Codex 时，先检查同名配置，再添加/更新本服务，保留其他设置：

```sh
codex mcp list
codex mcp add moomoo-market-data -- "$(pwd -P)/moomoo" mcp
codex mcp get moomoo-market-data
```

Windows 注册使用绝对 `apps/python/.venv/Scripts/python.exe`，参数为 `-X utf8 -m moopython.market_mcp`，不要让 MCP 宿主直接执行 `.ps1`。对应完整命令见 README。

同名服务存在时先检查路径和参数，不盲目覆盖。可合并下面的 TOML 到 Codex `~/.codex/config.toml`，使用实际绝对路径；与 CLI 添加方式选一种：

```toml
[mcp_servers.moomoo-market-data]
command = "/ABSOLUTE/PATH/moomoo-clients/moomoo"
args = ["mcp"]
startup_timeout_sec = 20
tool_timeout_sec = 120
```

其他宿主的 JSON 示例见 README。使用绝对入口，从其他目录启动也能找到项目环境；宿主应与本机 OpenD 位于可互通的环境。远程/云端 agent 的 localhost 不等于用户 Mac。

重载 MCP 或新开会话后确认工具实际可见。配置记录、工具发现、真实行情调用分别验证，不互相替代。手动 `./moomoo mcp` 等待协议输入是正常状态；不把它当成 HTTP 服务或主动输出行情的命令，日志只写 stderr。

宿主还没加载工具时，可以通过官方 Python `Client` / `StdioServerParameters` 启动同一 stdio 服务验证；也可继续使用 CLI/Python 接口。说明实际调用路径，不声称不可见的宿主工具已加载。

## 6. 实际调用和日常使用

确认四个工具：

| 工具 | 最小参数示例 |
| --- | --- |
| `get_market_snapshots` | `{"codes":["US.AVGO"]}` |
| `get_daily_bars` | `{"symbols":["AVGO"]}` |
| `get_option_chain` | `{"symbol":"AVGO","months":1,"option_type":"PUT"}` |
| `get_earnings_calendar` | 今天起不超过七个自然日的 start/end |

先做小批量请求。股票、期权、日线权限分别检查，保留 `missing_codes`、`error` 和数据时间。当前 MCP/综合采集/Put 分析支持 US，原始 `options` 命令另支持 HK。

完整研究流程：

```sh
./moomoo collect AVGO NVDA AAPL --months 3 --output artifacts/put-screen/input.json
./moomoo analyze artifacts/put-screen/input.json \
  --output artifacts/put-screen/ranking.json --csv-output artifacts/put-screen/ranking.csv
```

支持用户指定标的，不写死 AVGO。分析规则保留在独立 `modules/put-screener/put_rules.py`，修改 `TREND_RULES` / `RULES` / `SORT_ORDER` 后更新规则版本，对同一输入重跑。抓取、协议、分析和以后可能添加的存储层保持分离。

趋势分析报告数据日期/时区、考察期限、指标值、关键价位和改判条件；只使用已完成日线，不把规则命中数当成经过校准的涨跌概率。Put 结果查看 `ranked`、财报未验证观察名单、`failed_rules`、预算及快照时间。空结果保留，不为产生候选自动放宽规则；未知财报不推断成无财报。

Filter 与 Sort 分离：日常 CLI/桌面调用独立文件的 `recommend(dataset, budget=None, configuration=None, top_n=10)`。主界面Top数量可选5/10/20，默认10，在完整候选排序后截取，不限制采集范围。预设支持 `duration`（到期时长升序）、`cost`（行权价×100的担保现金升序）、`return`（日均毛收益率降序）、`risk`（风险分升序）、`balanced`（综合分降序），也可自定义。严格返回 `ranked[:top_n]`，不足所选数量返回实际数量，不按到期日替换更高排名者。`ranking_views` 提供五种预设的Top代码。切换数量/排序通过 `research_cli --input --top` 离线重算完整缓存；GUI数量偏好独立保存在 `put_top_n`。日期、天数、行权价、成本及评分都由引擎返回。

评分只在 `put_rules.py` 的 `RISK_WEIGHTS` / `SCORING_PARAMETERS` 及函数中维护，初版Delta/情景亏损/趋势/流动性/财报权重25/25/20/15/15，参考情景下跌20%。风险分含缺失信息惩罚（默认100），不是亏损概率。收益分用固定日均参考目标0.1%映射0–100，综合分为 `return_weight×收益分+(1−return_weight)×(100−风险分)`，初始0.5。全部都是未校准原型参数。可选 `min-cost` / `max-cost` / `min-daily-return` / `max-risk` / `expiry-before` 默认关闭，启用后在完整数据上先评分、再过滤、最后排序取Top。比较为严格 `>` / `<`，成本美元、日均收益百分数值、风险0–100；日期阈值为ISO日期，不包含当天。修改评分不改变Filter配置或采集时间，但启用风险分过滤时可能改变候选集合。关闭Filter不取消该项风险分，趋势评分仍使用默认参考条件。详见 [docs/put-scoring.md](docs/put-scoring.md)。

`RECOMMENDATION_BOUNDARIES` 为未校准的示例预设：7–90天、价外幅度≥0、绝对Delta≤0.30、Bid≥0.10、买盘数量≥1、价差≤15%、同交易日报价，及标准合约/未停牌。个人风险范围未确认，不将示例阈值当成用户认可；预算未提供必须标记。趋势/财报/最低Delta/成交量/未平仓量默认不拦截，可通过 `--config` 显式启用为硬限制。基础有效性检查始终执行；任何已启用边界不可因高收益或结果为空而自动越过。`scan()` / `--scan-only` 保留原全条件扫描，调用时说明两者默认配置不同。`filter_impact` / `relaxation_preview` 只模拟数量。

新版 GUI 用独立设置键 `put_recommendation_configuration_v1`，保留旧设置且不自动继承旧全条件配置。已有新版配置继续复用，不随意重置用户选择。恢复默认 Filter 使用 `recommendation_configuration()`。趋势描述与风险提示不随过滤开关消失。

桌面配置界面在 `research_controls.py`，不是第二套规则。修改配置后优先通过研究子进程的 `--input` 离线重算现有 `input_dataset`，保持原始 `collected_at`；点击主抓取按钮才刷新。股票/端口改变后丢弃缓存；导出包含数据、实际配置和证据。日线抓取失败需保留期权数据和明确错误：启用趋势 Filter 时阻止候选，用户关闭后可继续其他过滤。

原始行情和分析结果写 gitignored 的 `artifacts/`。不提交账号、真实行情和本机绝对配置。数据库和旧数据清理优先级较低，基础安装时不添加数据库、定时任务或新的后台常驻服务。

## 7. 验证与交付

```sh
PYTHONPATH=apps/python apps/python/.venv/bin/python -m unittest discover -s apps/python/tests/unit -v
apps/python/.venv/bin/python -m unittest discover -s modules/put-screener/tests -v
PYTHONPATH=apps/python apps/python/.venv/bin/python -m unittest discover -s apps/python/tests/mcp -v
```

跨平台工作流 `.github/workflows/client-platforms.yml` 必须同时跑 Windows 和 macOS 安装、命令、MCP、规则、独立 wheel 和研究界面测试。Windows 使用 PowerShell 真正执行，macOS 用 Bash；Windows 专项测试验证带空格路径、退出码与保留不完整环境。Windows 构建便携 EXE ZIP 并验证启动与 JSON 错误协议；macOS 打包工作流负责 DMG。不要把 wheel 或便携 ZIP 称作安装向导。

桌面默认是 `research_ui.py`：一个股票输入框，筛选 Put / 分析走势两个按钮。通过 `QProcess` 运行 `research_cli.py`，后者调用 `research.py` 和共享抓取服务，SDK 在子进程主线程运行。窗口关闭/取消会停止子进程。冻结的 windowed EXE 通过临时 JSON 文件返回结果，不依赖 stdout；不要改为 GUI 线程直接请求 SDK。真实失败保留为空，不填演示报价。

规则、阈值、排序和趋势解释仍只维护 `modules/put-screener/put_rules.py`。`setup.py` 仅在 wheel/sdist 构建时拷贝快照，PyInstaller 同样包含该文件。源码总是优先读取独立文件；修改分发包规则要重新构建。不要手动维护第二套规则。运行研究界面测试：`PYTHONPATH=apps/python QT_QPA_PLATFORM=offscreen apps/python/.venv/bin/python -m unittest discover -s apps/python/tests/integration -p test_research_ui.py -v`。

协议测试使用合成 provider，不证明个人行情权限；`doctor` 和实际调用验证真实 OpenD。行为修改运行相应测试，文档修改检查链接和示例命令。完整 DMG 在 CI 构建，本地做必要测试和 wheel 验证即可。

开发迭代先集中修改并做本地验证。用户要求暂不触发CI时，不通过推送或手动运行工作流触发CI；保留本地可审查的结果，按用户的批次安排交付。

交付时说明安装、OpenD 登录、doctor、MCP 宿主配置/发现/真实调用分别完成到哪里，保留未解决错误。不要把等待输入或下载失败说成成功。延续用户授权推进工作，不反复询问已确认事项；不自动合并 PR 或发布 Release。

需要推送而 macOS 钥匙串 helper 卡住时，已登录 `gh` 的情况下可仅对本次 push 使用 `git -c credential.helper= -c 'credential.helper=!gh auth git-credential' push`，不打印 token，不覆盖全局 Git 设置。

参考：[数据接口](docs/market-data.md)、[独立规则](modules/put-screener/README.md)、[官方 Codex MCP](https://developers.openai.com/codex/mcp/)、[Codex AGENTS.md](https://developers.openai.com/codex/guides/agents-md/)、[官方 MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)。
