import Foundation
import SwiftUI
import MooCore

@MainActor
final class MarketModel: ObservableObject {
    @Published var watchlist: [Security]
    @Published var selected: Security
    @Published var quotes: [String: Quote] = [:]
    @Published var candles: [Candle] = []
    @Published var sparks: [String: [Double]] = [:]
    @Published var period: Period = .day
    @Published var mode = "演示数据"
    @Published var connected = false
    @Published var connecting = false
    @Published var loadingChart = false
    @Published var message = "演示数据 · 连接本机 OpenD 后显示实际行情"
    @Published var chartError: String?
    @Published var favorites: Set<String>
    @Published var redUp: Bool { didSet { UserDefaults.standard.set(redUp, forKey: "redUp") } }
    private let client = OpenDClient()
    private var chartRequest = UUID()
    private var session = UUID()
    private var subscriptions: Set<String> = []
    private var demo = true
    var currentQuote: Quote? { quotes[selected.id] }

    init() {
        let defaults = UserDefaults.standard
        let stored = defaults.stringArray(forKey: "watchlist") ?? DemoMarket.symbols
        var initial: [Security] = []
        for security in stored.compactMap(Security.init(symbol:)) where !initial.contains(security) { initial.append(security) }
        if initial.isEmpty { initial = DemoMarket.symbols.compactMap(Security.init(symbol:)) }
        watchlist = Array(initial.prefix(30))
        selected = initial[0]
        favorites = Set(defaults.stringArray(forKey: "favorites") ?? ["US.PLTR", "US.NVDA", "US.AAPL"])
        redUp = defaults.object(forKey: "redUp") as? Bool ?? true
        showDemo()
        client.onPush = { [weak self] id, data in self?.receivePush(id, data) }
        client.onDisconnect = { [weak self] error in
            guard let self else { return }
            self.connected = false; self.connecting = false
            self.mode = "已断开 · 数据已停更"; self.message = error
            self.session = UUID(); self.chartRequest = UUID(); self.loadingChart = false
        }
    }
    func color(_ change: Double) -> Color {
        if change == 0 { return Palette.text }
        return (change > 0) == redUp ? Palette.red : Palette.green
    }
    func showDemo() {
        session = UUID(); chartRequest = UUID(); client.disconnect()
        connected = false; connecting = false; demo = true; mode = "演示数据"
        quotes = Dictionary(uniqueKeysWithValues: watchlist.map { ($0.id, DemoMarket.quote(for: $0)) })
        sparks = Dictionary(uniqueKeysWithValues: watchlist.map { ($0.id, DemoMarket.candles(for: $0, period: .day).suffix(60).map(\.close)) })
        candles = DemoMarket.candles(for: selected, period: period)
        chartError = nil; loadingChart = false
        message = "演示数据 · 所有价格均为合成示例，连接 OpenD 后显示实际行情"
    }
    func disconnect() {
        session = UUID(); chartRequest = UUID(); client.disconnect(); connected = false; connecting = false
        loadingChart = false; mode = "已断开 · 数据已停更"; message = "连接已断开；屏幕保留上次数据"
    }
    func connect(host: String, port: String) async {
        guard !connecting else { return }
        guard let port = UInt16(port), port != 0 else { message = "请输入有效端口（1–65535）"; return }
        chartRequest = UUID(); loadingChart = false
        demo = false; quotes.removeAll(); sparks.removeAll(); candles.removeAll(); chartError = nil
        let token = UUID(); session = token
        connecting = true; mode = "连接中"; message = "正在连接本机 OpenD…"
        do {
            try await client.connect(host: host, port: port)
            guard token == session else { return }
            connected = true; connecting = false; subscriptions.removeAll(); mode = "OpenD 行情"
            message = "已连接 · 行情实时性取决于账户权限及市场状态"
            UserDefaults.standard.set(host, forKey: "host"); UserDefaults.standard.set(String(port), forKey: "port")
            await refresh()
        } catch {
            guard token == session else { return }
            connecting = false; connected = false; mode = "连接失败"; message = error.localizedDescription
            client.disconnect()
        }
    }
    func refresh() async {
        guard connected else { if demo { select(selected) }; return }
        let token = session
        // Separate requests isolate a missing entitlement for one market from all other stocks.
        var errors: [String] = []
        for security in watchlist {
            guard connected, token == session else { return }
            do {
                _ = try await client.request(3001, ["securityList": [security.json], "subTypeList": [1],
                                                    "isSubOrUnSub": true, "isRegOrUnRegPush": true])
                let data = try await client.request(3004, ["securityList": [security.json]])
                guard token == session else { return }
                applyQuotes(data)
            } catch { errors.append("\(security.id)：\(error.localizedDescription)") }
        }
        guard token == session else { return }
        message = errors.isEmpty ? "已更新 · 行情实时性取决于账户权限及市场状态" : errors.joined(separator: "；")
        await loadChart()
    }
    func select(_ security: Security) {
        selected = security; chartRequest = UUID(); chartError = nil; candles = []
        if demo { candles = DemoMarket.candles(for: security, period: period) }
        else if connected { Task { await loadChart() } }
    }
    func setPeriod(_ value: Period) { period = value; select(selected) }
    func loadChart() async {
        guard connected else { return }
        let token = UUID(); chartRequest = token
        let security = selected, period = period
        loadingChart = true; chartError = nil
        do {
            let key = "\(security.id):\(period.subType)"
            if !subscriptions.contains(key) {
                guard subscriptions.count < 60 else { throw OpenDError.server("本次连接已订阅 60 组 K 线，请重新连接以释放订阅") }
                _ = try await client.request(3001, ["securityList": [security.json], "subTypeList": [period.subType],
                                                    "isSubOrUnSub": true, "isRegOrUnRegPush": true,
                                                    "regPushRehabTypeList": [1]])
                guard chartRequest == token, connected else { return }
                subscriptions.insert(key)
            }
            let data = try await client.request(3006, ["security": security.json, "klType": period.klType,
                                                        "rehabType": 1, "reqNum": 200])
            guard chartRequest == token, connected else { return }
            candles = (data["klList"] as? [[String: Any]] ?? []).compactMap(Candle.init(json:)).sorted { $0.time < $1.time }
            loadingChart = false
            if candles.isEmpty { chartError = "OpenD 暂未返回 K 线，请检查行情权限或稍后刷新" }
        } catch {
            guard chartRequest == token else { return }
            loadingChart = false; chartError = error.localizedDescription
        }
    }
    func applyQuotes(_ data: [String: Any]) {
        for item in data["basicQotList"] as? [[String: Any]] ?? [] {
            guard var quote = Quote(json: item), watchlist.contains(quote.security) else { continue }
            if quote.name == quote.security.code {
                quote.name = quotes[quote.security.id]?.name ?? DemoMarket.names[quote.security.code] ?? quote.name
            }
            quotes[quote.security.id] = quote
            var points = sparks[quote.security.id] ?? []
            points.append(quote.price); sparks[quote.security.id] = Array(points.suffix(80))
        }
    }
    private func receivePush(_ id: UInt32, _ data: [String: Any]) {
        // OpenD can push data during handshake; do not lose initial quote updates.
        guard !demo else { return }
        if id == 3005 { applyQuotes(data) }
        if id == 3007, let sec = data["security"] as? [String: Any], Security(json: sec) == selected,
           Int(number(data["klType"])) == period.klType, Int(number(data["rehabType"])) == 1 {
            let incoming = (data["klList"] as? [[String: Any]] ?? []).compactMap(Candle.init(json:))
            var merged = Dictionary(uniqueKeysWithValues: candles.map { ($0.time, $0) })
            incoming.forEach { merged[$0.time] = $0 }
            candles = Array(merged.values.sorted { $0.time < $1.time }.suffix(200))
        }
    }
    func add(_ symbol: String) -> String? {
        guard let security = Security(symbol: symbol) else { return "请输入 US.AAPL、HK.00700、SH.600519 或 SZ.000001" }
        guard !watchlist.contains(security) else { select(security); return nil }
        guard watchlist.count < 30 else { return "最多支持 30 只自选股" }
        watchlist.append(security); persist()
        if demo {
            quotes[security.id] = DemoMarket.quote(for: security)
            sparks[security.id] = DemoMarket.candles(for: security, period: .day).suffix(60).map(\.close)
        }
        select(security)
        if connected { Task { await refresh() } }
        return nil
    }
    func remove(_ security: Security) {
        guard watchlist.count > 1 else { message = "请至少保留一只自选股"; return }
        watchlist.removeAll { $0 == security }; quotes.removeValue(forKey: security.id); favorites.remove(security.id); persist()
        if selected == security { select(watchlist[0]) }
        if connected {
            Task {
                do { _ = try await client.request(3001, ["securityList": [security.json], "subTypeList": [1], "isSubOrUnSub": false, "isRegOrUnRegPush": false]) }
                catch { message = "取消订阅：\(error.localizedDescription)" }
            }
        }
    }
    func favorite(_ security: Security) {
        if favorites.contains(security.id) { favorites.remove(security.id) } else { favorites.insert(security.id) }
        persist()
    }
    private func persist() {
        UserDefaults.standard.set(watchlist.map(\.id), forKey: "watchlist")
        UserDefaults.standard.set(Array(favorites), forKey: "favorites")
    }
}
