import XCTest
import MooBridge
final class BridgeTests: XCTestCase {
 func testOfficialSDKRequestValidation() {
  XCTAssertEqual(moo_cpp_validate_request(3001, #"{"c2s":{"securityList":[{"market":11,"code":"AAPL"}],"subTypeList":[1],"isSubOrUnSub":true}}"#), 1)
  XCTAssertEqual(moo_cpp_validate_request(3006, #"{"c2s":{"security":{"market":11,"code":"AAPL"},"klType":2,"rehabType":1,"reqNum":200}}"#), 1)
  XCTAssertEqual(moo_cpp_validate_request(3006, #"{"c2s":{}}"#), 0)
  XCTAssertEqual(moo_cpp_validate_request(3004, "invalid json"), 0)
  XCTAssertEqual(moo_cpp_validate_request(9999, #"{"c2s":{}}"#), 0)
 }
}
