# Moomoo desktop client experiments

两个可独立打包的 macOS 行情客户端，用来比较 Python + Qt 与 SwiftUI + 官方 C++ SDK 的体验。

| 目录 | 界面 | OpenD 接入 |
| --- | --- | --- |
| `apps/python` | PySide6 / Qt Widgets | 官方 moomoo Python SDK 10.11.7108 |
| `apps/swift-cpp` | SwiftUI / Canvas | 官方 C++ SDK 10.11.7108，通过 C ABI 桥接 |

目前包含自选列表、搜索、行情表格、K 线与成交量、均线、周期切换和演示模式。不是官方 moomoo 的完整复制品；未实现交易、账户和资讯功能。演示行情是生成数据，不可用于投资决策。两版的演示与性能回放使用同一个合成行情文件 `fixtures/market.json`。

## 下载 runner 打包结果

打开仓库 **Actions → Package macOS clients → 成功的运行 → Artifacts**：

- `MooPython-macos-arm64`：应用 ZIP、界面预览、包体积 JSON 与逐轮性能记录。
- `MooSwiftCpp-macos-arm64`：应用 ZIP、界面预览、包体积 JSON 与逐轮性能记录。

还有 `macOS-performance-comparison`，包含对比表和原始结果，可直接在 Compare benchmark results 的 Summary 中查看。

外层 artifact ZIP 解压后，再解压内部应用 ZIP。当前为 Apple Silicon，系统要求 macOS 14 或以上。应用为 ad-hoc 签名，未使用 Apple Developer ID，也未公证；首次打开可能需要在系统隐私与安全设置中允许运行。

每次推送 main、创建 PR、推送 v 开头的 tag 都会触发构建；也可在 Actions 页面点 **Run workflow**。使用 GitHub 托管 macOS 15 runner，无需在个人 Mac 上安装 runner。产物保留 14 天。构建会下载并打包真实官方 OpenD；预览使用演示数据，无需账号、预先安装 OpenD 或 secret。

## 本地构建

Python 3.14；由于共用原生更新器，打包也需要 Xcode Command Line Tools：

```sh
cd apps/python
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements-build.txt
python3 -m unittest discover -s tests/unit -v
python3 -m unittest discover -s tests/integration -v
./scripts/build-app.sh
```

Swift / C++：安装 Xcode Command Line Tools 和 CMake 3.20+（CI 固定 4.1.2）。

```sh
cd apps/swift-cpp
./scripts/build-sdk.sh
swift test
./scripts/build-app.sh
```

C++ 构建脚本从 SDK 附带的源归档编译 protobuf 3.21.5 和 OpenSSL 3.0.17，随后编译官方 SDK。动态库会一起放进应用，运行不依赖本机 Homebrew。生成文件、构建缓存、虚拟环境和应用 ZIP 不进入 Git。

## 真实行情

打包版自动启动内置[官方 OpenD](https://www.moomoo.com/download/OpenAPI)，请在官方窗口登录，启用本机 API（通常 `127.0.0.1:11111`），再在客户端连接设置中填入同一地址和端口。这两个实验客户端仅支持本机未加密 API 连接。账号登录与行情权限由 OpenD 管理，CI 不会登录账号。两版均打包真实官方 OpenD，并共用自动更新器。

已验证构建、数据处理与协议校验；真实 OpenD 端到端联调和统一工作负载下的 CPU / 内存比较仍需进行。runner 自动进行三轮相同负载测试，记录 SDK 已加载时的启动、空闲/更新 CPU 与 RSS、离屏界面更新耗时；它不能代替真实 OpenD 和个人 Mac 上的交互比较。CPU 100% 代表一个核心，离屏截图耗时不是显示 FPS。两版 UI 框架不同，结果比较的是整套方案。

测试分层与当前覆盖范围见 [tests/README.md](tests/README.md)。两版使用原创共用图标；生成源码是 `scripts/render-icon.swift`，运行 `scripts/build-icon.sh` 可重建 icns。

## 第三方代码

`apps/swift-cpp/vendor/MMAPI4CPP_10.11.7108` 来自官方 SDK 下载包，保留原始版权声明与第三方归档；项目自有代码的 MIT 许可不覆盖此目录。Python SDK 与 Qt 等依赖保留各自许可。参见 [THIRD_PARTY.md](THIRD_PARTY.md)。

## Bundled real OpenD and automatic updates

Both macOS packages now include the **pristine official GUI moomoo OpenD 10.11.7108**, including its frameworks and login UI. It is a universal Intel/Apple Silicon binary. `runtime/opend.json` pins the official archive URL and SHA-256 for reproducible builds; its original Developer ID signature (Team ID `6HE4ZULJ45`, bundle ID `com.moomoo.opend`) is preserved. OpenD is proprietary third-party software and is not covered by this repository's MIT license.

On normal app startup, the native `OpenDManager` helper installs a shared runtime into `~/Library/Application Support/MooClients/OpenD`, opens the official login window, and checks for updates in the background. Both clients use this same gateway; an already running official OpenD is reused and never killed. Sign in through **OpenD's own window**, then use **Connect OpenD** in the client. Credentials are handled by official OpenD, not these clients. Closing either client leaves the shared gateway running. Previews, SDK tests and UI benchmarks do not auto-launch OpenD.

Updates are checked on startup (at most once per 24 hours) and every 24 hours while a client stays open. Settings provide **Launch / Login**, **Check updates**, and **Rollback**. The updater uses moomoo's latest-link endpoint and the official Futu endpoint as a version-only fallback; it always downloads the **moomoo** artifact over HTTPS. It checks bundle identity, expected version, CPU architecture, and the official publisher's signature before atomically changing the selected version. The currently running gateway is not restarted. Quit the official OpenD and launch it again to use the newly staged version; the preceding version remains available for rollback. Concurrent updates are prevented with a process lock. Failed downloads, invalid signatures and invalid packages leave the selected version unchanged. A launch-command failure attempts the previous version; failures after launch or account login still require manual rollback.

OpenD updates do **not** rewrite the Python or C++ SDK inside a signed/frozen client. SDK versions remain pinned and must be updated, tested and rebuilt when an API change requires it. Updating OpenD alone cannot guarantee perpetual API compatibility.

The official GUI OpenD currently occupies about **735 MiB**, so it dominates both package sizes. There is also one shared runtime copy on first launch, plus retained versions and official caches; previous small client-only package sizes no longer describe these bundles. UI benchmark CPU/RSS still measures only the client process, without a logged-in OpenD. Live end-to-end resource comparisons need a logged-in gateway on the same Mac.

The runners test the updater and actually launch the bundled, publisher-signed GUI OpenD for a five-second smoke test without account credentials. This verifies packaging and startup, **not** live quotes or account permissions.

```sh
swift test --package-path runtime
python3 scripts/smoke-opend.py apps/python/dist/MooPython.app artifacts/python-opend-smoke.json
python3 scripts/smoke-opend.py apps/swift-cpp/dist/MooSwiftCpp.app artifacts/swift-cpp-opend-smoke.json
```
