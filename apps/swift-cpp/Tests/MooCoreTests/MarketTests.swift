import XCTest
import Foundation
@testable import MooCore

final class MarketTests: XCTestCase {
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
