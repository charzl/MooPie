# Agent 安装与使用指南

目标：以最少步骤把仓库安装为可验证的行情工具。macOS 日常入口是 `./setup.sh` 和 `./moomoo`，Windows 为 `setup.ps1` 和 `moomoo.ps1`，人类使用说明见 [README.md](README.md)。

按需阅读 [docs 导航](docs/README.md)，完整任务流程见 [Agent 工作流](docs/guides/agent-workflows.md)。先遵循本页约束，再只加载任务相关文档：

| 当前任务 | 对应文档 |
| --- | --- |
| 安装、连接、第一次运行 | [安装](docs/getting-started/installation.md)、[快速上手](docs/getting-started/quickstart.md) |
| Put / 趋势研究 | [Put 筛选](docs/guides/put-screening.md)、[趋势分析](docs/guides/trend-analysis.md) |
| Watchlist 与批量研究 | [Watchlist 与预检查](docs/guides/watchlists.md) |
| 配置宿主或调 MCP | [MCP 服务](docs/guides/mcp-server.md) |
| 查参数、配置或返回字段 | [CLI](docs/reference/cli.md)、[配置](docs/reference/configuration.md)、[输出结构](docs/reference/output-schemas.md) |
| 盘中 / 盘后查询、本地数据库 | [数据库](docs/guides/database.md) |
| 股票策略研究与模拟盘 | [研究来源](docs/research/stock-strategies.md)、[计划](docs/plans/paper-trading.md)、[使用说明](docs/guides/paper-trading.md) |
| 修改代码并交付 | [架构](docs/reference/architecture.md)、[测试](docs/guides/functional-testing.md)、[GitHub / CI](docs/guides/github-workflows.md) |
| 排错或补文档 | [排查指南](docs/guides/troubleshooting.md)、[贡献规范与模板](docs/contributing/README.md) |

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

OpenD管理器统一实现于 `apps/python/moopython/opend_manager.py`，打包应用用同一可执行文件的 `opend` 子命令，不额外编译管理程序。保留官方签名、架构和固定版本哈希验证、原子选择、回退及文件锁；复用已有 `MooClients/OpenD` 安装和旧selection.json，不退出用户已登录的OpenD。资源目录只放opend.json，图标生成使用Python/Qt。

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

用户提供 JSON 名单时，使用 `./moomoo watchlist LIST.json --output artifacts/watchlist/results.json`，默认同时做每股 Top 10 Put 与走势；`--top` 可选5/10/20，`--action put|trend|both`。格式为 `{"symbols":["AVGO","NVDA"]}` 或字符串数组。先做本地全表检查，再通过证券基本资料验证全部代码；重复别名只分析一次。任一无效或无法验证的代码阻止整批分析，退出码2；缓存 / 权限缺失不当成代码不存在，不自动修正或跳过失败代码。`--check-only` 仅预检查；首次可显式加 `--refresh` 刷新基本资料。全部通过后逐只研究，一只分析失败记录错误并继续，退出码1且保留其他结果。`both` 复用已采集日线。名单超过20只仍逐只处理，预检查按200个分批。Top为每股独立排名。见[名单指南](docs/guides/watchlists.md)。

单次采集与离线研究流程：

```sh
./moomoo collect AVGO NVDA AAPL --months 3 --output artifacts/put-screen/input.json
./moomoo analyze artifacts/put-screen/input.json \
  --output artifacts/put-screen/ranking.json --csv-output artifacts/put-screen/ranking.csv
```

支持用户指定标的，不写死 AVGO。分析规则保留在独立 `modules/put-screener/put_rules.py`，修改 `TREND_RULES` / `RULES` / `SORT_ORDER` 后更新规则版本，对同一输入重跑。抓取、协议、分析和以后可能添加的存储层保持分离。

趋势分析报告数据日期/时区、考察期限、指标值、关键价位和改判条件；只使用已完成日线，不把规则命中数当成经过校准的涨跌概率。Put 结果查看 `ranked`、财报未验证观察名单、`failed_rules`、预算及快照时间。空结果保留，不为产生候选自动放宽规则；未知财报不推断成无财报。

Filter 与 Sort 分离：日常 CLI/桌面调用独立文件的 `recommend(dataset, budget=None, configuration=None, top_n=10)`。主界面Top数量可选5/10/20，默认10，每股选Top20再归并截取，不限制采集或Filter检查范围。预设支持 `duration`（到期时长升序）、`cost`（行权价×100的担保现金升序）、`return`（日均毛收益率降序）、`risk`（风险分升序）、`balanced`（综合分降序），也可自定义。严格返回 `ranked[:top_n]`，不足所选数量返回实际数量，不按到期日替换更高排名者。`ranking_views` 提供五种预设的Top代码。切换数量/排序通过 `research_cli --input --top` 离线重算完整缓存；GUI数量偏好独立保存在 `put_top_n`。日期、天数、行权价、成本及评分都由引擎返回。

评分只在 `put_rules.py` 的 `RISK_WEIGHTS` / `SCORING_PARAMETERS` 及函数中维护，初版Delta/情景亏损/趋势/流动性/财报权重25/25/20/15/15，参考情景下跌20%。风险分含缺失信息惩罚（默认100），不是亏损概率。收益分用固定日均参考目标0.1%映射0–100，综合分为 `return_weight×收益分+(1−return_weight)×(100−风险分)`，初始0.5。全部都是未校准原型参数。可选 `min-cost` / `max-cost` / `min-daily-return` / `max-risk` / `expiry-before` 默认关闭，启用后在完整数据上先评分、再过滤、最后排序取Top。比较为严格 `>` / `<`，成本美元、日均收益百分数值、风险0–100；日期阈值为ISO日期，不包含当天。修改评分不改变Filter配置或采集时间，但启用风险分过滤时可能改变候选集合。关闭Filter不取消该项风险分，趋势评分仍使用默认参考条件。详见 [docs/put-scoring.md](docs/put-scoring.md)。

`RECOMMENDATION_BOUNDARIES` 为未校准的示例预设：7–90天、价外幅度≥0、绝对Delta≤0.30、Bid≥0.10、买盘数量≥1、价差≤15%、同交易日报价，及标准合约/未停牌。个人风险范围未确认，不将示例阈值当成用户认可；预算未提供必须标记。趋势/财报/最低Delta/成交量/未平仓量默认不拦截，可通过 `--config` 显式启用为硬限制。基础有效性检查始终执行；任何已启用边界不可因高收益或结果为空而自动越过。`scan()` / `--scan-only` 保留原全条件扫描，调用时说明两者默认配置不同。`filter_impact` / `relaxation_preview` 只模拟数量。

新版 GUI 用独立设置键 `put_recommendation_configuration_v1`，保留旧设置且不自动继承旧全条件配置。已有新版配置继续复用，不随意重置用户选择。恢复默认 Filter 使用 `recommendation_configuration()`。趋势描述与风险提示不随过滤开关消失。

桌面配置界面在 `research_controls.py`，不是第二套规则。修改配置后优先通过研究子进程的 `--input` 离线重算现有 `input_dataset`，保持原始 `collected_at`。桌面启动先显示 Watchlist 价格总览与基本信息；股票逐行保留报价时间，支撑阻力使用最新已完成日线及报价计算。点击股票进入详情，按需读取前十档可见买卖盘，盘口时间缺失必须标明。卖出 Put 的正常查询仍带 `--saved`，通过 `saved_research.py` 读取最近已保存收盘报告，盘中也展示上一完成交易日，并恢复 Sort / Top 设置。更新后的收盘报告保存在原 snapshots 表，键绑定原始ID、参数和分析实现；旧库首次离线生成。盘中快照不能替代默认收盘报告，不同交易日不得合并。已有股票无收盘数据明确要求页签外右下角「更新行情」；从未采集过的单股首次手动查询自动抓取。原始采集 CLI / MCP 的时段路由不变。股票/端口改变后丢弃界面输入；导出包含数据、实际配置和证据。日线抓取失败需保留期权数据和明确错误：启用趋势 Filter 时阻止候选，用户关闭后可继续其他过滤。

输入候选的爱心由 `symbol_favorites.py` 绘制，点击经独立QProcess只验证身份并写Watchlist，不触发研究、不更改输入。实心仅表示已加入；删除仍在管理窗口确认。Put 完成后，走势页复用 canonical underlyings，不重复抓取；不足205根完整日线明确显示现有数量和原因，不编造长均线或趋势结论。

持仓效率由 `position_efficiency.py` 独立计算，`efficiency_dialog.py` 通过候选区「持仓效率」入口展示。按固定全额担保本金、自然日，E=(回购价/剩余天数)/(开仓权利金/原始期限)×100%；100%仅为原始效率基准。退出阈值独立参数exit_threshold_pct，默认None只观察；显式配置后E严格低于阈值才触发buy_to_close信号，等于不触发。80%只是待测候选，不设为已确认最优值；未来模拟盘按实验冻结配置，当前股票模拟器尚未接入Put退出。按用户当前要求不计风险、费用、利息，不改变Put排名；不是最优退出或预期收益。未盈利、当天开仓、已到期明确标记适用性。开仓信息必须手填，Ask / 交易日仅预填行情事实，不猜测持仓，也不新建交易上下文。见[指标说明](docs/guides/position-efficiency.md)。

桌面候选列表在 `research_table.py`，使用原生 Qt 表格，仅展示规则引擎返回值。排序入口只保留列头点击，不再显示重复的「收益优先 / 风险优先 / 综合 / 表头排序」下拉框；Top 数量和 Filter / 评分设置保留。列头通过配置触发完整缓存离线重算，不启用 Qt 对可见 Top N 的局部排序。点选合约后详情必须对应所选行；输入改变、重新抓取、取消或失败时清除过期候选。走势在独立页签，不需要网页服务。

顶层导航为「分析 / 模拟盘」，`main_tabs` 管理这两层入口。分析左侧选择股票 / 全名单，右侧突出 canonical 当前排序 No.1，再比较Top候选；原 `tabs` 仅保留推荐、详情、技术面依据三个页签，走势和价格信号合并在技术面中。OpenD端口和启动入口在全局设置。股票买入与 Sell Put 是不同工具，不能把卖出Put推荐直接当成股票买入信号，也不在本地研究中创建真实交易上下文。

导出的行情和分析结果写 gitignored 的 `artifacts/`。不提交账号、真实行情、本机绝对配置或 SQLite 数据文件。共享查询使用 `market_repository.market_data_connection`：盘中抓取并保存，盘后优先读取对应交易日的匹配快照，缺失自动连接OpenD抓取并保存；混合名单只补抓缺失成员。获取失败明确报错，不把无缓存或连接失败当成空候选。`market_collection.opend_connection` 保留为实时接口，`doctor` 使用它。SQLite 为 Python 内置模块，默认放平台应用数据目录，可用 `MOOMOO_DB_PATH` 覆盖。schema5以股票、操作、交易日、原始采集时间和批次索引，支持批量 / 单股 / 重排列表复用；旧版事务迁移不丢快照。保留原始时间和 `data_access.members`，不把不同采集时点当成同时报价。

使用 `./moomoo db retention --days N` 为当前数据库设置自动保留期；0为关闭。设置正数后，共享查询每天至多一次删除 `fetched_at` 严格早于 N 个自然日前的快照，读取缓存不延长寿命。用户尚未指定天数时保持关闭。`db cleanup --older-than-days N --dry-run` 可先预览，去掉 dry-run 执行一次；手动天数不改持久策略。最新日线快照内部的历史K线不被裁剪，旧采集版本按期限删除，旧报告引用不自动豁免，需要长期留存则导出完整输入。`db vacuum` 显式压缩文件，不在查询时执行。不安装定时任务或新后台服务。详见[数据库约定](docs/guides/database.md)。

## 7. 验证与交付

模拟盘v1.2默认6个客户，范围6–100，始终包含QQQ和SPY两个独立买入持有基准。config.symbols冻结策略股票池，market_symbols额外包含QQQ/SPY；每个客户的symbols明确限制选股，不能把两个额外ETF悄悄混进策略候选池。每客户默认500000美元，可独立设置initial_capital；funding_mode默认fixed、不补资，auto_deposit明确启用追加。两个ETF账户以各自完整起始本金建仓，费用、滑点、分红、下一开盘时序保持一致。默认表格比较相对SPY收益，JSON和详情另有相对QQQ / 股票池收益差；不是风险调整后的Alpha。旧v1.0实验不倒填基准，创建新版本实验，旧报告收益差可为空。

股票模拟盘分为 paper_strategies.py（独立策略）、paper_engine.py（纯账本与时序）、paper_data.py（行情抓取）、paper_store.py（SQLite v5）、paper_cli.py 和 paper_ui.py。只调用行情接口，不创建真实交易上下文。创建时冻结股票池、参数和引擎源文件哈希；已有实验实现变化后拒绝继续更新，保留旧报告并新建实验。PyInstaller需额外打包paper_engine.py / paper_strategies.py两份源码作为哈希审计资源。前向信号不能倒填过去开盘；历史回测单独标记，未到的1 / 3 / 6个月结果必须pending。任一股票日线不足253天、日历不齐或公司行动不支持时阻止整组推进，不擅自删股。固定资金不足时新买单等额分享可用现金并预留费用；自动补资模式单独记账，收益用时间加权净值。本金与单股投入独立，比较收益要同时查看实际持仓比例。新实验冻结每客户金额，旧实验本金不修改。行情保留期不能清理模拟盘输入或账本。桌面不轮询，仅显式更新或执行高级 paper watch 时抓取；没有配置每日 CI 或系统后台任务。

桌面语言和外观由 `desktop_preferences.py` 管理，翻译目录为 `desktop_translations.py`，配色为 `desktop_theme.py`。语言为 zh / en，主题为 system / dark / light，用原 QSettings 的 ui_language / ui_theme 保存，默认中文和跟随系统。动态展示文字经 ui.set_text 保存源文本，新增静态控件通过 localize_tree 注册；不得翻译或修改原始 report、股票代码、配置和导出数据。原生弹窗继承主窗口设置，表格自绘颜色须适配两种配色。切换语言 / 外观只重新展示，不调用研究或网络请求；系统颜色变化只影响 system 模式。

价格位置与择时信号单独维护在 `price_signals.py`，展示在「分析 → 技术面依据」，通过研究包装的 `price_signals` 返回，不能接入当前 Put Filter / 分数 / 排序。用户以后讨论系数不代表现在获准改变排名。复用 canonical trend 已验证日线及 ATR / 动能指标，不重复抓取；历史转折区保留日期、确认日期、参考价格来源、参数和版本，最后2根不确认为转折。未验证盘口承接和买卖比例保持 unknown，不将历史日线或期权 OI 声称为当前等候的真实买卖单。缺失证据不阻止原有 Put 排名。算法细节见趋势指南。

增量更新用 `market_data_connection(update=True,max_age_seconds=60)`，与 refresh 互斥。普通查询盘中实时、盘后缓存优先且缺失自动抓取；已有匹配的盘中快照保持原时间及非收盘标记。桌面「更新行情」及 CLI --update 还会补抓过期或仅盘中版本，盘后复用要求对应交易日收市后采集。盘中报价默认60秒，边界过期；身份按交易日复用，日线按最近完成交易日复用。右侧菜单「强制刷新全部」和 --refresh 保持全量强制语义。来源按成员保留，自动首次补抓用data_access.cache_miss_fetch说明，界面显示复用 / 抓取股票数。

研究入口统一调用 canonical recommend(...,per_symbol_limit=20)：同一 Filter / Sort 下每股有界堆选20，再归并全局20并输出5/10/20，不完整排序所有合格者；指标和 Filter 仍检查全部原始合约。global Put 采集用 run_watchlist(raw_put=True)，避免先逐股分析后再重复全表分析。qualified_count 是全部合格数，ranked最多20，ranking_reduction说明合并池；辅助预设名次仅在其Top20内提供，其他为null。改条件从完整input_dataset重新选择；独立API省略per_symbol_limit保持完整报告。严禁把旧排序Top20当新排序全集，或给每只股票分配最终名额。

桌面名称候选由 `symbol_search.py` 展示、`security_directory.py` 查询，150毫秒防抖、最多20项，精确代码 / 名称 / 别名优先，支持前缀、`*` / `?`。打字只查本地 SQLite，不导入 SDK。选中仅填代码，不自动研究或修改 Watchlist；未选定的名称 / 通配符不能猜为股票。`更新股票目录` / `./moomoo db sync-symbols` 才显式连接 OpenD，同步 US STOCK/ETF；保留更新失败前目录，记录不支持格式的 skipped。schema3 增加证券 / 别名表，旧快照和清理配置不变，资料不参加行情清理；别名允许多证券同名并保留来源，精选内置别名随包分发。CLI 名称检索用 `db search`，原研究和 JSON Watchlist 仍接受规范代码。

数据库结构维护在 `apps/python/moopython/database/migrations/`，已发布迁移不修改，新增版本递增执行。迁移和旧请求元数据转换共用同一个事务，禁止使用会隐式提交的 `executescript()` 破坏回滚。`schema.sql` 是自动导出的查阅文件，不手动维护；修改迁移后运行 `apps/python/.venv/bin/python scripts/export-database-schema.py`，加 `--check` 可检查一致性。`./moomoo db schema` 只在内存生成结构，不打开行情库。版本化 SQL 和导出文件必须包含在 wheel / 桌面包中。

```sh
PYTHONPATH=apps/python apps/python/.venv/bin/python -m unittest discover -s apps/python/tests/unit -v
apps/python/.venv/bin/python -m unittest discover -s modules/put-screener/tests -v
PYTHONPATH=apps/python apps/python/.venv/bin/python -m unittest discover -s apps/python/tests/mcp -v
```

跨平台工作流 `.github/workflows/client-platforms.yml` 必须同时跑 Windows 和 macOS 安装、命令、MCP、规则、独立 wheel 和研究界面测试。Windows 使用 PowerShell 真正执行，macOS 用 Bash；Windows 专项测试验证带空格路径、退出码与保留不完整环境。Windows 构建便携 EXE ZIP 并验证启动与 JSON 错误协议；macOS 打包工作流负责 DMG。不要把 wheel 或便携 ZIP 称作安装向导。

桌面默认是 `research_ui.py`，按首页价格总览 → 点击个股查看价位与盘口 → 查看走势 / Put 依据 → 独立模拟评估的流程组织。输入代码仍可筛选 Put；从左侧名单选择单股直接进入技术面详情，左侧「全部 Watchlist」返回首页；候选展开时回车选定，收起时回车搜索 Put。标题与搜索同行，No.1为紧凑摘要，统计与Top / Filter同行；候选表至少预留5个完整行及表头、滚动条的高度。左侧 Watchlist 菜单提供「查看」「加入」「管理」「更新目录」，右下角为行情更新。全名单对全部原始合约调用同一 `recommend()` 后取 Top 5/10/20，按相同条件每股保留20再归并，也不另写排序公式。原始合并输入支持离线筛选 / 表头排序，单股仍检查输入只包含该股票。

桌面截图、视觉检查和临时测试必须将 `MOOMOO_DB_PATH` 指向临时 SQLite 文件；不得在默认用户数据库运行测试名单的 `_merge(..., replace=True)` 或其他破坏性写入。读取真实用户行情库核对问题时先确认路径，保持只读；需要恢复数据时先做 SQLite 在线备份。

Watchlist 以同一 SQLite 的 `watchlist` 表为准，schema4新增，成员有唯一 symbol、自增id、加入时间和来源。首次读取时将库旁旧 JSON 或旧 `MOOMOO_WATCHLIST_PATH` 指定文件一次迁入并保留原文件；初始化标记和成员同事务，之后不再读取旧文件。无旧数据的新安装种子在 `watchlist_store.py` 的 DEFAULT_SYMBOLS，删除后不恢复。加入通过研究子进程核验证券资料后事务写入，不抓期权报价；重复不新增。`watchlist_dialog.py` 暂存删除，确认保存才按旧成员ID删除，取消不写库，保留并发新增和历史行情；删空保持空。CLI 省略 JSON 路径默认查库，显式 JSON 是本次只读输入，导入 / 导出使用 db import-watchlist / export-watchlist；不再维护默认 JSON 或文件锁。全名单预检查失败阻止采集，单股失败保留部分结果。

桌面通过 `QProcess` 运行 `research_cli.py`，后者调用共享研究 / 抓取服务，SDK 在子进程主线程运行。窗口关闭/取消会停止工作进程。冻结的 windowed EXE 通过临时 JSON 文件返回结果，不依赖 stdout；不要改为 GUI 线程直接请求 SDK。真实失败保留为空，不填演示报价。

规则、阈值、排序和趋势解释仍只维护 `modules/put-screener/put_rules.py`。`setup.py` 仅在 wheel/sdist 构建时拷贝快照，PyInstaller 同样包含该文件。源码总是优先读取独立文件；修改分发包规则要重新构建。不要手动维护第二套规则。运行研究界面测试：`PYTHONPATH=apps/python QT_QPA_PLATFORM=offscreen apps/python/.venv/bin/python -m unittest discover -s apps/python/tests/integration -p test_research_ui.py -v`。

协议测试使用合成 provider，不证明个人行情权限；`doctor` 和实际调用验证真实 OpenD。行为修改运行相应测试，文档修改检查链接和示例命令。完整 DMG 在 CI 构建，本地做必要测试和 wheel 验证即可。

开发迭代先集中修改并做本地验证。用户要求暂不触发CI时，不通过推送或手动运行工作流触发CI；保留本地可审查的结果，按用户的批次安排交付。

交付时说明安装、OpenD 登录、doctor、MCP 宿主配置/发现/真实调用分别完成到哪里，保留未解决错误。不要把等待输入或下载失败说成成功。延续用户授权推进工作，不反复询问已确认事项；不自动合并 PR 或发布 Release。

需要推送而 macOS 钥匙串 helper 卡住时，已登录 `gh` 的情况下可仅对本次 push 使用 `git -c credential.helper= -c 'credential.helper=!gh auth git-credential' push`，不打印 token，不覆盖全局 Git 设置。

参考：[数据接口](docs/market-data.md)、[独立规则](modules/put-screener/README.md)、[官方 Codex MCP](https://developers.openai.com/codex/mcp/)、[Codex AGENTS.md](https://developers.openai.com/codex/guides/agents-md/)、[官方 MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)。
