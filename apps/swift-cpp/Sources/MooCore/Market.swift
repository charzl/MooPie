import Foundation

public struct Security: Codable, Hashable, Identifiable {
    public let market: Int
    public let code: String
    public var id: String { "\(prefix).\(code)" }
    public var prefix: String { [1: "HK", 11: "US", 21: "SH", 22: "SZ"][market] ?? "?" }
    public var json: [String: Any] { ["market": market, "code": code] }
    public init(market: Int, code: String) { self.market = market; self.code = code }
    public init?(symbol: String) {
        let parts = symbol.trimmingCharacters(in: .whitespacesAndNewlines).uppercased().split(separator: ".", maxSplits: 1)
        guard parts.count == 2, let market = ["US": 11, "HK": 1, "SH": 21, "SZ": 22][String(parts[0])] else { return nil }
        let code = String(parts[1])
        guard !code.isEmpty, code.count <= 32,
              code.allSatisfy({ $0.isASCII && ($0.isLetter || $0.isNumber || ".-_".contains($0)) }) else { return nil }
        self.init(market: market, code: code)
    }
    public init?(json: [String: Any]) {
        guard let code = json["code"] as? String else { return nil }
        self.init(market: Int(number(json["market"])), code: code)
    }
}

public struct Quote {
    public let security: Security
    public var name: String
    public var price: Double
    public var previousClose: Double
    public var open: Double
    public var high: Double
    public var low: Double
    public var volume: Double
    public var turnover: Double
    public var updated: String
    public var afterPrice: Double?
    public var change: Double { price - previousClose }
    public var changePercent: Double { previousClose == 0 ? 0 : change / previousClose * 100 }
    public init(security: Security, name: String, price: Double, previousClose: Double,
                open: Double, high: Double, low: Double, volume: Double, turnover: Double,
                updated: String, afterPrice: Double? = nil) {
        self.security = security; self.name = name; self.price = price; self.previousClose = previousClose
        self.open = open; self.high = high; self.low = low; self.volume = volume
        self.turnover = turnover; self.updated = updated; self.afterPrice = afterPrice
    }
    public init?(json: [String: Any]) {
        guard let sec = json["security"] as? [String: Any], let security = Security(json: sec) else { return nil }
        self.init(security: security, name: json["name"] as? String ?? security.code,
                  price: number(json["curPrice"]), previousClose: number(json["lastClosePrice"]),
                  open: number(json["openPrice"]), high: number(json["highPrice"]), low: number(json["lowPrice"]),
                  volume: number(json["volume"]), turnover: number(json["turnover"]),
                  updated: json["updateTime"] as? String ?? "",
                  afterPrice: (json["afterMarket"] as? [String: Any]).map { number($0["price"]) })
    }
}

public struct Candle: Identifiable {
    public let time: String
    public let open: Double
    public let high: Double
    public let low: Double
    public let close: Double
    public let volume: Double
    public var id: String { time }
    public init(time: String, open: Double, high: Double, low: Double, close: Double, volume: Double) {
        self.time = time; self.open = open; self.high = high; self.low = low; self.close = close; self.volume = volume
    }
    public init?(json: [String: Any]) {
        guard let time = json["time"] as? String, !(json["isBlank"] as? Bool ?? false),
              json["closePrice"] != nil, json["openPrice"] != nil else { return nil }
        self.init(time: time, open: number(json["openPrice"]), high: number(json["highPrice"]),
                  low: number(json["lowPrice"]), close: number(json["closePrice"]), volume: number(json["volume"]))
    }
}

public enum Period: String, CaseIterable, Identifiable {
    case day = "日K", week = "周K", month = "月K", minute = "1分", five = "5分", fifteen = "15分", hour = "1小时"
    public var id: String { rawValue }
    public var klType: Int {
        switch self { case .day: return 2; case .week: return 3; case .month: return 4
        case .minute: return 1; case .five: return 6; case .fifteen: return 7; case .hour: return 9 }
    }
    public var subType: Int {
        switch self { case .day: return 6; case .week: return 12; case .month: return 13
        case .minute: return 11; case .five: return 7; case .fifteen: return 8; case .hour: return 10 }
    }
}

public enum DemoMarket {
    private static let fixture: [String: Any]? = {
        let url = ProcessInfo.processInfo.environment["MOOMOO_BENCHMARK_FIXTURE"].map { URL(fileURLWithPath: $0) }
            ?? Bundle.main.url(forResource: "market", withExtension: "json")
        guard let url, let data = try? Data(contentsOf: url) else { return nil }
        return try? JSONSerialization.jsonObject(with: data) as? [String: Any]
    }()
    public static let symbols = ["US.PLTR", "US.INTC", "US.AVGO", "US.TEM", "US.NVDA", "US.AAPL", "US.AMZN", "US.MSFT", "US.TSLA", "HK.00700", "HK.00981", "HK.09988", "HK.01810"]
    public static let names = ["PLTR": "Palantir", "INTC": "英特尔", "AVGO": "博通", "TEM": "Tempus AI", "NVDA": "英伟达", "AAPL": "苹果", "AMZN": "亚马逊", "MSFT": "微软", "TSLA": "特斯拉", "00700": "腾讯控股", "00981": "中芯国际", "09988": "阿里巴巴-W", "01810": "小米集团-W"]
    // Fixed synthetic fixture: never presented as current market prices.
    public static func candles(for security: Security, period: Period) -> [Candle] {
        if let all = fixture?["candles"] as? [String: [String: [[String: Any]]]], let bars = all[security.id]?[period.rawValue] {
            return bars.compactMap(Candle.init(json:))
        }
        var seed = security.id.utf8.reduce(UInt64(17)) { $0 &* 31 &+ UInt64($1) } &+ UInt64(period.klType)
        func random() -> Double { seed = seed &* 6364136223846793005 &+ 1; return Double(seed >> 33) / Double(UInt32.max >> 1) }
        var price = 80.0 + Double(seed % 180)
        let calendar = Calendar(identifier: .gregorian)
        let base = Date(timeIntervalSince1970: 1735689600)
        let formatter = DateFormatter(); formatter.dateFormat = "yyyy-MM-dd HH:mm:ss"; formatter.timeZone = TimeZone(secondsFromGMT: 0)
        return (0..<180).map { i in
            let open = price
            price = max(5, open * (1 + (random() - 0.46) * 0.035))
            let high = max(open, price) * (1 + random() * 0.018)
            let low = min(open, price) * (1 - random() * 0.018)
            let minutes = [1: 1, 6: 5, 7: 15, 9: 60][period.klType]
            let date = minutes.map { base.addingTimeInterval(Double(i * $0 * 60)) }
                ?? calendar.date(byAdding: .day, value: i * (period == .week ? 7 : period == .month ? 30 : 1), to: base)!
            return Candle(time: formatter.string(from: date), open: open, high: high, low: low, close: price,
                          volume: 500_000 + random() * 12_000_000)
        }
    }
    public static func quote(for security: Security) -> Quote {
        if let all = fixture?["quotes"] as? [String: [String: Any]], let data = all[security.id], let quote = Quote(json: data) { return quote }
        let bars = candles(for: security, period: .day), last = bars.last!
        return Quote(security: security, name: names[security.code] ?? security.code,
                     price: last.close, previousClose: bars[bars.count - 2].close, open: last.open,
                     high: last.high, low: last.low, volume: last.volume, turnover: last.volume * last.close,
                     updated: "演示数据", afterPrice: nil)
    }
}
