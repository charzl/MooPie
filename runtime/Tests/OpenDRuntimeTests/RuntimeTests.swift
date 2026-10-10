import XCTest
@testable import OpenDRuntime
final class RuntimeTests: XCTestCase {
    func testNumericVersionsAndNoDowngrade() throws {
        XCTAssertTrue(try Policy.newer("10.11.7108", than: "10.9.6908"))
        XCTAssertFalse(try Policy.newer("10.11.7108", than: "10.11.7108"))
        XCTAssertFalse(try Policy.newer("10.9.6908", than: "10.11.7108"))
    }
    func testRejectsUntrustedRedirectAndTraversal() throws {
        for invalid in ["../x", "10.11.7108/../../x", "10.11", "10.-1.3", "10.11.7;rm", "10.11.٧"] { XCTAssertThrowsError(try Policy.parts(invalid)) }
        for url in ["http://softwaredownload.moomoo.com/moomoo_OpenD_10.11.7108_Mac.tar.gz", "https://evil.example/moomoo_OpenD_10.11.7108_Mac.tar.gz", "https://softwaredownload.moomoo.com.evil.example/moomoo_OpenD_10.11.7108_Mac.tar.gz", "https://www.moomoo.com/403"] { XCTAssertThrowsError(try Policy.versionFromRedirect("Location: \(url)\r\n")) }
    }
    func testOfficialFallbackUsesMoomooArtifact() throws {
        let version = try Policy.versionFromRedirect("HTTP/2 302\r\nlocation: https://softwaredownload.futunn.com/Futu_OpenD_10.11.7108_Mac.tar.gz\r\n")
        XCTAssertEqual(try Policy.downloadURL(version).host, "softwaredownload.moomoo.com")
        XCTAssertEqual(try Policy.downloadURL(version).lastPathComponent, "moomoo_OpenD_10.11.7108_Mac.tar.gz")
    }
    func withStore(_ body: (Store) throws -> Void) throws {
        let root = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        defer { try? FileManager.default.removeItem(at: root) }
        try body(Store(root: root))
    }
    func testFailedValidationPreservesCurrent() throws {
        try withStore { store in
            try store.save(Selection(current: "10.10.7008"))
            XCTAssertThrowsError(try store.activate("10.11.7108", validate: { _ in throw RuntimeError.invalid("signature rejected") }))
            XCTAssertEqual(try store.read()?.current, "10.10.7008")
        }
    }
    func testAtomicSwitchAndRollback() throws {
        try withStore { store in
            try store.activate("10.10.7008", validate: { _ in })
            try store.activate("10.11.7108", validate: { _ in })
            XCTAssertEqual(try store.read()?.previous, "10.10.7008")
            try store.rollback(validate: { _ in })
            XCTAssertEqual(try store.read()?.current, "10.10.7008")
            XCTAssertEqual(try store.read()?.previous, "10.11.7108")
            try store.rollback(validate: { _ in })
            XCTAssertEqual(try store.read()?.current, "10.11.7108")
        }
    }
    func testFailedRollbackAndOlderCandidatePreserveSelection() throws {
        try withStore { store in
            try store.save(Selection(current: "10.11.7108", previous: "10.10.7008"))
            let before = try store.read()
            XCTAssertThrowsError(try store.rollback(validate: { _ in throw RuntimeError.invalid("missing old bundle") }))
            try store.activate("10.9.6908", validate: { _ in })
            XCTAssertEqual(try store.read(), before)
        }
    }
    func testUpdateLockExcludesSecondClient() throws {
        try withStore { store in
            var first: Manager? = try Manager(root: store.root)
            try withExtendedLifetime(first) { XCTAssertThrowsError(try Manager(root: store.root)) }
            first = nil
            XCTAssertNoThrow(try Manager(root: store.root))
        }
    }
}
