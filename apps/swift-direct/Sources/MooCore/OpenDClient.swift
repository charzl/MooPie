import Foundation
import Network

@MainActor
public final class OpenDClient {
    private var connection: NWConnection?
    private var decoder = FrameDecoder()
    private var serial: UInt32 = 0
    private var generation = UUID()
    private var readiness: CheckedContinuation<Void, Error>?
    private var pending: [UInt32: (UInt32, CheckedContinuation<[String: Any], Error>, Task<Void, Never>)] = [:]
    private var heartbeat: Task<Void, Never>?
    public var onPush: ((UInt32, [String: Any]) -> Void)?
    public var onDisconnect: ((String) -> Void)?
    public init() {}

    public func connect(host: String, port: UInt16) async throws {
        guard ["localhost", "127.0.0.1", "::1"].contains(host) else {
            throw OpenDError.server("此版本仅允许本机 OpenD（localhost / 127.0.0.1 / ::1）")
        }
        disconnect()
        let token = generation
        let connection = NWConnection(host: NWEndpoint.Host(host == "localhost" ? "127.0.0.1" : host),
                                      port: NWEndpoint.Port(rawValue: port)!, using: .tcp)
        self.connection = connection
        try await withCheckedThrowingContinuation { (continuation: CheckedContinuation<Void, Error>) in
            readiness = continuation
            connection.stateUpdateHandler = { [weak self] state in
                Task { @MainActor in
                    guard let self, self.generation == token else { return }
                    switch state {
                    case .ready:
                        self.readiness?.resume(); self.readiness = nil
                        self.receive(connection, token: token)
                    case .failed(let error): self.fail(error)
                    case .cancelled: self.fail(OpenDError.disconnected)
                    default: break
                    }
                }
            }
            connection.start(queue: DispatchQueue(label: "MooSwift.OpenD"))
            Task { [weak self] in
                try? await Task.sleep(nanoseconds: 8_000_000_000)
                guard let self, self.generation == token, self.readiness != nil else { return }
                self.fail(OpenDError.timeout)
            }
        }
        guard generation == token else { throw OpenDError.disconnected }
        let hello = try await request(1001, ["clientVer": 100, "clientID": "MooSwift-\(UUID().uuidString)",
                                             "recvNotify": false, "pushProtoFmt": 1, "programmingLanguage": "Swift"])
        guard generation == token else { throw OpenDError.disconnected }
        let interval = max(1, number(hello["keepAliveInterval"]) / 2)
        heartbeat = Task { [weak self] in
            while !Task.isCancelled {
                do { try await Task.sleep(nanoseconds: UInt64(interval * 1_000_000_000)) }
                catch { return }
                guard let self, self.generation == token else { return }
                do { _ = try await self.request(1004, ["time": String(Int(Date().timeIntervalSince1970))]) }
                catch { if self.generation == token { self.fail(error) }; return }
            }
        }
    }

    public func disconnect() {
        generation = UUID()
        heartbeat?.cancel(); heartbeat = nil
        let old = connection; connection = nil; old?.cancel()
        readiness?.resume(throwing: OpenDError.disconnected); readiness = nil
        let requests = pending; pending.removeAll()
        for (_, continuation, timer) in requests.values { timer.cancel(); continuation.resume(throwing: OpenDError.disconnected) }
        decoder = FrameDecoder()
    }
    private func fail(_ error: Error) {
        disconnect()
        onDisconnect?(error.localizedDescription)
    }

    public func request(_ protocolID: UInt32, _ payload: [String: Any]) async throws -> [String: Any] {
        guard let connection else { throw OpenDError.disconnected }
        let body = try JSONSerialization.data(withJSONObject: ["c2s": payload], options: [.sortedKeys])
        serial &+= 1
        if serial == 0 { serial = 1 }
        let sequence = serial, token = generation
        return try await withCheckedThrowingContinuation { continuation in
            let timer = Task { [weak self] in
                do { try await Task.sleep(nanoseconds: 10_000_000_000) } catch { return }
                guard let self, self.generation == token,
                      let (_, waiting, _) = self.pending.removeValue(forKey: sequence) else { return }
                waiting.resume(throwing: OpenDError.timeout)
            }
            pending[sequence] = (protocolID, continuation, timer)
            connection.send(content: Frame.encode(protocolID: protocolID, serial: sequence, body: body),
                            completion: .contentProcessed { [weak self] error in
                guard let error else { return }
                Task { @MainActor in
                    guard let self, self.generation == token else { return }
                    self.fail(error)
                }
            })
        }
    }

    private func receive(_ connection: NWConnection, token: UUID) {
        connection.receive(minimumIncompleteLength: 1, maximumLength: 256 * 1024) { [weak self] data, _, done, error in
            Task { @MainActor in
                guard let self, self.generation == token else { return }
                do {
                    if let data {
                        for frame in try self.decoder.append(data) { try self.handle(frame) }
                    }
                    if let error { self.fail(error) }
                    else if done { self.fail(OpenDError.disconnected) }
                    else { self.receive(connection, token: token) }
                } catch { self.fail(error) }
            }
        }
    }
    private func handle(_ frame: Frame) throws {
        let response = try frame.object
        let status = response["retType"].map(number) ?? -400
        if let waiting = pending[frame.serial], waiting.0 == frame.protocolID {
            pending.removeValue(forKey: frame.serial); waiting.2.cancel()
            if status == 0 { waiting.1.resume(returning: response["s2c"] as? [String: Any] ?? [:]) }
            else { waiting.1.resume(throwing: OpenDError.server(response["retMsg"] as? String ?? "OpenD 错误 \(status)")) }
        } else if status == 0 {
            onPush?(frame.protocolID, response["s2c"] as? [String: Any] ?? [:])
        }
    }
}
