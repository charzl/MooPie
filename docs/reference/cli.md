# CLI 参考

从仓库根目录运行 `./moomoo <命令> --help` 查看当前实现。Windows 使用 `powershell -NoProfile -ExecutionPolicy Bypass -File .\moomoo.ps1 <命令>`，参数相同。

## 根目录入口

| 命令 | 主要参数 | 成功输出 |
| --- | --- | --- |
| `doctor` | `--symbol AAPL`、`--port 11111` | 人类可读的环境和真实报价检查 |
| `options SYMBOL` | `--months 3`、`--start`、`--end`、`--type ALL\|CALL\|PUT`、`--format json\|csv`、`--output`、`--host`、`--port` | 指定文件，或未指定 output 时的 stdout |
| `collect SYMBOL...` | `--months 3`、`--enrich INPUT`、`--output PATH`（必需）、`--port` | 原始 JSON 文件；stdout 是保存摘要 |
| `analyze INPUT` | `--output PATH`（必需）、`--config PATH`、`--budget USD`、`--top N`、`--rank-by`、`--csv-output PATH`、`--scan-only` | 分析 JSON、可选 CSV；stdout 是摘要 |
| `mcp` | `--host`、`--port` | stdio 协议，等待宿主输入 |
| `desktop` | `--classic`（可选旧面板） | 桌面窗口；需安装 desktop extra |

`options` 的月份范围1–24，默认3；到期日 start/end 为 `YYYY-MM-DD`，区间包含 end，支持 US 和 HK。它返回合约信息，不返回完整报价研究数据。`collect` / MCP / Put 研究当前支持 US；完整采集最多20只股票。

`--enrich` 为已有原始输入补已完成日线，保留原报价采集时间。分析不连接 OpenD。`--budget` 限制一份标准合约的全部接股现金；与严格 `<` 的 `max-cost` Filter 边界不同。

`--rank-by` 可用 `duration`、`cost`、`return`、`risk`、`balanced`，覆盖本次排序。独立引擎的 `--top` 接受正整数；桌面和研究 CLI 只提供5/10/20。`--scan-only` 使用旧严格条件，输出扫描证据，不生成推荐列表。

## 单股票研究入口

根目录启动器没有 `research` 或 `trend` 子命令。使用项目解释器：

```sh
apps/python/.venv/bin/python -m moopython.research_cli put AVGO --top 10
apps/python/.venv/bin/python -m moopython.research_cli trend AVGO
apps/python/.venv/bin/python -m moopython.research_cli put AVGO \
  --input artifacts/put-screen/input.json --config artifacts/put-screen/filters.json --top 20
```

支持 `--port`、`--output`、`--config`、`--top 5|10|20` 和 `--input`。`--input` 仅用于 Put，要求原始 dataset；研究 CLI 结果先提取 `input_dataset`，桌面导出先提取 `put.input_dataset`，不能把整个包装结果作为输入。该入口校验输入只有请求的一只股票；多股票输入用 `analyze`。

成功时写 UTF-8 JSON 到 output，未指定 output 则写 stdout；SDK 日志走 stderr。**指定 output 前先创建父目录**；`options --output` 同样要求目录存在。`collect` 与独立引擎会创建其输出父目录。

## 安装包入口

安装后的环境提供 `moomoo-options`、`moomoo-data`、`moomoo-mcp`、`moomoo-research`，分别对应上述 options、collect、MCP、研究模块。desktop extra 另提供 `moomoo-desktop`。源码统一入口额外提供 `analyze`，直接执行独立规则文件。

## 错误与退出码

以下是正常处理路径；未捕获的异常仍可能产生 traceback，应检查退出码和 stderr。

| 入口 | 已处理失败 | 参数用法错误 |
| --- | --- | --- |
| `doctor` | 1；人类可读输出 | 2；argparse stderr |
| `options` | 1；stderr 文本；取消为130 | 2；argparse stderr |
| `collect` | 1；stderr 文本 | 2；argparse stderr |
| `analyze` | 2；stderr 文本 | 2；argparse stderr |
| `research_cli` | 1；`{"error":"..."}` 写入所选 JSON 通道 | 2；argparse stderr，不能假定存在 JSON |
| `mcp` | 工具错误按 MCP 协议返回 | 启动参数无效或缺 MCP 依赖为2 |

成功的短命令退出码为0。MCP 是长运行服务；宿主应检查协议结果。不要给 doctor、collect 或 analyze 添加不存在的 `--output json` 参数；其中 output 表示文件路径或根本不支持。
