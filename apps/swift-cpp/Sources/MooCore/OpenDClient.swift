import Foundation
import MooBridge

private final class CallbackBox {
 let generation: UUID
 weak var owner: OpenDClient?
 init(_ generation: UUID, _ owner: OpenDClient) { self.generation = generation; self.owner = owner }
}
private let sdkCallback: MooCallback = { context, event, id, serial, json in
 guard let context, let json else { return }
 let box = Unmanaged<CallbackBox>.fromOpaque(context).takeUnretainedValue()
 let text = String(cString: json)
 Task { @MainActor in box.owner?.handle(event: event, id: id, serial: serial, text: text, token: box.generation) }
}

@MainActor
public final class OpenDClient {
 private var channel: UnsafeMutableRawPointer?
 private var box: CallbackBox?
 private var generation = UUID()
 private var readiness: CheckedContinuation<Void, Error>?
 private var pending: [UInt32: (UInt32, CheckedContinuation<[String: Any], Error>, Task<Void, Never>)] = [:]
 public var onPush: ((UInt32, [String: Any]) -> Void)?
 public var onDisconnect: ((String) -> Void)?
 public init() {}
 public func connect(host: String, port: UInt16) async throws {
  guard ["localhost", "127.0.0.1", "::1"].contains(host) else { throw OpenDError.server("此版本仅允许本机 OpenD") }
  disconnect()
  let token = generation, box = CallbackBox(generation, self)
  self.box = box
  guard let channel = moo_cpp_create(sdkCallback, Unmanaged.passUnretained(box).toOpaque()) else { throw OpenDError.server("无法创建 C++ SDK 连接") }
  self.channel = channel
  try await withCheckedThrowingContinuation { (continuation: CheckedContinuation<Void, Error>) in
   readiness = continuation
   if moo_cpp_connect(channel, host == "localhost" ? "127.0.0.1" : host, port) != 0 { fail(OpenDError.disconnected); return }
   Task { [weak self] in
    try? await Task.sleep(nanoseconds: 10_000_000_000)
    guard let self, self.generation == token, self.readiness != nil else { return }
    self.fail(OpenDError.timeout)
   }
  }
 }
 public func disconnect() {
  generation = UUID()
  if let channel { moo_cpp_destroy(channel) }
  channel = nil; box = nil
  readiness?.resume(throwing: OpenDError.disconnected); readiness = nil
  let requests = pending; pending.removeAll()
  for (_, continuation, timer) in requests.values { timer.cancel(); continuation.resume(throwing: OpenDError.disconnected) }
 }
 private func fail(_ error: Error) { disconnect(); onDisconnect?(error.localizedDescription) }
 public func request(_ protocolID: UInt32, _ payload: [String: Any]) async throws -> [String: Any] {
  guard let channel else { throw OpenDError.disconnected }
  let body = try JSONSerialization.data(withJSONObject: ["c2s": payload], options: [.sortedKeys])
  let serial = moo_cpp_request(channel, protocolID, String(decoding: body, as: UTF8.self))
  guard serial != 0 else { throw OpenDError.server("C++ SDK 拒绝请求 \(protocolID)") }
  let token = generation
  return try await withCheckedThrowingContinuation { continuation in
   let timer = Task { [weak self] in
    do { try await Task.sleep(nanoseconds: 10_000_000_000) } catch { return }
    guard let self, self.generation == token, let (_, waiting, _) = self.pending.removeValue(forKey: serial) else { return }
    waiting.resume(throwing: OpenDError.timeout)
   }
   pending[serial] = (protocolID, continuation, timer)
  }
 }
 fileprivate func handle(event: Int32, id: UInt32, serial: UInt32, text: String, token: UUID) {
  guard generation == token else { return }
  guard let object = try? JSONSerialization.jsonObject(with: Data(text.utf8)) as? [String: Any] else { fail(OpenDError.server("SDK 响应解析失败")); return }
  let success = object["retType"].map(number) == 0
  let error = OpenDError.server(object["retMsg"] as? String ?? "SDK 请求失败")
  switch event {
  case 0:
   if success { readiness?.resume(); readiness = nil } else { fail(error) }
  case 1: fail(error)
  case 2:
   guard let waiting = pending[serial], waiting.0 == id else { return }
   pending.removeValue(forKey: serial); waiting.2.cancel()
   if success { waiting.1.resume(returning: object["s2c"] as? [String: Any] ?? [:]) } else { waiting.1.resume(throwing: error) }
  case 3:
   if success { onPush?(id, object["s2c"] as? [String: Any] ?? [:]) }
  default: break
  }
 }
}
