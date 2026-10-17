# Moomoo 行情工具

抓取股票趋势分析所需的日线、期权合约和报价，用独立规则文件筛选卖 Put 的研究候选，也可让 agent 通过本地 MCP 调用。AVGO、NVDA、AAPL 都只是示例，当前研究工具支持美股标的。

**首次使用：安装工具 → 在官方 OpenD 登录 → 检查连接 → 开始查询。** 给 agent 的完整操作指南见 [agent.md](agent.md)，自动发现入口为 [AGENTS.md](AGENTS.md)。

## 1. 安装工具

需要 Git 和 [uv](https://docs.astral.sh/uv/getting-started/installation/)。macOS 缺少 uv 时运行 `brew install uv`；Windows 用 `winget install --id=astral-sh.uv -e`，安装后重开终端。脚本会准备 Python **3.14**，无需自己激活虚拟环境。

当前安装简化功能位于 `codex/simple-setup` 分支，首次下载对应版本：

```sh
git clone --branch codex/simple-setup https://github.com/charzl/moomoo-clients.git
cd moomoo-clients
./setup.sh
```

已有仓库时直接进入其根目录。主线合并该功能后可使用默认分支；切分支前保留本地未提交修改。

Windows 在 PowerShell 中使用以下安装入口（上面的 clone/cd 相同）：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\setup.ps1
```

日常命令使用 `powershell -NoProfile -ExecutionPolicy Bypass -File .\moomoo.ps1 <命令>`；若当前会话已允许运行本地脚本，可简写为 `.\moomoo.ps1 <命令>`。上述执行策略仅作用于该子进程，无需修改全局策略。

默认安装 **CLI + MCP**，不要求 Qt 桌面组件。已有环境会复用，所有依赖留在 `apps/python/.venv`。安装失败时先看具体错误，排查方法见 [agent.md](agent.md)。

## 2. 安装并登录 OpenD

1. 从[官方 OpenAPI 下载页](https://www.moomoo.com/download/OpenAPI)下载对应系统的 **moomoo OpenD GUI**，按官方说明安装。
2. 打开 OpenD，在官方窗口登录并完成验证。已安装、登录的实例直接复用。
3. 确认本机 API 地址为 **`127.0.0.1:11111`**，保持 OpenD 运行。

OpenD 是行情网关；Python SDK 和 MCP 通过它读取行情。安装本仓库不会代替你完成 OpenD 登录。源码默认 SDK/OpenD 版本信息在 [requirements.txt](apps/python/requirements.txt) 和 [opend.json](runtime/opend.json)。

## 3. 检查是否可以使用

```sh
./moomoo doctor
```

Windows 对应命令：`powershell -NoProfile -ExecutionPolicy Bypass -File .\moomoo.ps1 doctor`。下文命令相同，换用 Windows 入口即可；多行命令可合为一行执行。

会显示 Python、SDK、MCP 版本，并请求一条 AAPL 真实股票快照。成功时显示报价及 broker 更新时间；失败时指出检查位置。可用 `./moomoo doctor --symbol AVGO --port 11111` 更换验证标的或端口。

端口连通不等于拥有全部数据权限；股票、期权和历史日线可能分别受权限限制。收盘后得到最近交易时段的数据是正常情况。

## 4. 开始查询和分析

以下命令从仓库根目录执行，不用激活虚拟环境。

**查询未来三个月的 Put 到期日、行权价和合约代码：**

```sh
mkdir -p artifacts/options
./moomoo options AVGO --months 3 --type PUT \
  --output artifacts/options/AVGO-puts.json
```

这里是合约表，实时权利金需要另取快照。查询日期须为今天或未来；原始 `options` 命令另支持港股，但综合采集、MCP 和 Put 规则目前仅支持美股。

**抓取合约、报价、日线、财报，再运行独立规则：**

```sh
./moomoo collect AVGO NVDA AAPL --months 3 \
  --output artifacts/put-screen/input.json

./moomoo analyze artifacts/put-screen/input.json \
  --output artifacts/put-screen/ranking.json \
  --csv-output artifacts/put-screen/ranking.csv
```

抓取联网，分析离线。结果保存为 JSON/CSV；`ranked` 是全部规则通过的合约，`underlyings` 有 MA、RSI、MACD、ATR 和趋势证据，`failed_rules` 说明排除原因。未知财报的观察名单不属于合格名单，筛选结果为空也是有效结果。

修改 [put_rules.py](modules/put-screener/put_rules.py) 后，可对同一个输入重新分析，无需重新抓取或打包。可传 `--budget 25000` 限制一份合约的接股现金。规则是待验证的研究条件，不代表已经回测的收益优势或未来涨跌概率。详见[规则说明](modules/put-screener/README.md)。

所有命令可加 `--help`；总入口为 `./moomoo --help`。

## 5. 让 agent 使用 MCP

我们使用的是**本仓库自建的 `moomoo-market-data` 服务**，底层为官方 Python `mcp` SDK 的 `MCPServer`，通过本地 **stdio** 接口调用 OpenD。

| MCP 工具 | 用途 |
| --- | --- |
| `get_market_snapshots` | 股票/期权快照、可用的 Bid/Ask、Delta、IV 等 |
| `get_option_chain` | 期权到期日、行权价和合约代码 |
| `get_daily_bars` | 已完成的常规时段前复权日线 |
| `get_earnings_calendar` | 每次 1–7 个自然日的美股财报日历 |

**Codex CLI 已安装时**，在仓库根目录添加服务：

```sh
codex mcp add moomoo-market-data -- "$(pwd -P)/moomoo" mcp
codex mcp get moomoo-market-data
```

Windows 用项目虚拟环境的绝对解释器路径注册，避免宿主依赖 PowerShell 的执行策略：

```powershell
$MoomooPython = Join-Path (Get-Location).Path "apps\python\.venv\Scripts\python.exe"
codex mcp add moomoo-market-data -- $MoomooPython -X utf8 -m moopython.market_mcp
```

先用 `codex mcp list` 检查同名配置，已有服务时按 [agent.md](agent.md) 核对和更新。新开 agent 会话或重载 MCP，确认四个工具实际出现；Codex CLI 交互界面可用 `/mcp` 查看。[官方配置说明](https://developers.openai.com/codex/mcp/)

使用 `mcpServers` JSON 的其他宿主，可配置：

```json
{
  "mcpServers": {
    "moomoo-market-data": {
      "command": "/ABSOLUTE/PATH/moomoo-clients/moomoo",
      "args": ["mcp"]
    }
  }
}
```

Windows JSON 配置把 `command` 换成实际 `C:/.../apps/python/.venv/Scripts/python.exe`，`args` 使用 `["-X", "utf8", "-m", "moopython.market_mcp"]`。

替换为实际仓库绝对路径。MCP 服务由宿主按需启动；手动运行 `./moomoo mcp` 后等待输入是正常状态，它不是 HTTP 服务，也不会主动打印行情。

接入后可以问：

> 读取 AVGO 最新快照和已完成日线，分析未来几天到几周的走势。给出数据日期、指标证据、关键价位及改变判断的条件。

> 查询 NVDA 未来三个月 Put，抓取报价后使用仓库的独立规则筛选，解释未通过的条件。

## 6. 可选：桌面界面

需要 MooPie 图形界面时再安装：

```sh
./setup.sh --desktop
./moomoo desktop
```

Windows 对应 `setup.ps1 -Desktop` 和 `moomoo.ps1 desktop`。CLI/MCP 与 wheel 在 Windows 和 macOS 各自的 CI runner 验证；Windows 当前提供 Python wheel，尚不生成桌面 EXE 安装器。

macOS 也可从成功的 GitHub Actions 或 Releases 下载 `MooPie-macos-arm64`，打开 DMG 并拖到 Applications。打包应用的 OpenD 管理器可独立下载、验签和启动官方 OpenD；仍需在其官方窗口登录。DMG 不会替 agent 宿主注册 MCP。

## 开发与更多说明

抓取和 MCP 共用 Python 服务；规则保留为独立文件。当前保存 JSON，数据库和旧数据清理后续再做。正式 wheel 提供 `moomoo-options`、`moomoo-data`、`moomoo-mcp`；根目录 `./moomoo` 是方便源码使用的统一入口。

- [agent 安装、验证与排查](agent.md)
- [数据接口与架构](docs/market-data.md)
- [独立 Put 规则](modules/put-screener/README.md)
- [测试分层](tests/README.md)
- [第三方许可](THIRD_PARTY.md)

完整 DMG 交给 GitHub CI 构建；本地做开发、必要测试和 wheel 验证。CI 不登录个人 OpenD，真实数据权限以本机 `doctor` 和实际 MCP 调用为准。

跨平台 CI 见 [client-platforms.yml](.github/workflows/client-platforms.yml)：**Windows / install, test and wheel** 与 **macOS / install, test and wheel** 独立运行，验证安装、无 Qt 默认依赖、命令、MCP、规则和 wheel。每个平台产物分别保存；macOS DMG 另由现有打包工作流生成。
