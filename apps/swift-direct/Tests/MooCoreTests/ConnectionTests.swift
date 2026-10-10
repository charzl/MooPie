import XCTest
import Network
import Foundation
@testable import MooCore

@MainActor
private final class MockOpenD {
    let listener: NWListener
    var connection: NWConnection?
    var decoder = FrameDecoder()
    var requests: [(UInt32, [String: Any])] = []
    init() throws { listener = try NWListener(using: .tcp, on: .any) }
    func start() async throws -> UInt16 {
        try await withCheckedThrowingContinuation { (continuation: CheckedContinuation<UInt16, Error>) in
            listener.stateUpdateHandler = { [weak self] state in
                Task { @MainActor in
                    guard let self else { return }
                    switch state {
                    case .ready: continuation.resume(returning: self.listener.port!.rawValue)
                    case .failed(let error): continuation.resume(throwing: error)
                    default: break
                    }
                }
            }
            listener.newConnectionHandler = { [weak self] connection in
                Task { @MainActor in
                    guard let self else { return }
                    self.connection = connection
                    connection.start(queue: DispatchQueue(label: "MooSwift.Test.Server"))
                    self.receive(connection)
                }
            }
            listener.start(queue: DispatchQueue(label: "MooSwift.Test.Listener"))
        }
    }
    func stop() { connection?.cancel(); listener.cancel() }
    func receive(_ connection: NWConnection) {
        connection.receive(minimumIncompleteLength: 1, maximumLength: 65_536) { [weak self] data, _, done, _ in
            Task { @MainActor in
                guard let self else { return }
                if let data {
                    do {
                        for frame in try self.decoder.append(data) {
                            let object = try frame.object
                            let payload = object["c2s"] as? [String: Any] ?? [:]
                            self.requests.append((frame.protocolID, payload))
                            var response: [String: Any] = ["retType": 0, "s2c": [:]]
                            switch frame.protocolID {
                            case 1001:
                                response["s2c"] = ["keepAliveInterval": 2, "connID": "123", "serverVer": 1000]
                            case 3004:
                                response["s2c"] = ["basicQotList": [["security": ["market": 11, "code": "AAPL"], "curPrice": 123.45, "lastClosePrice": 120, "volume": "9000"]]]
                            case 9998:
                                continue // deliberately silent to exercise disconnect cleanup
                            case 9999:
                                response = ["retType": -1, "retMsg": "missing market entitlement"]
                            default: break
                            }
                            self.send(frame.protocolID, frame.serial, response)
                        }
                    } catch { XCTFail(error.localizedDescription) }
                }
                if !done { self.receive(connection) }
            }
        }
    }
    func send(_ id: UInt32, _ serial: UInt32, _ object: [String: Any]) {
        let body = try! JSONSerialization.data(withJSONObject: object)
        let frame = Frame.encode(protocolID: id, serial: serial, body: body)
        // Explicitly split in the middle of the 44-byte header.
        connection?.send(content: Data(frame.prefix(13)), completion: .contentProcessed { _ in })
        connection?.send(content: Data(frame.dropFirst(13)), completion: .contentProcessed { _ in })
    }
}

final class ConnectionTests: XCTestCase {
    @MainActor func testHandshakeQuotePushErrorAndHeartbeat() async throws {
        let server = try MockOpenD(), client = OpenDClient()
        let port = try await server.start()
        defer { client.disconnect(); server.stop() }
        try await client.connect(host: "127.0.0.1", port: port)
        XCTAssertEqual(server.requests.first?.0, 1001)
        XCTAssertEqual(number(server.requests.first?.1["pushProtoFmt"]), 1)
        _ = try await client.request(3001, ["securityList": [["market": 11, "code": "AAPL"]], "subTypeList": [1], "isSubOrUnSub": true])
        let response = try await client.request(3004, ["securityList": [["market": 11, "code": "AAPL"]]])
        let quote = (response["basicQotList"] as? [[String: Any]])?.first.flatMap(Quote.init(json:))
        XCTAssertEqual(quote?.price, 123.45)
        let pushed = expectation(description: "unsolicited quote push")
        client.onPush = { id, data in
            XCTAssertEqual(id, 3005)
            XCTAssertEqual(number(data["marker"]), 42)
            pushed.fulfill()
        }
        server.send(3005, 0, ["retType": 0, "s2c": ["marker": 42]])
        await fulfillment(of: [pushed], timeout: 3)
        do { _ = try await client.request(9999, [:]); XCTFail("expected entitlement error") }
        catch { XCTAssertEqual(error.localizedDescription, "missing market entitlement") }
        try await Task.sleep(nanoseconds: 1_200_000_000)
        XCTAssertTrue(server.requests.contains { $0.0 == 1004 })
    }
    @MainActor func testDisconnectReleasesPendingRequestAndRejectsRemoteHost() async throws {
        let server = try MockOpenD(), client = OpenDClient()
        let port = try await server.start()
        defer { client.disconnect(); server.stop() }
        try await client.connect(host: "localhost", port: port)
        let request = Task { try await client.request(9998, [:]) }
        try await Task.sleep(nanoseconds: 50_000_000)
        client.disconnect()
        do { _ = try await request.value; XCTFail("expected cancellation") } catch { XCTAssertTrue(error is OpenDError) }
        do { try await client.connect(host: "192.0.2.1", port: port); XCTFail("remote host must be rejected") }
        catch { XCTAssertTrue(error.localizedDescription.contains("仅允许本机")) }
    }
}
