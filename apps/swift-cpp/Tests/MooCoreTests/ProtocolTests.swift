import XCTest
import Foundation
import CryptoKit
@testable import MooCore

final class ProtocolTests: XCTestCase {
    func testFragmentedAndCoalescedFrames() throws {
        let body = Data(#"{"retType":0,"s2c":{"curPrice":123.45}}"#.utf8)
        let packet = Frame.encode(protocolID: 3004, serial: 42, body: body)
        XCTAssertEqual(packet.count, 44 + body.count)
        XCTAssertEqual(Array(packet.prefix(16)), [70, 84, 188, 11, 0, 0, 1, 0, 42, 0, 0, 0, UInt8(body.count), 0, 0, 0])
        for split in 1..<packet.count {
            var decoder = FrameDecoder()
            XCTAssertTrue(try decoder.append(Data(packet.prefix(split))).isEmpty)
            let decoded = try decoder.append(Data(packet.dropFirst(split)) + packet)
            XCTAssertEqual(decoded.count, 2)
            XCTAssertEqual(decoded[0].protocolID, 3004)
            XCTAssertEqual(decoded[0].serial, 42)
            let object = try decoded[0].object
            XCTAssertEqual(number((object["s2c"] as? [String: Any])?["curPrice"]), 123.45)
        }
    }
    func testRejectsCorruptionAndUnsupportedProtocol() throws {
        let body = Data(#"{"retType":0}"#.utf8)
        let packet = Frame.encode(protocolID: 1001, serial: 1, body: body)
        for offset in [0, 6, 7, 16, 44] {
            var broken = packet; broken[offset] ^= 0xff
            var decoder = FrameDecoder()
            XCTAssertThrowsError(try decoder.append(broken))
        }
        var oversized = packet
        oversized.replaceSubrange(12..<16, with: [0xff, 0xff, 0xff, 0x7f])
        var decoder = FrameDecoder()
        XCTAssertThrowsError(try decoder.append(oversized))
    }
    func testMarketIdentityAndInt64JSON() {
        XCTAssertEqual(Security(symbol: " hk.00700 ")?.market, 1)
        XCTAssertEqual(Security(symbol: "US.BRK.B")?.code, "BRK.B")
        XCTAssertNil(Security(symbol: "AAPL"))
        XCTAssertNil(Security(symbol: "US.bad symbol"))
        let quote = Quote(json: ["security": ["market": 11, "code": "AAPL"], "curPrice": 110.0,
                                 "lastClosePrice": 100.0, "volume": "123456789", "updateTime": "2026-10-10 09:30:00"])
        XCTAssertEqual(quote?.changePercent, 10)
        XCTAssertEqual(quote?.volume, 123456789)
        XCTAssertNil(Candle(json: ["time": "2026-01-01", "isBlank": true]))
    }
}
