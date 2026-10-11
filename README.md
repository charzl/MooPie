# Moomoo desktop client experiments

两个可独立打包的 macOS 行情客户端，用来比较 Python + Qt 与 SwiftUI + 官方 C++ SDK 的体验。

| 目录 | 界面 | OpenD 接入 |
| --- | --- | --- |
| `apps/python` | PySide6 / Qt Widgets | 官方 moomoo Python SDK 10.11.7108 |
| `apps/swift-cpp` | SwiftUI / Canvas | 官方 C++ SDK 10.11.7108，通过 C ABI 桥接 |

目前包含自选列表、搜索、行情表格、K 线与成交量、均线、周期切换和演示模式。Python 客户端命名为 MooPie，优先推进功能：官方自选分组导入和全宽观察表、期权到期日与 Call/Put 合约链及报价、市场总览，以及账户现金/资产/盈亏、持仓、订单、成交历史和资金明细只读查询；Swift/C++ 版保留作对照。未实现下单和完整资讯功能。市场数据受公开 API 覆盖和账户权限限制，美股总览使用明确标注的 ETF，未伪装成美股指数；外汇和未覆盖的全球市场不会填入演示值。演示行情是生成数据，不可用于投资决策。两版的演示与性能回放使用同一个合成行情文件 `fixtures/market.json`。

## 下载 runner 打包结果

打开仓库 **Actions → Package Python macOS client → 成功的运行 → Artifacts**：

- `MooPie-macos-arm64`：DMG 安装包、界面预览、包体积 JSON 和安装包校验结果。

日常 CI 只构建 Python 版，不运行性能测试或 Swift/C++ 打包。Swift/C++ 源码保留供以后使用。安装包由 CI 生成，本地只做开发和必要测试。手动触发：`gh workflow run package-python.yml --ref main -f force=true`。

外层 artifact ZIP 解压后，打开 DMG，将应用拖入 Applications。也可从仓库 Releases 直接下载 DMG。当前为 Apple Silicon，系统要求 macOS 14 或以上。客户端为 ad-hoc 签名，尚未公证；首次打开可能需要在系统隐私与安全设置中允许运行。内置 OpenD 保留官方签名。

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

Python 版连接后，点击自选列表旁的 **moomoo 自选**，获取分组、读取分组，再点击导入；导入替换本地列表并保存前一列表备份，不修改官方账号自选。完整显示当前支持的 US/HK/SH/SZ 标的；同时最多订阅 30 只报价，其余选中后按需读取，并释放旧订阅。K 线保留最多 60 组近期订阅，超出时释放旧订阅。其他市场暂时跳过并显示数量。

侧栏 **账户** 使用主窗口内的账户列表、持仓和资产页签。选择开户券商、交易市场、币种，获取账户后点击账户卡片或“刷新资产与持仓”。区分实盘和模拟账户，账户 ID 保持完整精度，查询失败或切换连接时清空旧数据。只读查询不保存资产/持仓到磁盘；尚未接入的订单、历史和资金明细页签禁用。账户页参考官方布局，但不是所有官方功能的完整复制。

独立每日扫描模块见 [modules/rule-engine](modules/rule-engine/README.md)：标准化日线输入、版本化 JSON 规则、MA50 等指标与逐条命中证据，输出可供 Codex 读取的 JSON。模块有独立 wheel 构建和测试流程，当前尚未接入客户端的真实行情采集或 AI 调用。

打包版自动启动内置[官方 OpenD](https://www.moomoo.com/download/OpenAPI)，请在官方窗口登录，启用本机 API（通常 `127.0.0.1:11111`），再在客户端连接设置中填入同一地址和端口。这两个实验客户端仅支持本机未加密 API 连接。账号登录与行情权限由 OpenD 管理，CI 不会登录账号。两版均打包真实官方 OpenD，并共用自动更新器。

已验证构建、数据处理与协议校验；真实 OpenD 端到端联调和统一工作负载下的 CPU / 内存比较仍需进行。runner 自动进行三轮相同负载测试，记录 SDK 已加载时的启动、空闲/更新 CPU 与 RSS、离屏界面更新耗时；它不能代替真实 OpenD 和个人 Mac 上的交互比较。CPU 100% 代表一个核心，离屏截图耗时不是显示 FPS。两版 UI 框架不同，结果比较的是整套方案。

测试分层与当前覆盖范围见 [tests/README.md](tests/README.md)。两版使用原创共用图标；生成源码是 `scripts/render-icon.swift`，运行 `scripts/build-icon.sh` 可重建 icns。

## 第三方代码

`apps/swift-cpp/vendor/MMAPI4CPP_10.11.7108` 来自官方 SDK 下载包，保留原始版权声明与第三方归档；项目自有代码的 MIT 许可不覆盖此目录。Python SDK 与 Qt 等依赖保留各自许可。参见 [THIRD_PARTY.md](THIRD_PARTY.md)。

## Bundled real OpenD and automatic updates

Both macOS packages now include the **pristine official GUI moomoo OpenD 10.11.7108**, including its frameworks and login UI. It is a universal Intel/Apple Silicon binary. `runtime/opend.json` pins the official archive URL and SHA-256 for reproducible builds; its original Developer ID signature (Team ID `6HE4ZULJ45`, bundle ID `com.moomoo.opend`) is preserved. OpenD is proprietary third-party software and is not covered by this repository's MIT license.

On normal app startup, the native `OpenDManager` helper installs a shared runtime into `~/Library/Application Support/MooClients/OpenD`, opens the official login window, and checks for updates in the background. Both clients use this same gateway; an already running official OpenD is reused and never killed. Sign in through **OpenD's own window**, then use **Connect OpenD** in the client. Credentials are handled by official OpenD, not these clients. Closing either client leaves the shared gateway running. Previews, SDK tests and UI benchmarks do not auto-launch OpenD.

Updates are checked on startup (at most once per 24 hours) and every 24 hours while a client stays open. Settings provide **Launch / Login**, **Check updates**, and **Rollback**. The updater uses moomoo's latest-link endpoint and the official Futu endpoint as a version-only fallback; it always downloads the **moomoo** artifact over HTTPS. It checks bundle identity, expected version, CPU architecture, and the official publisher's signature before atomically changing the selected version. The currently running gateway is not restarted. Quit the official OpenD and launch it again to use the newly staged version; the preceding version remains available for rollback. Concurrent updates are prevented with a process lock. Failed downloads, invalid signatures and invalid packages leave the selected version unchanged. A launch-command failure attempts the previous version; failures after launch or account login still require manual rollback.

OpenD updates do **not** rewrite the Python or C++ SDK inside a signed/frozen client. Local builds use pinned SDK versions; CI automatically resolves official SDK updates, tests and rebuilds both clients, and publishes new installers only when all checks pass. Updating OpenD alone cannot guarantee perpetual API compatibility.

The official GUI OpenD currently occupies about **735 MiB**, so it dominates both package sizes. There is also one shared runtime copy on first launch, plus retained versions and official caches; previous small client-only package sizes no longer describe these bundles. UI benchmark CPU/RSS still measures only the client process, without a logged-in OpenD. Live end-to-end resource comparisons need a logged-in gateway on the same Mac.

The runners test the updater and actually launch the bundled, publisher-signed GUI OpenD for a five-second smoke test without account credentials. This verifies packaging and startup, **not** live quotes or account permissions.

```sh
swift test --package-path runtime
python3 scripts/smoke-opend.py apps/python/dist/MooPie.app artifacts/python-opend-smoke.json
python3 scripts/smoke-opend.py apps/swift-cpp/dist/MooSwiftCpp.app artifacts/swift-cpp-opend-smoke.json
```

## Automatic CI upgrades and DMG releases

[Releases](https://github.com/charzl/moomoo-clients/releases) contains drag-to-Applications Python DMG installers as experimental prereleases. The workflow checks official SDK/OpenD versions daily, on main pushes and on manual dispatch. A compatible Python SDK/OpenD pair is resolved for the Python client. The official Python source distribution is hash-pinned; SDK directories, bundled dependency archives and dylib identities are read from build metadata instead of a fixed version path.

Upgrades happen in ephemeral CI checkouts, without automatically changing the main branch. Local source defaults stay pinned in `runtime/sdk.json` and `runtime/opend.json`. Each release includes `resolved-build.json` with the actual source commit, SDK/OpenD versions, official URLs and SHA-256 hashes, plus `SHA256SUMS.txt` for the Python installer.

Publication requires Python unit and integration tests, real OpenD update/startup acceptance, mounted-DMG identity/signature checks. Downloads, hashes, incompatible versions, compilation or tests failing prevent publication; the previous Release is never overwritten. Breaking API changes may still require changes to our adapter code; CI does not automatically repair application code.

Already published source/version combinations skip the expensive builds. Manual dispatch offers `force` to create another build. The Python installer and validation evidence are uploaded to a draft first; the draft becomes public only when every asset's name and size is verified. Releases persist; Actions artifacts expire after 14 days. GitHub scheduled workflows can run late and must remain enabled on the default branch.

Installed OpenD's own automatic updates and CI's SDK-driven client rebuilds are separate. Download the new client DMG from Releases to replace an installed client.
