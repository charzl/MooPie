# 完成第一次查询

先完成[安装与连接](installation.md)。下面的联网示例可以替换成其他美股代码；只想试离线分析可直接运行最后一节。

## 使用界面

macOS 运行 `./moomoo desktop`。Windows 运行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\moomoo.ps1 desktop
```

输入股票代码，选择「筛选卖出 Put」或「分析走势」。Put 可选 Top 5/10/20、排序方式和 Filter；结果不足时查看排除原因。趋势结果说明日线日期、指标和改判条件。两者都可以导出 JSON。

## 查询未来三个月的挂牌 Put

```sh
mkdir -p artifacts/quickstart
./moomoo options AVGO --months 3 --type PUT \
  --output artifacts/quickstart/contracts.json
```

这里得到到期日、行权价和合约代码。合约表本身不含可用于收益比较的最新 Bid/Ask；完整研究还需要采集报价等数据。

## 抓取后离线筛选

```sh
./moomoo collect AVGO --months 3 --output artifacts/quickstart/input.json
./moomoo analyze artifacts/quickstart/input.json --top 10 --rank-by return \
  --output artifacts/quickstart/ranking.json \
  --csv-output artifacts/quickstart/ranking.csv
```

`input.json` 是原始研究输入；`ranking.json` 中 `recommendations` 是符合全部已启用边界的前10项，`ranked` 是完整排名，`results` 保留逐合约证据。CSV 导出完整合格排名及另列的待确认名单，数量可能超过10。

Windows 使用 `New-Item -ItemType Directory -Force artifacts/quickstart` 创建目录，把 `./moomoo` 换成上述 PowerShell 入口。多行命令可合为一行，Bash 的反斜杠不是 PowerShell 续行符。

## 不连接 OpenD 的合成示例

```sh
./moomoo analyze modules/put-screener/example.json --top 5 \
  --output artifacts/quickstart/synthetic-ranking.json
```

该文件是合成数据，结果日期来自示例。离线重算不会刷新行情，也不证明个人行情权限。接下来见[Put 筛选流程](../guides/put-screening.md)和[趋势分析流程](../guides/trend-analysis.md)。
