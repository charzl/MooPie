# Moomoo 行情工具

输入一个美股代码，点击「筛选卖出 Put」或「分析走势」。桌面界面使用同一套抓取服务和独立规则文件，支持 macOS 和 Windows；也可通过 CLI 和本地 MCP 调用。AVGO、NVDA、AAPL 都只是示例。

**首次使用：安装工具 → 在官方 OpenD 登录 → 检查连接 → 开始查询。** 给 agent 的完整操作指南见 [agent.md](agent.md)，自动发现入口为 [AGENTS.md](AGENTS.md)。

## 1. 安装工具

需要 Git 和 [uv](https://docs.astral.sh/uv/getting-started/installation/)。macOS 缺少 uv 时运行 `brew install uv`；Windows 用 `winget install --id=astral-sh.uv -e`，安装后重开终端。脚本会准备 Python **3.14**，无需自己激活虚拟环境。

当前按日均收益比较 Put 的功能位于 `codex/put-recommendations` 分支，首次下载对应版本：

```sh
git clone --branch codex/put-recommendations https://github.com/charzl/moomoo-clients.git
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

抓取联网，分析离线。规则引擎先执行硬边界，再按 **权利金 ÷ 全额担保本金 ÷ 剩余自然日** 比较所有留下的合约。`best_recommendation` 返回首选，`recommendations` 默认最多三项，优先覆盖不同到期日，包含行权价、日均毛收益率、选择理由、风险及下跌情景损益。`ranked` 保留完整排序；`underlyings` 有趋势证据，`failed_rules` 说明排除原因。趋势偏弱及财报未知默认提示风险，可自行设为硬边界。

日均毛收益率是完整保留权利金时的比较值，不是每天实际到账或保证盈利。例如每张权利金 $200、担保本金 $10,000、剩余30天，日均为 `200 / 10000 / 30 × 100% = 0.0667%`。本金按 `行权价 × 100股`，使用 Bid 估算权利金，尚未扣除费用。

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

Windows 在 PowerShell 执行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\setup.ps1 -Desktop
powershell -NoProfile -ExecutionPolicy Bypass -File .\moomoo.ps1 desktop
```

输入股票代码，选择一个功能：

- **筛选卖出 Put**：抓取未来三个月合约、报价、日线和财报。展示规则引擎选出的首选与备选到期日/行权价、日均毛收益率、权利金、担保现金、盈亏平衡、最大亏损及选择理由，并保留前10名完整排序。
- **分析走势**：用已完成日线计算 MA20/50/200、RSI、MACD 和成交量，展示未来 5–20 个交易日的条件判断、关键价位及改判依据。它不是盘中预测或涨跌概率模型。

两个结果均标注股票、数据时间，可导出完整 JSON。查询在独立进程运行，可以取消；输入另一只股票会清空旧结果。默认连接本机 OpenD，界面可改端口。无需配置 MCP 或外部 AI API Key。

点「Filter / Sort 设置」：

- **Filter 页面**：勾选条件、调整不可越过的边界。基础预设为7–90天、行权价不高于现价、绝对 Delta ≤0.30、Bid ≥$0.10、买盘数量 ≥1、价差 ≤15%，且报价属于采集交易日。这些数值仅作研究示例，未代表你的个人承受范围。趋势、最低 Delta、成交量、未平仓量和财报默认仅供参考；可勾选升级为硬限制。标准100股、未停牌和必要数据检查始终执行。
- **Sort 页面**：独立选择最多三项排序指标及升降序。默认日均毛收益率从高到低，再比较价差与绝对 Delta。简单年化为日均值乘365，排序等价；改变 Sort 不改变候选名单。
- **没有结果**：面板显示实际指标、阈值、排除数量，以及关闭单项或趋势/财报组合后的候选数量预览。预览不自动应用条件；各项排除数量可能重叠。
- **调整后重跑**：已有数据时，点击“应用并重新筛选（已有数据）”离线重算，不重新请求 OpenD；结果保留原始采集时间。点击主界面“筛选卖出 Put”才刷新行情。更换股票或端口会清空缓存。设置会保留到下次打开。

关闭 Filter 不会消除风险：财报未知、默认趋势未通过和历史数据不可验证等提示仍保留。IV=0 作为未知展示，不参与当前排序；无效报价、Delta 或身份不一致等基础问题不会因关闭 Filter 而放行。

CLI 同样支持配置文件：`./moomoo analyze input.json --config filters.json --output ranking.json`，格式见[独立规则说明](modules/put-screener/README.md)。导出桌面 JSON 会保留原始输入、实际 Filter / Sort 配置与逐合约证据。

新版使用独立的推荐配置记录，首次启动采用上述基础预设，不自动继承旧版全部启用的严格筛选配置；旧配置记录保留。恢复默认 Filter 恢复基础预设。若仍需原先全条件扫描，可用 CLI 的 `--scan-only` 或独立引擎的 `scan()`。

Put 排序依据保留在 [put_rules.py](modules/put-screener/put_rules.py)，趋势解释在同文件的 `describe_trend()`。源码运行修改后立即生效；wheel 和桌面分发包带构建时的规则快照，修改后需要重新打包。原有行情面板可用 `./moomoo desktop --classic` 打开。

Windows 可在成功的 **Client platform CI** 中下载 `moomoo-tools-Windows`，取其中 `MooPie-windows-x64.zip`，完整解压后双击文件夹内的 `MooPie.exe`。这是便携版，不是安装向导；不需要另装 Python，但仍需安装并登录官方 OpenD。

macOS 也可从成功的 GitHub Actions 或 Releases 下载 `MooPie-macos-arm64`，打开 DMG 并拖到 Applications。打包应用的 OpenD 管理器可独立下载、验签和启动官方 OpenD；仍需在其官方窗口登录。DMG 不会替 agent 宿主注册 MCP。

## 开发与更多说明

桌面、CLI 和 MCP 共用 Python 抓取服务；规则保留为独立文件。当前保存 JSON，数据库和旧数据清理后续再做。wheel 提供 `moomoo-options`、`moomoo-data`、`moomoo-mcp`、`moomoo-research`；安装 desktop extra 后还可运行 `moomoo-desktop`。根目录 `./moomoo` 是方便源码使用的统一入口。

- [agent 安装、验证与排查](agent.md)
- [数据接口与架构](docs/market-data.md)
- [独立 Put 规则](modules/put-screener/README.md)
- [测试分层](tests/README.md)
- [第三方许可](THIRD_PARTY.md)

完整 DMG 交给 GitHub CI 构建；本地做开发、必要测试和 wheel 验证。CI 不登录个人 OpenD，真实数据权限以本机 `doctor` 和实际 MCP 调用为准。

跨平台 CI 见 [client-platforms.yml](.github/workflows/client-platforms.yml)：Windows 与 macOS 独立验证安装、无 Qt 默认依赖、命令、MCP、规则、独立 wheel 和界面。Windows 额外打包并实际启动 EXE；macOS DMG 由现有打包工作流生成并验证。
