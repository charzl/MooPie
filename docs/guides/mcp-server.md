# 配置本地 MCP 服务

服务名是本仓库自建的 **`moomoo-market-data`**，使用官方 Python `mcp>=2.3,<3` SDK 的 `MCPServer`，通过 **stdio** 提供行情工具。共享抓取层连接本机 OpenD；没有交易、账户、任意文件访问或自动选合约工具。

## 1. 先确认本机可用

完成[安装](../getting-started/installation.md)，运行 `./moomoo doctor`。默认安装包含 MCP；Qt 不影响 MCP。宿主与 OpenD 必须处于可互通环境，云端 agent 的 localhost 不是用户电脑。

## 2. 注册到宿主

先检查已有同名配置，保留其他服务。以下命令适用于已安装 Codex CLI 的 macOS，在仓库根目录运行：

```sh
codex mcp list
codex mcp add moomoo-market-data -- "$(pwd -P)/moomoo" mcp
codex mcp get moomoo-market-data
```

已有服务时先核对路径和参数，再按需更新；不要重复添加。若 OpenD 使用其他端口，在服务参数 `mcp` 后追加 `--port` 和实际端口。

Windows 宿主直接启动项目解释器，避免直接执行 PowerShell 脚本：

```powershell
codex mcp list
$MoomooPython = Join-Path (Get-Location).Path "apps\python\.venv\Scripts\python.exe"
codex mcp add moomoo-market-data -- $MoomooPython -X utf8 -m moopython.market_mcp
codex mcp get moomoo-market-data
```

使用 JSON 配置的宿主可合并下面一项，替换为实际绝对路径：

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

Windows 的 `command` 换成 `C:/.../apps/python/.venv/Scripts/python.exe`，`args` 换成 `["-X", "utf8", "-m", "moopython.market_mcp"]`。只要求阅读或更新文档时，不修改用户宿主配置。

## 3. 验证发现，再验证调用

重载 MCP 或打开新会话，确认四个工具出现，再发起小请求。配置记录存在、工具可发现、真实行情可调用是三项独立检查。

| 工具 | 参数示例 | 内容 |
| --- | --- | --- |
| `get_market_snapshots` | `{"codes":["US.AVGO"]}` | 股票或期权快照，每次1–200个代码 |
| `get_option_chain` | `{"symbol":"AVGO","months":1,"option_type":"PUT"}` | US 挂牌合约，默认1个月，支持显式 start/end |
| `get_daily_bars` | `{"symbols":["AVGO"]}` | 已完成日线，最多20个股票；支持 session_date/cutoff |
| `get_earnings_calendar` | `{"start":"2026-10-19","end":"2026-10-25"}` | 1–7个自然日；替换为所需日期 |

先看调用错误，再处理结构化数据中的缺失与逐项错误。日期范围、代码和限制详见[数据接口](../market-data.md)。不要用合约表代替可成交报价，也不要把未列入日历推断成没有财报。

## 4. 理解运行方式

宿主启动子进程，通过 stdin / stdout 收发协议。手动运行 `./moomoo mcp` 等待输入是正常现象，它不会主动打印行情，也不监听 HTTP 端口。SDK 日志走 stderr。

四个工具默认盘中连接 OpenD 并保存 SQLite，盘后优先查数据库，缺少匹配数据自动抓取并保存。`"refresh":true` 强制重抓；返回 `data_access` 说明来源、原始时间和 `cache_miss_fetch` 自动补抓标记。已有缓存查询保持本地读取，不连接OpenD。宿主可设置 `MOOMOO_DB_PATH` 与桌面共享同一数据库，见[数据库说明](database.md)。

实际 OpenD 请求由适配层串行执行并留限流间隔，数据库读取不等待限流；多个进程仍共享券商限额。优先小批量查询，完整 Put 研究用 `collect` 写文件再离线分析。MCP 与 CLI 共用抓取、路由和存储服务。

协议测试使用合成 provider，不能证明真实账号权限。宿主尚未加载工具时，可验证同一 stdio 服务的协议或继续使用 CLI，但交付时应说明实际调用路径。
