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

保留现有修改和已经可用的环境。功能尚未合并主线时，确认当前分支有 `setup.sh`、`moomoo` 和 `apps/python/moopython/market_mcp.py`；当前安装简化分支为 `codex/simple-setup`。不要为安装强制清空工作区或覆盖其他配置。

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

原始行情和分析结果写 gitignored 的 `artifacts/`。不提交账号、真实行情和本机绝对配置。数据库和旧数据清理优先级较低，基础安装时不添加数据库、定时任务或新的后台常驻服务。

## 7. 验证与交付

```sh
PYTHONPATH=apps/python apps/python/.venv/bin/python -m unittest discover -s apps/python/tests/unit -v
apps/python/.venv/bin/python -m unittest discover -s modules/put-screener/tests -v
PYTHONPATH=apps/python apps/python/.venv/bin/python -m unittest discover -s apps/python/tests/mcp -v
```

跨平台工作流 `.github/workflows/client-platforms.yml` 必须同时跑 Windows 和 macOS 安装、命令、MCP、规则和 wheel。Windows 使用 PowerShell 真正执行，macOS 用 Bash；Windows 专项测试验证带空格路径、退出码与保留不完整环境。macOS 打包工作流继续负责 DMG；当前不把 wheel 称作 Windows EXE 安装器。

协议测试使用合成 provider，不证明个人行情权限；`doctor` 和实际调用验证真实 OpenD。行为修改运行相应测试，文档修改检查链接和示例命令。完整 DMG 在 CI 构建，本地做必要测试和 wheel 验证即可。

交付时说明安装、OpenD 登录、doctor、MCP 宿主配置/发现/真实调用分别完成到哪里，保留未解决错误。不要把等待输入或下载失败说成成功。延续用户授权推进工作，不反复询问已确认事项；不自动合并 PR 或发布 Release。

需要推送而 macOS 钥匙串 helper 卡住时，已登录 `gh` 的情况下可仅对本次 push 使用 `git -c credential.helper= -c 'credential.helper=!gh auth git-credential' push`，不打印 token，不覆盖全局 Git 设置。

参考：[数据接口](docs/market-data.md)、[独立规则](modules/put-screener/README.md)、[官方 Codex MCP](https://developers.openai.com/codex/mcp/)、[Codex AGENTS.md](https://developers.openai.com/codex/guides/agents-md/)、[官方 MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)。
