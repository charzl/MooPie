import Foundation
import CryptoKit

public enum OpenDError: LocalizedError {
    case invalidFrame(String), server(String), disconnected, timeout
    public var errorDescription: String? {
        switch self {
        case .invalidFrame(let reason): return "OpenD 协议错误：\(reason)"
        case .server(let message): return message
        case .disconnected: return "OpenD 连接已断开。请启动 OpenD 并登录。"
        case .timeout: return "OpenD 请求超时。请检查端口、登录状态及加密配置。"
        }
    }
}

public struct Frame {
    public let protocolID: UInt32
    public let serial: UInt32
    public let body: Data
    public var object: [String: Any] {
        get throws {
            guard let result = try JSONSerialization.jsonObject(with: body) as? [String: Any] else {
                throw OpenDError.invalidFrame("JSON 根节点无效")
            }
            return result
        }
    }
    public static func encode(protocolID: UInt32, serial: UInt32, body: Data) -> Data {
        var data = Data([0x46, 0x54])
        data.appendLE(protocolID)
        data.append(contentsOf: [1, 0]) // JSON, protocol version zero
        data.appendLE(serial)
        data.appendLE(UInt32(body.count))
        data.append(contentsOf: Insecure.SHA1.hash(data: body))
        data.append(Data(repeating: 0, count: 8))
        data.append(body)
        return data
    }
}

/// TCP may split a header or coalesce several responses. Never assume receive boundaries.
public struct FrameDecoder {
    private var buffer = Data()
    public init() {}
    public mutating func append(_ bytes: Data) throws -> [Frame] {
        buffer.append(bytes)
        var frames: [Frame] = []
        while buffer.count >= 44 {
            guard buffer[0] == 0x46, buffer[1] == 0x54 else {
                throw OpenDError.invalidFrame("包头无效；此版本仅支持本机未加密 OpenD")
            }
            guard buffer[6] == 1, buffer[7] == 0 else {
                throw OpenDError.invalidFrame("需要 JSON 协议格式")
            }
            let length = Int(buffer.uint32LE(at: 12))
            guard length <= 16 * 1024 * 1024 else { throw OpenDError.invalidFrame("包体过大") }
            guard buffer.count >= 44 + length else { break }
            let body = Data(buffer[44..<(44 + length)])
            guard Data(Insecure.SHA1.hash(data: body)) == Data(buffer[16..<36]) else {
                throw OpenDError.invalidFrame("SHA1 校验失败")
            }
            frames.append(Frame(protocolID: buffer.uint32LE(at: 2), serial: buffer.uint32LE(at: 8), body: body))
            buffer = Data(buffer.dropFirst(44 + length))
        }
        return frames
    }
}

extension Data {
    mutating func appendLE(_ value: UInt32) {
        append(contentsOf: (0..<4).map { UInt8(truncatingIfNeeded: value >> ($0 * 8)) })
    }
    func uint32LE(at offset: Int) -> UInt32 {
        (0..<4).reduce(UInt32(0)) { $0 | UInt32(self[offset + $1]) << ($1 * 8) }
    }
}

public func number(_ value: Any?) -> Double {
    if let number = value as? NSNumber { return number.doubleValue }
    if let text = value as? String { return Double(text) ?? 0 }
    return 0
}
