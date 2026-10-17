# GitHub、CI 与交付

仓库开发先完成可审查的本地改动和必要验证，再按用户安排提交、推送和交付。当前没有强制安装的提交格式 hook；清楚描述实际行为即可。

## 1. 查看工作区

```sh
git status --short --branch
git diff --stat
git diff --check
```

保留用户修改，按任务选择分支。不要为开始工作而清空仓库；不把 `artifacts/` 内真实行情、个人配置或凭据提交进去。

## 2. 批量实现并验证

相关修改集中完成后，按[测试指南](functional-testing.md)验证。PR 描述写清触发场景、修改后的行为和实际检查结果。涉及规则时，说明 Filter 是否改变、排序是否改变，以及使用哪份合成输入复现。

只读诊断可以使用已认证的 GitHub CLI：

```sh
gh pr status
gh pr view NUMBER --json number,title,state,headRefName,baseRefName,statusCheckRollup
gh pr checks NUMBER
gh run view RUN_ID --log-failed
```

把 `NUMBER` / `RUN_ID` 换成实际值。检查对应分支和提交，旧提交的绿灯不能证明新修改已经验证。

## 3. 了解现有 CI

| 文件 | 职责 |
| --- | --- |
| [client-platforms.yml](../../.github/workflows/client-platforms.yml) | Windows / macOS 安装、测试、独立 wheel、研究界面与 Windows 便携包 |
| [put-screener.yml](../../.github/workflows/put-screener.yml) | 独立 Put 文件测试、无第三方依赖运行、规则 artifact |
| [market-data-mcp.yml](../../.github/workflows/market-data-mcp.yml) | 抓取 / doctor / stdio MCP 的合成验证 |
| [package-python.yml](../../.github/workflows/package-python.yml) | macOS DMG、运行验证及受条件控制的发布 |
| [rule-engine.yml](../../.github/workflows/rule-engine.yml) | 单独 `modules/rule-engine` 包，和当前 Put 单文件不是同一入口 |

触发条件以 YAML 为准：部分工作流使用 paths 过滤，macOS 打包工作流还监听 PR、main push、版本 tag、定时任务和手动运行。因此文档改动也不能假定 push 后完全没有 CI。

用户要求暂不触发 CI 时，把结果留在本地，不推送、不手动运行工作流。不要以跳过检查标记替代应做的本地验证，也不要为这次要求修改现有工作流。

## 4. 合并与发布

合并前确认提交范围、冲突状态及本次所需检查。合并 PR、创建 tag 或发布 Release 按用户当前授权执行；一次合并不表示以后所有新改动都已获准发布。

交付准确区分本地已修改、已提交、已推送、PR 已合并、artifact 已构建和 Release 已发布。构建成功不自动代表公开发布，wheel / 便携 ZIP 也不是安装向导。

若 macOS 凭据 helper 卡住且 `gh` 已登录，需要推送时可仅对该次命令使用 Git 的临时 credential helper 配置；不要输出 token 或修改全局设置。实际命令见根目录 [agent.md](../../agent.md)。
