# Watchlist 与预检查

股票名单保存在 SQLite，独立于规则配置。先预检查整个名单，再逐只采集和分析。桌面支持单股或整个 Watchlist，沿用同一张原生候选表；CLI 也可输出每只股票的独立报告。

## 桌面搜索与加入

- 输入股票代码，点击「筛选卖出 Put」或按回车：查询该股票，默认 Top 10。
- 输入留空时按回车：返回首页价格总览；点击「筛选卖出 Put」则查询默认 Watchlist，将全部成功采集的合约交给同一规则引擎，按当前 Filter / Sort 取全名单 Top 5 / 10 / 20。
- 在左侧 Watchlist 下拉菜单选择「查看 Watchlist」：返回首页价格总览。点击任一股票进入详情，查看历史支撑阻力及当前可见买卖盘。
- 输入股票后在菜单选择「加入 Watchlist」：先核验证券基本资料，再保存；不抓取期权或日线。重复代码不重复写入，无效或无法验证的代码不加入。
- 输入候选行右侧的空心爱心也可以加入，成功后变实心；不改变输入、不启动研究、不清除当前结果。键盘可在候选显示时按 Ctrl+D。已收藏的爱心不执行删除，移除仍用管理窗口确认。
- 在菜单选择「管理 Watchlist」打开名单，可选一个或多个股票，再点「删除选中」。此时仅在窗口内暂存删除，点「确认保存」才写入数据库；取消或关闭窗口不改变名单。只删除所选记录，保留其他窗口的新加入项，也不删除历史行情或公司资料。删空后保持空名单，提示先加入股票。

正常启动时，首页和左侧 Watchlist 只显示股票名、股价和涨跌；上涨为绿色，下跌为红色。悬停查看各股报价时间。点击股票后才计算该股日线支撑阻力并读取买卖盘；结果连同参考价、报价时间、算法版本及历史转折依据保存到 SQLite，按股票可查询历次记录。卖出 Put 的已保存收盘结果仍在「筛选卖出 Put」中使用，并恢复当前排序和 Top 设置；盘中读取上一完成交易日的收盘研究，不能把盘中快照冒充收盘。见[保存结果策略](database.md)。

切换 Top、表头排序或 Filter 时，对已保存的完整输入离线重算，不重新抓取。同一套 Filter / Sort 下，每只股票用有界堆保留 Top 20，再归并取全局 Top 5 / 10 / 20；不按股票分配最终名额。所有合约仍需检查必要指标和 Filter，完整原始输入用于更改条件后重新选 Top 20，不把旧收益排序的 Top 20 直接用作新风险排序的全集。某只股票采集失败会明确显示为部分结果，并保留具体原因；预检查失败仍阻止整批采集。

「更新行情」逐股检查缓存，只补抓新增、缺失或过期股票，界面显示复用 / 抓取数量；右侧菜单「强制刷新全部」用于主动重抓所有股票。盘中默认60秒过期，盘后有效快照的判定见[缓存策略](database.md)。

默认名单以同一个 SQLite 的 `watchlist` 表为准，`MOOMOO_DB_PATH` 决定数据库位置，按钮提示显示实际位置。首次使用自动把库旁已有 `watchlist.json` 导入一次，保留原文件；旧 `MOOMOO_WATCHLIST_PATH` 仅兼容指定首次迁移来源，不再控制日常存储。旧名单格式错误时明确报错，不用默认值覆盖。完全新安装默认 AVGO / NVDA / AAPL，此后不会自动恢复已删除股票。新增和删除用事务及唯一约束，不再维护 JSON 文件锁。

JSON 只用于显式导入、导出或本次临时研究，导出不是自动同步。导入全表通过证券验证后才合并；`--replace` 表示验证通过后替换名单，失败保留原名单：

```sh
./moomoo db watchlist
./moomoo db import-watchlist examples/watchlist.json --refresh
./moomoo db export-watchlist artifacts/watchlist/export.json
```

## 公司名、别名与候选选择

桌面在 Watchlist 菜单选择「更新股票目录」，由子进程读取 OpenD 的美股 STOCK / ETF 基本资料，不抓报价、期权或日线。更新失败保留已有目录；成功合并时保留证券ID和别名，不因本次名单缺少某代码就推断退市。名称为空或退市状态不明确的响应阻止入库，当前代码语法不支持的特殊证券在同步结果 `skipped[]` 中列明。

输入后约150毫秒在下方显示最多20个候选，精确代码优先，其次精确名称 / 别名，再按代码和名称前缀排序；相同证券只显示一次。匹配忽略大小写、首尾及重复空格，统一 Unicode 字形：

| 输入 | 匹配方式 |
| --- | --- |
| `av`、`broad` | 代码、公司名或别名前缀 |
| `*broadcom*` | 任意位置包含 Broadcom |
| `nv?` | `?` 匹配一个字符，`*` 匹配任意长度 |
| `avago`、`博通` | 已收录的 Broadcom / AVGO 别名 |

SQL 的 `%`、`_` 按字面字符处理，不是这里的通配符。点击候选，或用上下键与回车选择，只将明确代码填入输入框，不自动抓取或加入名单；再点击 Put / 趋势按钮，或在菜单选择加入 Watchlist。Esc 收起，清空后恢复 Watchlist 查询。未选择的公司名、前缀或通配符不作为猜测的股票代码发送。已有完整代码仍可直接查询，即使本地目录尚未收录它；实际可用性由原有证券验证 / 行情接口判断。

目录存 `securities`、别名存 `security_aliases`，独立于行情快照清理。别名来源保存在表内，内置文件为 [`security_aliases.json`](../../apps/python/moopython/data/security_aliases.json)，当前仅精选 AVGO 的历史名称及常用名，并非全市场中英文 / 历史别名全集。同一别名可对应多个证券，交给用户选择。Python 调用 `SecurityDirectory.search()`、`add_alias()` 可复用及补充目录。

```sh
./moomoo db sync-symbols              # 显式连接已登录 OpenD，更新目录
./moomoo db search avago             # 本地查别名
./moomoo db search '*broadcom*'       # 给通配符加引号，防止 shell 展开
```

## 可选 JSON 输入

复制 [examples/watchlist.json](../../examples/watchlist.json)，修改为所需的 US 股票 / ETF：

```json
{"symbols": ["AVGO", "NVDA", "US.AAPL"]}
```

也接受纯字符串数组 `["AVGO", "NVDA"]`。代码去首尾空格、转大写、补 `US.`，支持 `BRK.B` 等代码；重复别名只分析一次，报告保留重复项位置。JSON 对象只接受 `symbols` 字段，重复字段、非标准 JSON、空数组、非字符串或非 US 代码会明确报错。期权完整合约代码不能放在股票名单里。

名单不限于20只：证券基本资料按每批最多200个代码预检查，研究按每只股票串行执行，复用已有采集接口。

## 预检查与批量分析

```sh
# 首次或需要更新证券资料时，显式连接 OpenD；不抓期权或日线
./moomoo watchlist --check-only --refresh \
  --output artifacts/watchlist/precheck.json

# 验证全部代码后逐只采集、保存 SQLite、分析 Put 和走势
./moomoo watchlist --update --top 10 \
  --output artifacts/watchlist/results.json

# 盘后复用数据库，可更换 Top、排序和规则配置
./moomoo watchlist --top 20 --rank-by risk \
  --output artifacts/watchlist/risk-top20.json
```

本地格式检查全部通过后，调用 OpenD `get_stock_basicinfo` 确认代码、证券类型和退市状态。接口依据[官方证券基本资料文档](https://openapi.moomoo.com/moomoo-api-doc/en/quote/get-static-info.html)；不通过“有一条价格”或“格式正确”推断有效。代码有效不保证具有期权 / 日线权限，也不保证存在可卖 Put。

| 状态 | 意义 |
| --- | --- |
| `valid` | 券商识别为未退市股票 / ETF，名称和状态齐全 |
| `duplicate` | 已出现过的规范化代码，只研究一次 |
| `invalid_format` | 本地格式或市场不支持；整份名单不发起数据查询 |
| `invalid` | 券商明确不识别、已退市或为不支持的证券类型 |
| `unverified` | 缺少缓存、连接 / 权限错误、缺失资料或响应不完整；不推断为代码错误 |
| `not_checked` | 名单其他项有本地格式错误，尚未向券商验证 |

任一唯一代码无效或无法验证时，**整批分析暂停**，报告 `status=precheck_failed`，退出码2。修正名单或补齐验证资料后重跑；不会自动删掉失败代码继续。重复项不阻止其他有效代码分析。

默认 `--action both`；`--action put` 只研究 Put，`--action trend` 只研究走势。`--config` 使用现有 Filter / 评分 / Sort 配置；`--rank-by return|risk|duration|cost|balanced` 覆盖本次 Put 排序。Top 数量作用于每只股票，不足时返回实际候选，不自动放宽 Filter。

上面的 `./moomoo watchlist` 保留逐股报告。与桌面相同的合并排名使用研究入口：

```sh
# 单股票
apps/python/.venv/bin/python -m moopython.research_cli put AVGO --top 10
# 整个数据库名单合并取 Top 10；可用 --watchlist FILE.json 临时读取另一个名单
apps/python/.venv/bin/python -m moopython.research_cli put --top 10
# 核验并加入默认名单；此动作的refresh仅刷新证券基本资料
apps/python/.venv/bin/python -m moopython.research_cli add MSFT --refresh
```

预检查通过后，单只股票分析失败会记录具体错误并继续后续股票。`both` 复用 Put 采集已有的日线；Put 读取失败仍尝试该股票走势。空候选列表保留为空，不伪造结果。

证券资料和研究遵循[盘中 / 盘后数据库策略](database.md)：盘中抓取保存，盘后优先读取对应交易日缓存，缺少成员自动请求OpenD并保存；已有匹配缓存的成员不重抓。`--refresh` 强制重抓，`--check-only --refresh` 只刷新证券资料。获取失败保留具体原因，不把无缓存当成无效股票或空分析。正常查询会应用已配置的数据库保留策略。

Windows 将 `./moomoo` 换成 `powershell -NoProfile -ExecutionPolicy Bypass -File .\moomoo.ps1`。安装后的独立入口为 `moomoo-watchlist`。

## 报告与退出码

指定 `--output` 自动创建父目录，写完整 UTF-8 JSON；否则 JSON 写 stdout。进度和 SDK 日志写 stderr，不污染结果。

| 字段 | 内容 |
| --- | --- |
| `precheck.entries` | 输入位置、规范化代码、状态、原因、名称与来源时间 |
| `precheck.valid_symbols`、`invalid`、`unverified`、`duplicates` | 完整检查分类 |
| `results[]` | 每只股票的 `symbol`、`status`，及所选 `put` / `trend` 研究结果或 `error` |
| `summary` | 输入、去重、有效、无效、未验证、实际分析和失败数量 |
| `ranking_scope`、`top_n` | 当前为 `per_symbol`，每股独立取 Top N |
| `started_at`、`completed_at` | 本次执行时间；行情原始时间仍在每只股票结果中 |

退出码0：预检查成功或全部分析完成；2：预检查失败或 argparse 用法错误；1：文件 / 配置等运行错误或部分分析失败。单股 `status=partial` 表示两个动作中一个失败，另一个结果仍可读取。零候选是有效分析结果。
