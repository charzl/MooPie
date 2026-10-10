# MooSwift

原生 Swift + SwiftUI macOS 看盘客户端，按本机 moomoo 桌面版的深色「图表」页面重写。独立实现，不包含原客户端代码、品牌图片或 SDK 运行时。无第三方 Swift 依赖，不打包 Chromium、Node.js 或 Python。

## 使用

双击 `dist/MooSwift.app`。启动时显示醒目标记的**合成演示数据**，不代表实际价格。

真实行情：从 [moomoo 官方网站](https://www.moomoo.com/download/OpenAPI) 下载并启动 **OpenD**，在 OpenD 中完成登录。MooSwift 右上角「连接 OpenD」填写本机地址与端口（默认 `127.0.0.1:11111`）。支持未配置 RSA 加密的本机网关；不支持远程地址或加密网关，也不会修改 OpenD 的现有配置。账户行情权限、市场状态、订阅配额仍适用；连接成功不保证实时行情权限。

## 已实现

- 原版风格左侧导航、自选股双栏页面；表格与图表之间可拖动调整宽度。
- US / HK / SH / SZ 自选股添加、移除，特别关注、搜索、市场过滤、价格及涨幅排序；配置在本机保存。
- 报价订阅与推送、涨跌额/幅、盘后价（网关返回时）、报价更新时间。
- 日、周、月、1分、5分、15分、1小时 K 线与推送；前复权，最近 200 根。
- 原生 Canvas K 线、成交量、MA5/10/20/60，十字光标、缩放、收盘价曲线、红涨绿跌切换。
- TCP 包拆分/合并、44字节包头、SHA1 校验、JSON 编解码、请求序列匹配、超时、心跳及断线提示。

断开后保留上次数据并显示停更状态；不自动切换为示例价格。K 线订阅本次连接最多 60 组，可重新连接释放。自选股最多 30 只。

## 当前边界

复刻的是核心图表页面布局，并非原客户端全部页面或逐像素复制。账户、交易、下单、期权链、社区、AI、资讯、完整绘图工具及其他技术指标尚未实现；侧边导航相应入口会明确提示。无需原 moomoo 桌面 App，但仍依赖官方 OpenD。未做真实账户下单。实际账户行情需要用户在 OpenD 登录后验证。

## 开发

要求 macOS 14+、Xcode / Swift 5.9+。用 Xcode 打开 `Package.swift`，选择 MooSwift scheme 运行，或：

```sh
swift run MooSwift
swift test
bash scripts/build-app.sh
dist/MooSwift.app/Contents/MacOS/MooSwift --render-preview preview.png
```

构建脚本生成当前机器架构的 Release App 并作本机 ad-hoc 签名，没有 Apple 分发公证。`dist/` 和 `.build/` 不纳入源码。

## 协议来源与验证

根据官方 [OpenD 协议文档](https://openapi.moomoo.com/moomoo-api-doc/en/ftapi/protocol.html) 和 [Python SDK 协议定义](https://github.com/FutunnOpen/py-futu-api/tree/master/futu/common/pb) 独立实现 Swift 客户端。使用的协议 ID：InitConnect 1001、KeepAlive 1004、Qot_Sub 3001、Qot_GetBasicQot 3004、Qot_UpdateBasicQot 3005、Qot_GetKL 3006、Qot_UpdateKL 3007。

自动测试覆盖 TCP 任意分片、合并帧、损坏与超大帧拒绝、市场代码、字符串 int64、模拟网关握手/报价/推送/错误/心跳/断开。模拟网关通过不等于真实 OpenD 验证。

本次构建：5 项自动测试通过，Release App 约 1.3 MB（不含系统 SwiftUI 框架与外部 OpenD）。已检查离屏预览；由于 Mac 锁屏，未完成窗口内点击验证。本机未发现独立 OpenD 安装，未验证真实账户行情。
