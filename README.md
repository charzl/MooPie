# MooPie · Moomoo 行情研究工具

<img width="1518" height="1035" alt="Screenshot 2026-10-17 at 1 56 39 AM" src="https://github.com/user-attachments/assets/0723947a-bcf2-4a03-b73c-ed8bf816a654" />





支持 macOS 和 Windows，通过本机 moomoo OpenD 查询美股行情。

- **筛选卖出 Put**：选择股票、Filter 和排序方式，返回 Top 5 / 10 / 20 候选，展示收益、风险、到期日及担保成本。
- **分析走势**：根据已完成日线展示均线、RSI、MACD、关键价位和判断依据。
- 同时提供桌面界面、命令行和本地只读 MCP；研究功能不下单。

## 快速开始

准备 Git 和 [uv](https://docs.astral.sh/uv/getting-started/installation/)，然后获取源码：

```sh
git clone https://github.com/charzl/moomoo-clients.git
cd moomoo-clients
```

从[官方下载页](https://www.moomoo.com/download/OpenAPI)安装 **moomoo OpenD GUI**，在官方窗口登录，保持本机 API `127.0.0.1:11111` 开启。

**macOS：**

```sh
./setup.sh --desktop
./moomoo doctor
./moomoo desktop
```

**Windows PowerShell：**

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\setup.ps1 -Desktop
powershell -NoProfile -ExecutionPolicy Bypass -File .\moomoo.ps1 doctor
powershell -NoProfile -ExecutionPolicy Bypass -File .\moomoo.ps1 desktop
```

安装脚本准备 Python 3.14 和项目依赖，无需手动激活虚拟环境。只用 CLI / MCP 时，省略 `--desktop` 或 `-Desktop`。

打开界面，输入代码搜索单股，留空搜索默认 Watchlist；同一张表显示 Top 5 / 10 / 20，输入股票后可点「加入 Watchlist」。盘中读取 OpenD 并保存 SQLite，盘后直接读库；首次无数据时点「更新行情」。更改 Top、Filter 或排序复用已有数据。详见[Watchlist](docs/guides/watchlists.md)与[数据库说明](docs/guides/database.md)。

关注名单保存在 SQLite。点「管理 Watchlist」可选中股票、删除，再点「确认保存」生效；取消则保留原名单。已有旧 JSON 会自动迁入一次，日常无需维护文件。

「更新行情」只补抓缺失或过期股票；右侧菜单可强制刷新全部。排名按相同条件每股选 Top 20，再合并取全局 Top 5 / 10 / 20。

首次点击「更新股票目录」，以后输入代码、公司名或别名，下面会显示可选股票。支持前缀（`av`）、通配符（`*broadcom*`、`nv?`）及已收录别名（`avago`）；点击或用方向键＋回车选择，再查询。打字时只查本地 SQLite。

## 命令行

从仓库根目录执行，例如采集 AVGO，再离线筛选：

```sh
./moomoo collect AVGO --months 3 --refresh --output artifacts/input.json
./moomoo analyze artifacts/input.json --top 10 --rank-by return --output artifacts/ranking.json
```

`--rank-by` 支持 `return`（收益）、`risk`（风险）、`duration`（期限）、`cost`（担保成本）、`balanced`（综合分）。规则独立维护在 [put_rules.py](modules/put-screener/put_rules.py)。

批量研究运行 `./moomoo watchlist --refresh --output artifacts/watchlist/results.json`，使用数据库中的名单。先验证全部股票代码，再逐只返回 Put 候选和走势；后续盘后查询省略 `--refresh`。JSON 仍可选作临时输入、导入或导出，见[Watchlist 使用说明](docs/guides/watchlists.md)。

Windows 将 `./moomoo` 换成 `powershell -NoProfile -ExecutionPolicy Bypass -File .\moomoo.ps1`。更多命令见 `./moomoo --help`。

数据库可设置自动保留期，例如 `./moomoo db retention --days 180`；清理前可用 `./moomoo db cleanup --older-than-days 180 --dry-run` 预览。默认保留全部，设置后查询时每天最多清理一次，详见[数据库与多股票存储](docs/guides/database.md)。

## MCP 与详细文档

本仓库的 `moomoo-market-data` 使用本地 stdio，提供快照、期权链、日线和财报日历四个只读工具。

- [Agent 安装、OpenD、MCP 配置与排查](agent.md)
- [数据接口与架构](docs/market-data.md)
- [Put 规则、Filter 与排序](modules/put-screener/README.md)
- [收益与风险评分](docs/put-scoring.md)
- [第三方许可](THIRD_PARTY.md)

结果用于研究：收益按 Bid 估算、未扣费用，风险分不是亏损概率；旧数据重算不会变成最新报价。
