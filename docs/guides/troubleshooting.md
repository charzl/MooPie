# 排查问题

先记录使用的入口、退出码、stderr、标的和数据时间；按失败阶段定位。以下处理只修改问题所需的范围。

| 现象 | 检查与处理 | 如何确认恢复 |
| --- | --- | --- |
| 找不到项目解释器 | 在仓库根目录运行对应平台 setup；检查 uv | `moomoo --help` 后运行 doctor |
| 虚拟环境版本不兼容 | 查看安装报错和 `.venv` 版本；保留旧环境，确认用途后再调整 | 项目解释器为3.14，安装成功 |
| 依赖下载失败 | 区分 DNS、证书、403 和缓存不足；不要归为 OpenD 失败 | 安装退出0，再验证运行 |
| `doctor` 连不上 | OpenD 是否运行、API 是否本机11111或所传端口 | doctor 返回请求股票的有效报价 |
| 股票报价正常，期权或日线失败 | 分别检查行情权限和实际接口错误 | 对相应接口的小请求成功 |
| MCP 启动后一直等待 | stdio 在等宿主输入；检查宿主配置与工具发现 | 宿主可见四个工具且小请求成功 |
| MCP 配置存在但工具不可见 | 绝对路径是否有效、环境是否本机、是否重载宿主 | 新会话发现工具；不能只看配置记录 |
| 查询被限流 | 检查其他进程是否并发抓取；减小批量、等待服务限额恢复 | 小批量请求成功，错误仍有记录 |
| JSON 解析失败 | 该入口是否本来输出文本摘要？是否读错 stdout / 文件？ | 按 [CLI 通道约定](../reference/cli.md)读取 |
| 没有合格 Put | 查失败规则、配置和数据缺失；不要自动放宽 | 解释实际原因，用户调整后重算 |
| 日期截止似乎少一天 | `expiry-before` 是严格 `<`，不包含当天 | 配置日期与期望边界一致 |
| 改排序后报价没更新 | 设置变更使用原始缓存，时间保持不变 | 点主抓取按钮后采集时间更新 |
| 历史日线不足或过期 | 看 daily_series 错误、as_of、cutoff 和交易日历 | 有足够已完成日线，保留真实日期 |
| 桌面导出无法直接 analyze | 提取桌面导出的 `put.input_dataset`；研究 CLI 结果提取 `input_dataset` | 原始 dataset 可被引擎读取 |
| 已改源码但分发包规则未变 | 检查加载的是源码还是旧 wheel / 冻结包 | 重建包并核对报告文件哈希 |
| 打包版无法使用行情 | 保持完整解压目录，并确认官方 OpenD 登录 | doctor 或真实小查询成功 |

## 依赖源失败的处理

优先复用已安装环境与缓存。默认镜像已确认不可用时，macOS 可以显式使用官方 PyPI 和系统证书重试：

```sh
uv --system-certs pip install --default-index https://pypi.org/simple \
  --python apps/python/.venv/bin/python -e './apps/python[mcp]'
```

Windows 换成实际 `apps/python/.venv/Scripts/python.exe` 路径；不要关闭 TLS 校验。若只缺 MCP 依赖，可检查成功的 `Validate market data MCP` 是否仍有匹配平台与 Python 的依赖 artifact；它不是完整 SDK 安装包，且可能过期，不固定旧运行 ID。

## Put 空结果怎么说明

先区分基础数据无效与可配置条件失败。`results[].failed_rules` 是逐项原因，`filter_impact` 是排除计数，`relaxation_preview` 只是模拟；计数可能重叠。检查当前是否误用了旧严格 `--scan-only`。

用户可以明确调整 Filter 后对同一输入重跑。关闭趋势或财报过滤不会消除风险提示；启用 `max-risk` 时修改评分会影响候选资格。若合格不足10份就返回实际数量，不能从不合格名单补齐。

## 提交问题时保留什么

提供系统、Python / SDK 版本、命令参数、退出码、去敏后的报错、是否通过 doctor，以及相关合成复现。真实报价和账号资料留在本地；不要上传密码、验证码、token 或个人绝对路径配置。可使用[故障模板](../contributing/templates/troubleshooting.md)。
