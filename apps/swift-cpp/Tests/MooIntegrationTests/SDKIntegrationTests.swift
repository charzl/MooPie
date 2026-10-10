import XCTest
import Foundation
@testable import MooCore
@testable import MooSwift
import AppKit
import SwiftUI

final class SDKIntegrationTests: XCTestCase {
    private func peer(arguments: [String] = []) throws -> (Process, UInt16, URL) {
        let root = URL(fileURLWithPath: #filePath).deletingLastPathComponent().deletingLastPathComponent().deletingLastPathComponent().deletingLastPathComponent().deletingLastPathComponent()
        let ready = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString + ".json")
        let process = Process(); process.executableURL = URL(fileURLWithPath: "/usr/bin/env")
        process.arguments = ["python3", root.appendingPathComponent("tests/support/mock_opend.py").path, "--ready-file", ready.path] + arguments
        process.standardOutput = FileHandle.nullDevice; process.standardError = FileHandle.nullDevice
        try process.run()
        let deadline = Date().addingTimeInterval(5)
        while !FileManager.default.fileExists(atPath: ready.path), Date() < deadline, process.isRunning { Thread.sleep(forTimeInterval: 0.02) }
        guard let data = try? Data(contentsOf: ready), let object = try JSONSerialization.jsonObject(with: data) as? [String: Any], let port = object["port"] as? Int else {
            if process.isRunning { process.terminate() }; throw OpenDError.server("Mock OpenD failed to start")
        }
        return (process, UInt16(port), ready)
    }
    private func stop(_ process: Process, _ ready: URL) { if process.isRunning { process.terminate(); process.waitUntilExit() }; try? FileManager.default.removeItem(at: ready) }

    @MainActor func testOfficialSDKConnectRequestPushAndReconnect() async throws {
        let (server, port, ready) = try peer(); defer { stop(server, ready) }
        let client = OpenDClient(); defer { client.disconnect() }
        let quotePush = expectation(description: "SDK quote push"), candlePush = expectation(description: "SDK candle push")
        var gotQuote = false, gotCandle = false
        client.onPush = { id, payload in
            if id == 3005, !gotQuote {
                let q = (payload["basicQotList"] as? [[String: Any]])?.first.flatMap(Quote.init(json:))
                XCTAssertEqual(q?.price, 111); gotQuote = true; quotePush.fulfill()
            }
            if id == 3007, !gotCandle {
                let c = (payload["klList"] as? [[String: Any]])?.first.flatMap(Candle.init(json:))
                XCTAssertEqual(c?.close, 112); gotCandle = true; candlePush.fulfill()
            }
        }
        try await client.connect(host: "127.0.0.1", port: port)
        _ = try await client.request(3001, ["securityList": [["market":11,"code":"AAPL"]], "subTypeList":[1], "isSubOrUnSub":true])
        let reply = try await client.request(3004, ["securityList": [["market":11,"code":"AAPL"]]])
        let quote = try XCTUnwrap((reply["basicQotList"] as? [[String: Any]])?.first.flatMap(Quote.init(json:)))
        XCTAssertEqual(quote.price, 110); XCTAssertEqual(quote.volume, 123456789)
        let kl = try await client.request(3006, ["security":["market":11,"code":"AAPL"],"rehabType":1,"klType":2,"reqNum":200])
        XCTAssertEqual((kl["klList"] as? [[String: Any]])?.count, 1)
        await fulfillment(of: [quotePush, candlePush], timeout: 3)
        client.disconnect()
        try await client.connect(host: "127.0.0.1", port: port)
        _ = try await client.request(3004, ["securityList": [["market":11,"code":"AAPL"]]])
    }
    @MainActor func testSubscriptionFailureIsReported() async throws {
        let (server, port, ready) = try peer(arguments:["--reject"]); defer { stop(server, ready) }
        let client = OpenDClient(); defer { client.disconnect() }
        try await client.connect(host:"127.0.0.1",port:port)
        do { _ = try await client.request(3001,["securityList":[["market":11,"code":"AAPL"]],"subTypeList":[1],"isSubOrUnSub":true]); XCTFail("Expected entitlement error") }
        catch { XCTAssertTrue(error.localizedDescription.contains("mock entitlement denied")) }
    }

    @MainActor func testUIModelSelectionPeriodAndRendering() throws {
        _ = NSApplication.shared
        let model = MarketModel(benchmark: true)
        XCTAssertEqual(model.watchlist.count, 13)
        XCTAssertEqual(model.candles.count, 180)
        let apple = try XCTUnwrap(Security(symbol: "US.AAPL"))
        model.select(apple); XCTAssertEqual(model.selected, apple)
        model.setPeriod(.week); XCTAssertEqual(model.period, .week); XCTAssertEqual(model.candles.count, 180)
        let host = NSHostingView(rootView: ContentView(model: model).frame(width: 1500, height: 900).environment(\.colorScheme, .dark))
        host.frame = NSRect(x: 0, y: 0, width: 1500, height: 900); host.layoutSubtreeIfNeeded()
        let bitmap = try XCTUnwrap(host.bitmapImageRepForCachingDisplay(in: host.bounds))
        host.cacheDisplay(in: host.bounds, to: bitmap)
        XCTAssertNotNil(bitmap.representation(using: .png, properties: [:]))
        model.disconnect(); XCTAssertFalse(model.connected)
    }
    @MainActor func testUIModelLiveDataAndDisconnect() async throws {
        let (server, port, ready) = try peer(); defer { stop(server, ready) }
        let model = MarketModel(benchmark: true)
        let apple = try XCTUnwrap(Security(symbol: "US.AAPL"))
        model.watchlist = [apple]; model.select(apple)
        await model.connect(host: "127.0.0.1", port: String(port))
        XCTAssertTrue(model.connected); XCTAssertNotNil(model.quotes[apple.id]); XCTAssertFalse(model.candles.isEmpty)
        model.disconnect(); XCTAssertFalse(model.connected); XCTAssertTrue(model.mode.contains("已断开"))
    }
    @MainActor func testUnexpectedServerDisconnectIsDelivered() async throws {
        let (server, port, ready) = try peer(arguments: ["--disconnect-after-quote"]); defer { stop(server, ready) }
        let client = OpenDClient(); defer { client.disconnect() }
        let disconnected = expectation(description: "SDK disconnect callback")
        var notified = false
        client.onDisconnect = { _ in if !notified { notified = true; disconnected.fulfill() } }
        try await client.connect(host: "127.0.0.1", port: port)
        _ = try? await client.request(3004, ["securityList": [["market":11,"code":"AAPL"]]])
        await fulfillment(of: [disconnected], timeout: 3)
    }
    @MainActor func testDisconnectedRequestAndRemoteAddressFail() async {
        let client = OpenDClient()
        do { _ = try await client.request(3004,[:]); XCTFail("Expected disconnected error") } catch {}
        do { try await client.connect(host:"example.com",port:11111); XCTFail("Expected loopback validation") } catch {}
    }
}
