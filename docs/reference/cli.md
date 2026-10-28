# CLI 参考

从仓库根目录运行 `./moomoo <命令> --help` 查看当前实现。Windows 使用 `powershell -NoProfile -ExecutionPolicy Bypass -File .\moomoo.ps1 <命令>`，参数相同。

## 根目录入口

| 命令 | 主要参数 | 成功输出 |
| --- | --- | --- |
| `doctor` | `--symbol AAPL`、`--port 11111` | 人类可读的环境和真实报价检查 |
| `options SYMBOL` | `--months 3`、`--start`、`--end`、`--type ALL\|CALL\|PUT`、`--format json\|csv`、`--output`、`--host`、`--port` | 指定文件，或未指定 output 时的 stdout |
| `collect SYMBOL...` | `--months 3`、`--enrich INPUT`、`--output PATH`（必需）、`--port`、`--refresh` | 原始 JSON 文件；stdout 是保存摘要 |
| `analyze INPUT` | `--output PATH`（必需）、`--config PATH`、`--budget USD`、`--top N`、`--rank-by`、`--csv-output PATH`、`--scan-only` | 分析 JSON、可选 CSV；stdout 是摘要 |
| `mcp` | `--host`、`--port` | stdio 协议，等待宿主输入 |
| `db` | `status`、`schema`、`watchlist`、`price-signals SYMBOL [--limit N]`、`support-studies SYMBOL [--limit N]`、`import-watchlist PATH`、`export-watchlist PATH`、`search QUERY [--limit N]`、`sync-symbols [--port N]`、`retention --days N`、`cleanup --older-than-days N [--dry-run]`、`vacuum` | 状态 / 本地股票候选 / 支撑阻力历史与回测追踪 / 同步 / 清理 JSON；`schema` 输出 SQL；`sync-symbols` 和显式导入验证可连接 OpenD |
| `watchlist [LIST.json]` | `--check-only`、`--action both\|put\|trend`、`--top 5\|10\|20`、`--rank-by`、`--config`、`--refresh`、`--port`、`--output` | 默认读 SQLite；可选 JSON 临时输入；全名单预检查及逐股研究 JSON |
| `desktop` | `--classic`（可选旧面板） | 桌面窗口；需安装 desktop extra |
| `paper` | `strategies`、`list`、`create`、`backtest`、`update ID`、`report ID`、`watch ID` | 本地股票模拟实验与JSON报告；详见[模拟盘](../guides/paper-trading.md) |

`options` 的月份范围1–24，默认3；到期日 start/end 为 `YYYY-MM-DD`，区间包含 end，支持 US 和 HK。它返回合约信息，不返回完整报价研究数据。`collect` / MCP / Put 研究当前支持 US；完整采集最多20只股票。

`--enrich` 为已有原始输入补已完成日线，保留原报价采集时间。分析不连接 OpenD。`--budget` 限制一份标准合约的全部接股现金；与严格 `<` 的 `max-cost` Filter 边界不同。

`--rank-by` 可用 `duration`、`cost`、`return`、`risk`、`balanced`，覆盖本次排序。独立引擎的 `--top` 接受正整数；桌面和研究 CLI 只提供5/10/20。`--scan-only` 使用旧严格条件，输出扫描证据，不生成推荐列表。

## 单股票 / Watchlist 研究入口

输入股票代码时查询单股；省略代码时查询 SQLite Watchlist，`--watchlist PATH` 可只读本次 JSON 名单并合并排名。`add SYMBOL [--refresh]` 核验后写入 SQLite，不接受 `--watchlist`；JSON 导入使用 `db import-watchlist`。合并排名的 `--input` 使用原始多股票 dataset 离线重算；单股的 `--input` 仍要求输入仅包含请求股票。股票代码和 `--watchlist` 不能同时指定。

桌面首页调用 `research_cli overview` 只读取 Watchlist 股票报价，显示股票名、股价和涨跌；独立的 `research_cli radar --update` 将报价与 SQLite 已保存支撑区及买点提醒合并，缺少历史价位时明确标记不可用。日线价位在单股 `trend --depth` 中计算，并保存在 SQLite `price_signals` 表，供日后用 `./moomoo db price-signals SYMBOL --limit 20` 查询历史 JSON。卖出 Put 的普通查询使用研究 CLI `--saved`：包括盘中在内都读取最近已保存的收盘报告；已有股票不自动刷新，无任何历史记录的单股首次手动查询仍会自动抓取。可用 `python -m moopython.research_cli put --saved --top 10` 查看全名单保存结果。`--saved` 与 `--input` / `--refresh` / `--update` 互斥；主动更新仍用 `--update`。结果的 `saved_view` 保留展示交易日、最近完成交易日及是否直接复用了预计算报告。

名单管理：`db watchlist` 查看成员；`db import-watchlist FILE.json [--replace] [--refresh] [--port N]` 验证后合并，replace 为替换；`db export-watchlist FILE.json` 导出备份。空 JSON 在导入时表示空集合，replace 可明确清空；默认合并不删除既有成员。只有显式导入验证刷新可能连接 OpenD，查看与导出始终本地。

`sync-directory [--port N] [--output PATH]` 是桌面用的目录更新子进程入口，与 `./moomoo db sync-symbols` 共用实现；日志走 stderr，成功 JSON 包含 `action=directory_sync`、导入数量、目录总数、别名数、更新时间及不支持格式的 `skipped[]`。Put / trend / add 的位置参数仍是明确代码；名称解析先调用本地 `db search` 或在桌面候选中选择。

根目录启动器没有 `research` 或 `trend` 子命令。使用项目解释器：

单股 `trend SYMBOL --depth` 的 `support_study` 包含支撑触及后5／10／20日表现、未完成观察期和冻结支撑生命周期；与当前价位复用相同已验证日线，保存在 `support_studies`。用 `./moomoo db support-studies SYMBOL --limit 5` 可离线读取完整输入和事件历史。定义见[趋势分析](../guides/trend-analysis.md#6-支撑回测与冻结区间追踪)。

`collect`、`watchlist` 和研究 CLI 支持 `--update` 增量补抓，与强制 `--refresh` 互斥；盘中报价缓存有效期用 `--max-age-seconds` 设置，默认60，范围1–3600。普通无标志查询行为不变；`--input` 不与 update / refresh 同用。研究报告保留每股 Top 20 后归并全局 Top N，完整原始输入仍可离线重选。

```sh
apps/python/.venv/bin/python -m moopython.research_cli put AVGO --top 10
apps/python/.venv/bin/python -m moopython.research_cli trend AVGO
apps/python/.venv/bin/python -m moopython.research_cli overview
apps/python/.venv/bin/python -m moopython.research_cli trend AVGO --update --depth
apps/python/.venv/bin/python -m moopython.research_cli put --watchlist examples/watchlist.json --top 10
apps/python/.venv/bin/python -m moopython.research_cli add MSFT --refresh
apps/python/.venv/bin/python -m moopython.research_cli put AVGO \
  --input artifacts/put-screen/input.json --config artifacts/put-screen/filters.json --top 20
```

支持 `--port`、`--output`、`--config`、`--top 5|10|20`、`--input` 和 `--refresh`。`collect` 与研究入口默认盘中抓取保存、盘后优先读SQLite；缺少匹配快照自动抓取并保存，批量请求只补缺少成员。获取失败明确报错，已有匹配缓存的股票不重抓；`--refresh` 强制重抓，包括盘后。数据库位置可用 `MOOMOO_DB_PATH` 设置，见[数据库说明](../guides/database.md)。`--input` 仅用于 Put，不能与 `--refresh` 同用，要求原始 dataset；研究 CLI 结果先提取 `input_dataset`，桌面导出先提取 `put.input_dataset`，不能把整个包装结果作为输入。单股模式校验输入只有请求的一只股票；省略股票代码时支持多股票输入的全名单排名。

成功时写 UTF-8 JSON 到 output，未指定 output 则写 stdout；SDK 日志走 stderr。**指定 output 前先创建父目录**；`options --output` 同样要求目录存在。`collect` 与独立引擎会创建其输出父目录。

## 安装包入口

股票名单另提供 `moomoo-watchlist [LIST.json]`，参数与 `./moomoo watchlist` 相同，见[名单指南](../guides/watchlists.md)。

安装后的环境提供 `moomoo-options`、`moomoo-data`、`moomoo-mcp`、`moomoo-research`、`moomoo-db`，分别对应上述 options、collect、MCP、研究和数据库模块。desktop extra 另提供 `moomoo-desktop`。源码统一入口额外提供 `analyze`，直接执行独立规则文件。数据库维护默认不启用自动删除，显式 `retention --days N` 持久设置；`cleanup` 未传天数时使用该策略，策略关闭则要求显式天数。详见[清理说明](../guides/database.md)。

## 错误与退出码

以下是正常处理路径；未捕获的异常仍可能产生 traceback，应检查退出码和 stderr。

| 入口 | 已处理失败 | 参数用法错误 |
| --- | --- | --- |
| `doctor` | 1；人类可读输出 | 2；argparse stderr |
| `options` | 1；stderr 文本；取消为130 | 2；argparse stderr |
| `collect` | 1；stderr 文本 | 2；argparse stderr |
| `db` | 1；stderr 文本 | 2；argparse stderr |
| `watchlist` | 1；运行 / 分析错误；2；预检查失败（JSON） | 2；argparse stderr |
| `analyze` | 2；stderr 文本 | 2；argparse stderr |
| `research_cli` | 1；`{"error":"..."}` 写入所选 JSON 通道 | 2；argparse stderr，不能假定存在 JSON |
| `paper` | 1；`{"error":"..."}` 写入所选 JSON 通道；watch错误后按间隔重试 | 2；argparse stderr |
| `mcp` | 工具错误按 MCP 协议返回 | 启动参数无效或缺 MCP 依赖为2 |

成功的短命令退出码为0。MCP 是长运行服务；宿主应检查协议结果。不要给 doctor、collect 或 analyze 添加不存在的 `--output json` 参数；其中 output 表示文件路径或根本不支持。
