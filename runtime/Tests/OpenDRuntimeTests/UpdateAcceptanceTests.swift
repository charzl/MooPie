import XCTest
@testable import OpenDRuntime
/// Real official artifact download, DMG extraction, signature validation and atomic selection.
/// Opt in explicitly: this downloads ~400MB and never logs in or opens the account UI.
final class UpdateAcceptanceTests: XCTestCase {
    func testOfficialDownloadAndAtomicInstallation() throws {
        guard ProcessInfo.processInfo.environment["MOOMOO_OPEND_UPDATE_ACCEPTANCE"] == "1" else { throw XCTSkip("Set MOOMOO_OPEND_UPDATE_ACCEPTANCE=1 for real network update acceptance") }
        let root = FileManager.default.temporaryDirectory.appendingPathComponent("opend-update-\(UUID().uuidString)")
        defer { try? FileManager.default.removeItem(at: root) }
        let manager = try Manager(root: root)
        // A sentinel selection makes a clean test store traverse the update path.
        // It is not a mock OpenD binary; the candidate is the genuine official download.
        try manager.store.save(Selection(current: "0.0.0"))
        _ = try manager.update(force: true)
        let selected = try XCTUnwrap(manager.store.read())
        XCTAssertTrue(try Policy.newer(selected.current, than: "0.0.0"))
        try manager.validate(manager.store.app(selected.current), version: selected.current)
        XCTAssertEqual(selected.previous, "0.0.0")
        // Cached reinstall/reselection must not overwrite a running or valid signed bundle.
        try manager.store.save(Selection(current: "0.0.0", previous: selected.current))
        let reused = try manager.update(force: true)
        XCTAssertTrue(reused.contains("已校验并选中"))
        XCTAssertEqual(try manager.store.read()?.current, selected.current)
        // Rollback to the sentinel must fail validation and preserve the installed candidate.
        XCTAssertThrowsError(try manager.store.rollback(validate: { try manager.validate($0) }))
        XCTAssertEqual(try manager.store.read()?.current, selected.current)
        XCTAssertFalse(try FileManager.default.contentsOfDirectory(at: root, includingPropertiesForKeys: nil).contains { $0.lastPathComponent.hasPrefix("staging-") })
    }
}
