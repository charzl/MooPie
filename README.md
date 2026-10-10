# Moomoo desktop client experiments

两个可独立打包的 macOS 行情客户端，用来比较 Python + Qt 与 SwiftUI + 官方 C++ SDK 的体验。

| 目录 | 界面 | OpenD 接入 |
| --- | --- | --- |
| `apps/python` | PySide6 / Qt Widgets | 官方 moomoo Python SDK 10.11.7108 |
| `apps/swift-cpp` | SwiftUI / Canvas | 官方 C++ SDK 10.11.7108，通过 C ABI 桥接 |
| `apps/swift-direct` | SwiftUI / Canvas | 原始纯 Swift JSON 协议版，保留为参考 |

目前包含自选列表、搜索、行情表格、K 线与成交量、均线、周期切换和演示模式。不是官方 moomoo 的完整复制品；未实现交易、账户和资讯功能。演示行情是生成数据，不可用于投资决策。两版当前演示生成器不同，不能据此认定某种语言性能更好。

## 下载 runner 打包结果

打开仓库 **Actions → Package macOS clients → 成功的运行 → Artifacts**：

- `MooPython-macos-arm64`：应用 ZIP、界面预览和包体积 JSON。
- `MooSwiftCpp-macos-arm64`：应用 ZIP、界面预览和包体积 JSON。

外层 artifact ZIP 解压后，再解压内部应用 ZIP。当前为 Apple Silicon，系统要求 macOS 14 或以上。应用为 ad-hoc 签名，未使用 Apple Developer ID，也未公证；首次打开可能需要在系统隐私与安全设置中允许运行。

每次推送 main、创建 PR、推送 v 开头的 tag 都会触发构建；也可在 Actions 页面点 **Run workflow**。使用 GitHub 托管 macOS 15 runner，无需在个人 Mac 上安装 runner。产物保留 14 天。构建与预览使用演示数据，无需账号、OpenD 或 secret。

## 本地构建

Python 3.14：

```sh
cd apps/python
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements-build.txt
python3 -m unittest discover -s tests -v
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

纯 Swift 参考版：`cd apps/swift-direct && swift test && ./scripts/build-app.sh`。

## 真实行情

单独安装并登录[官方 OpenD](https://www.moomoo.com/download/OpenAPI)，启用本机 API（通常 `127.0.0.1:11111`），再在客户端连接设置中填入同一地址和端口。这两个实验客户端仅支持本机未加密 API 连接。账号登录与行情权限由 OpenD 管理，CI 不会登录账号。未随应用打包 OpenD。

已验证构建、数据处理与协议校验；真实 OpenD 端到端联调和统一工作负载下的 CPU / 内存比较仍需进行。runner 记录的是包体积，不能代替个人 Mac 上同一数据、同一订阅、同一操作的性能比较。

## 第三方代码

`apps/swift-cpp/vendor/MMAPI4CPP_10.11.7108` 来自官方 SDK 下载包，保留原始版权声明与第三方归档；项目自有代码的 MIT 许可不覆盖此目录。Python SDK 与 Qt 等依赖保留各自许可。参见 [THIRD_PARTY.md](THIRD_PARTY.md)。
