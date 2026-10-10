import Foundation

public enum OpenDError: LocalizedError {
    case server(String), disconnected, timeout
    public var errorDescription: String? {
        switch self {
        case .server(let message): return message
        case .disconnected: return "OpenD 连接已断开。请启动 OpenD 并登录。"
        case .timeout: return "OpenD 请求超时。请检查端口、登录状态及加密配置。"
        }
    }
}

public func number(_ value: Any?) -> Double {
    if let number = value as? NSNumber { return number.doubleValue }
    if let text = value as? String { return Double(text) ?? 0 }
    return 0
}
