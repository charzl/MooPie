# 安装工具并连接 OpenD

目标是得到可运行的本地工具和一次真实股票报价。MCP、期权权限和日线权限需要在之后分别验证。

## 1. 检查已有环境

已有仓库时直接进入根目录，保留当前修改和虚拟环境。更新分支前先查看 `git status --short`。项目使用 Python `>=3.14,<3.15`，安装脚本通过 uv 准备项目环境，不修改系统 Python。

新环境先准备 Git 和 uv。macOS 可用 `brew install uv`，Windows 可用 `winget install --id=astral-sh.uv -e` 后重开终端。其他安装方式见 [uv 安装说明](https://docs.astral.sh/uv/getting-started/installation/)。

```sh
git clone https://github.com/charzl/moomoo-clients.git
cd moomoo-clients
```

## 2. 安装所需功能

macOS：

```sh
./setup.sh
# 需要图形界面时：
./setup.sh --desktop
```

Windows PowerShell：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\setup.ps1
# 需要图形界面时：
powershell -NoProfile -ExecutionPolicy Bypass -File .\setup.ps1 -Desktop
```

默认安装 CLI 和 MCP；桌面组件可选。脚本复用或创建 `apps/python/.venv`，不要求手动激活。已有虚拟环境版本不兼容时会保留并报错，不自动删除。PowerShell 执行策略只作用于本次子进程。

| 平台 | 项目解释器 | 日常入口 |
| --- | --- | --- |
| macOS | `apps/python/.venv/bin/python` | `./moomoo` |
| Windows | `apps/python/.venv/Scripts/python.exe` | `powershell -NoProfile -ExecutionPolicy Bypass -File .\moomoo.ps1` |

## 3. 安装并登录官方 OpenD

先检查现有 OpenD；macOS 可用 `lsof -nP -iTCP:11111 -sTCP:LISTEN`，Windows 可用 `Get-NetTCPConnection -LocalPort 11111 -State Listen`。复用已登录实例。

没有 OpenD 时，从[官方 OpenAPI 下载页](https://www.moomoo.com/download/OpenAPI)安装对应平台的 **moomoo OpenD GUI**，在官方窗口登录并完成验证。SDK 与普通交易客户端不能代替 OpenD。

保持本机未加密 API 地址 `127.0.0.1:11111`；自定义端口传给工具。源码安装脚本不自动安装或登录 OpenD。密码和验证码只在官方窗口输入，不写入配置文件、命令或 Git。

## 4. 验证一次真实连接

```sh
./moomoo doctor --symbol AVGO --port 11111
```

Windows：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\moomoo.ps1 doctor --symbol AVGO --port 11111
```

成功应看到 Python / 依赖检查以及请求标的的有效价格和更新时间，退出码为0。它只验证股票报价，不证明期权、日线权限或 MCP 宿主已接入。收盘后时间可能属于最近交易时段。

失败时按[排查指南](../guides/troubleshooting.md)区分安装、OpenD、登录、端口和行情权限；然后继续[快速上手](quickstart.md)或[配置 MCP](../guides/mcp-server.md)。

## 使用打包版

Windows 可从成功的 **Client platform CI** 下载 `moomoo-tools-Windows`，完整解压其中的 `MooPie-windows-x64.zip`，双击 `MooPie.exe`。macOS Apple Silicon 使用成功构建的 `MooPie-macos-arm64` DMG，拖到 Applications。

打包版无需另装 Python，仍需官方 OpenD 登录。Windows 是便携版；macOS 打包应用有独立的官方 OpenD 管理器。安装桌面应用不会自动为 agent 宿主配置 MCP。
