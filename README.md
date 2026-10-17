# MooPie · Moomoo 行情研究工具
<img width="1904" height="1013" alt="Screenshot 2026-10-17 at 3 38 37 PM" src="https://github.com/user-attachments/assets/587832e3-da88-4842-9e55-8833c4acfb16" />



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

打开界面，输入股票代码后选择「筛选卖出 Put」或「分析走势」。更改 Top、Filter 或排序复用已抓取的数据；点击查询按钮才刷新行情。股票、期权和历史日线权限以实际查询结果为准。

## 命令行

从仓库根目录执行，例如采集 AVGO，再离线筛选：

```sh
./moomoo collect AVGO --months 3 --output artifacts/input.json
./moomoo analyze artifacts/input.json --top 10 --rank-by return --output artifacts/ranking.json
```

`--rank-by` 支持 `return`（收益）、`risk`（风险）、`duration`（期限）、`cost`（担保成本）、`balanced`（综合分）。规则独立维护在 [put_rules.py](modules/put-screener/put_rules.py)。

Windows 将 `./moomoo` 换成 `powershell -NoProfile -ExecutionPolicy Bypass -File .\moomoo.ps1`。更多命令见 `./moomoo --help`。

## MCP 与详细文档

本仓库的 `moomoo-market-data` 使用本地 stdio，提供快照、期权链、日线和财报日历四个只读工具。

- [Agent 安装、OpenD、MCP 配置与排查](agent.md)
- [数据接口与架构](docs/market-data.md)
- [Put 规则、Filter 与排序](modules/put-screener/README.md)
- [收益与风险评分](docs/put-scoring.md)
- [第三方许可](THIRD_PARTY.md)

结果用于研究：收益按 Bid 估算、未扣费用，风险分不是亏损概率；旧数据重算不会变成最新报价。
