import Foundation
import AppKit
import Darwin

public enum RuntimeError: Error, LocalizedError {
    case invalid(String)
    public var errorDescription: String? { if case .invalid(let text) = self { return text }; return nil }
}
public enum Policy {
    public static let requirement = "identifier \"com.moomoo.opend\" and anchor apple generic and certificate leaf[subject.OU] = \"6HE4ZULJ45\""
    public static func parts(_ version: String) throws -> [Int] {
        let fields = version.split(separator: ".", omittingEmptySubsequences: false)
        guard fields.count == 3, fields.allSatisfy({ !$0.isEmpty && $0.allSatisfy({ $0.isASCII && $0.isNumber }) }), let a = Int(fields[0]), let b = Int(fields[1]), let c = Int(fields[2]) else { throw RuntimeError.invalid("Invalid OpenD version") }
        return [a,b,c]
    }
    public static func newer(_ lhs: String, than rhs: String) throws -> Bool { try parts(rhs).lexicographicallyPrecedes(parts(lhs)) }
    public static func downloadURL(_ version: String) throws -> URL {
        _ = try parts(version)
        return URL(string: "https://softwaredownload.moomoo.com/moomoo_OpenD_\(version)_Mac.tar.gz")!
    }
    public static func versionFromRedirect(_ headers: String) throws -> String {
        for line in headers.components(separatedBy: .newlines) where line.lowercased().hasPrefix("location:") {
            let value = line.dropFirst(9).trimmingCharacters(in: .whitespacesAndNewlines)
            guard let url = URL(string: value), url.scheme == "https", ["softwaredownload.moomoo.com", "softwaredownload.futunn.com"].contains(url.host ?? "") else { continue }
            let name = url.lastPathComponent
            let prefixes = ["moomoo_OpenD_", "Futu_OpenD_"]
            for prefix in prefixes where name.hasPrefix(prefix) && name.hasSuffix("_Mac.tar.gz") {
                let version = String(name.dropFirst(prefix.count).dropLast("_Mac.tar.gz".count))
                _ = try parts(version); return version
            }
        }
        throw RuntimeError.invalid("Official latest-version service unavailable")
    }
}
@discardableResult public func command(_ executable: String, _ arguments: [String]) throws -> String {
    let process = Process(); process.executableURL = URL(fileURLWithPath: executable); process.arguments = arguments
    let pipe = Pipe(); process.standardOutput = pipe; process.standardError = pipe
    try process.run()
    let data = pipe.fileHandleForReading.readDataToEndOfFile(); process.waitUntilExit()
    let text = String(decoding: data, as: UTF8.self)
    guard process.terminationStatus == 0 else { throw RuntimeError.invalid("\(URL(fileURLWithPath: executable).lastPathComponent) failed: \(text.prefix(1500))") }
    return text
}
public struct Selection: Codable, Equatable {
    public var current: String
    public var previous: String?
    public var lastCheck: Date?
    public init(current: String, previous: String? = nil, lastCheck: Date? = nil) { self.current = current; self.previous = previous; self.lastCheck = lastCheck }
}
public final class Store {
    public let root: URL
    private let fm = FileManager.default
    public init(root: URL) { self.root = root }
    public func app(_ version: String) throws -> URL { _ = try Policy.parts(version); return root.appendingPathComponent("versions/\(version)/moomoo_OpenD.app") }
    public func read() throws -> Selection? {
        let path = root.appendingPathComponent("selection.json")
        if !fm.fileExists(atPath: path.path) { return nil }
        let result = try JSONDecoder().decode(Selection.self, from: Data(contentsOf: path))
        _ = try Policy.parts(result.current); if let old = result.previous { _ = try Policy.parts(old) }; return result
    }
    public func save(_ state: Selection) throws {
        _ = try Policy.parts(state.current); if let old = state.previous { _ = try Policy.parts(old) }
        try fm.createDirectory(at: root, withIntermediateDirectories: true)
        try JSONEncoder().encode(state).write(to: root.appendingPathComponent("selection.json"), options: .atomic)
    }
    public func activate(_ version: String, validate: (URL) throws -> Void) throws {
        let target = try app(version); try validate(target)
        let state = try read()
        if let state, !(try Policy.newer(version, than: state.current)) { return }
        try save(Selection(current: version, previous: state?.current, lastCheck: Date()))
    }
    public func rollback(validate: (URL) throws -> Void) throws {
        guard let state = try read(), let previous = state.previous else { throw RuntimeError.invalid("No previous OpenD available") }
        try validate(app(previous)); try save(Selection(current: previous, previous: state.current, lastCheck: Date()))
    }
}
public final class Manager {
    public let store: Store
    private var lockFD: Int32 = -1
    private let fm = FileManager.default
    public init(root: URL) throws {
        store = Store(root: root); try fm.createDirectory(at: root, withIntermediateDirectories: true, attributes: [.posixPermissions: 0o700])
        lockFD = Darwin.open(root.appendingPathComponent("update.lock").path, O_CREAT | O_RDWR, S_IRUSR | S_IWUSR)
        guard lockFD >= 0, flock(lockFD, LOCK_EX | LOCK_NB) == 0 else { if lockFD >= 0 { Darwin.close(lockFD); lockFD = -1 }; throw RuntimeError.invalid("另一客户端正在管理 OpenD，请稍后重试") }
        for item in try fm.contentsOfDirectory(at: root, includingPropertiesForKeys: nil) where item.lastPathComponent.hasPrefix("staging-") { try? fm.removeItem(at: item) }
    }
    deinit { if lockFD >= 0 { flock(lockFD, LOCK_UN); Darwin.close(lockFD) } }
    public func validate(_ app: URL, version: String? = nil) throws {
        let data = try Data(contentsOf: app.appendingPathComponent("Contents/Info.plist"))
        let info = try PropertyListSerialization.propertyList(from: data, format: nil) as? [String: Any]
        guard info?["CFBundleIdentifier"] as? String == "com.moomoo.opend", let actual = info?["CFBundleShortVersionString"] as? String else { throw RuntimeError.invalid("Invalid official OpenD bundle") }
        _ = try Policy.parts(actual)
        if let version, actual != version { throw RuntimeError.invalid("OpenD package version mismatch") }
        try command("/usr/bin/codesign", ["--verify", "--deep", "--strict", "-R", "=" + Policy.requirement, app.path])
        let architectures = try command("/usr/bin/lipo", ["-archs", app.appendingPathComponent("Contents/MacOS/moomoo_OpenD").path])
        #if arch(arm64)
        guard architectures.split(separator: " ").contains(where: { $0.trimmingCharacters(in: .whitespacesAndNewlines) == "arm64" }) else { throw RuntimeError.invalid("OpenD does not support Apple Silicon") }
        #else
        guard architectures.contains("x86_64") else { throw RuntimeError.invalid("OpenD does not support Intel") }
        #endif
    }
    public func bootstrap(bundle: URL, version: String) throws {
        if let state = try store.read() { try validate(store.app(state.current), version: state.current); return }
        try validate(bundle, version: version)
        let destination = try store.app(version)
        try fm.createDirectory(at: destination.deletingLastPathComponent(), withIntermediateDirectories: true)
        try command("/usr/bin/ditto", [bundle.path, destination.path])
        try store.activate(version, validate: { try self.validate($0, version: version) })
        try store.save(Selection(current: version))
    }
    public func launch() throws {
        guard let state = try store.read() else { throw RuntimeError.invalid("OpenD not installed") }
        // Both clients share the gateway. Never kill an existing logged-in OpenD.
        if NSRunningApplication.runningApplications(withBundleIdentifier: "com.moomoo.opend").contains(where: { !$0.isTerminated }) { return }
        let target = try store.app(state.current); try validate(target, version: state.current)
        do { try command("/usr/bin/open", ["-a", target.path]) }
        catch {
            try store.rollback(validate: { try self.validate($0) })
            guard let old = try store.read() else { throw error }
            try command("/usr/bin/open", ["-a", try store.app(old.current).path])
        }
    }
    public func update(force: Bool) throws -> String {
        guard var state = try store.read() else { throw RuntimeError.invalid("OpenD not installed") }
        if !force, let date = state.lastCheck, Date().timeIntervalSince(date) < 86400 { return "OpenD \(state.current) · 自动检查间隔 24 小时" }
        state.lastCheck = Date(); try store.save(state)
        var latest: String?
        for host in ["www.moomoo.com", "www.futunn.com"] {
            if let headers = try? command("/usr/bin/curl", ["--fail", "--silent", "--show-error", "--proto", "=https", "--max-time", "20", "-I", "https://\(host)/download/fetch-lasted-link?name=opend-macos"]), let found = try? Policy.versionFromRedirect(headers) { latest = found; break }
        }
        guard let latest else { throw RuntimeError.invalid("更新服务暂不可用，保留 OpenD \(state.current)") }
        guard try Policy.newer(latest, than: state.current) else { return "OpenD \(state.current) 已是最新版" }
        return try install(version: latest)
    }
    /// Reuse a shared official gateway, or install the pinned gateway once.
    public func ensureInstalled(version: String, sha256: String, allowDownload: Bool = true) throws {
        _ = try Policy.parts(version)
        guard sha256.count == 64, sha256.allSatisfy({ $0.isASCII && ($0.isNumber || ("a"..."f").contains(String($0))) }) else { throw RuntimeError.invalid("Invalid OpenD archive checksum") }
        if let state = try store.read() {
            try validate(store.app(state.current), version: state.current)
            if !(try Policy.newer(version, than: state.current)) { return }
        } else {
            let candidates = NSRunningApplication.runningApplications(withBundleIdentifier: "com.moomoo.opend").compactMap { $0.bundleURL } + [URL(fileURLWithPath: "/Applications/moomoo_OpenD.app")]
            for candidate in candidates {
                guard (try? validate(candidate)) != nil,
                      let data = try? Data(contentsOf: candidate.appendingPathComponent("Contents/Info.plist")),
                      let info = try? PropertyListSerialization.propertyList(from: data, format: nil) as? [String: Any],
                      let actual = info["CFBundleShortVersionString"] as? String,
                      !(try Policy.newer(version, than: actual)) else { continue }
                try bootstrap(bundle: candidate, version: actual); return
            }
        }
        guard allowDownload else { throw RuntimeError.invalid("尚未安装兼容的 OpenD；首次使用需要联网下载") }
        _ = try install(version: version, sha256: sha256)
    }
    private func install(version: String, sha256: String? = nil) throws -> String {
        let existing = try store.app(version)
        if fm.fileExists(atPath: existing.path), (try? validate(existing, version: version)) != nil {
            try store.activate(version, validate: { try self.validate($0, version: version) })
            return "OpenD \(version) 已校验并选中；重新启动官方 OpenD 生效"
        }
        if NSRunningApplication.runningApplications(withBundleIdentifier: "com.moomoo.opend").contains(where: { $0.bundleURL?.standardizedFileURL == existing.standardizedFileURL }) {
            throw RuntimeError.invalid("待更新路径仍有 OpenD 运行；请退出官方 OpenD 后重试")
        }
        let stage = store.root.appendingPathComponent("staging-\(UUID().uuidString)")
        try fm.createDirectory(at: stage, withIntermediateDirectories: true)
        defer { try? fm.removeItem(at: stage) }
        let archive = stage.appendingPathComponent("download.tar.gz")
        try command("/usr/bin/curl", ["--fail", "--silent", "--show-error", "--proto", "=https", "--max-time", "600", "--max-filesize", "1073741824", "--output", archive.path, try Policy.downloadURL(version).absoluteString])
        if let expected = sha256 {
            let actual = try command("/usr/bin/shasum", ["-a", "256", archive.path]).split(separator: " ").first.map(String.init)
            guard actual == expected else { throw RuntimeError.invalid("Official OpenD archive SHA-256 mismatch") }
        }
        let entry = "moomoo_OpenD_\(version)_Mac/moomoo_OpenD-GUI_\(version)_Mac/moomoo_OpenD-GUI_\(version)_Mac.dmg"
        try command("/usr/bin/tar", ["-xzf", archive.path, "-C", stage.path, entry])
        let mount = stage.appendingPathComponent("mount")
        try fm.createDirectory(at: mount, withIntermediateDirectories: true)
        try command("/usr/bin/hdiutil", ["attach", "-readonly", "-nobrowse", "-mountpoint", mount.path, stage.appendingPathComponent(entry).path])
        defer { _ = try? command("/usr/bin/hdiutil", ["detach", mount.path]) }
        let app = mount.appendingPathComponent("moomoo_OpenD.app")
        try validate(app, version: version)
        let destination = try store.app(version)
        // A failed previous install is discarded; the selected current version is never touched.
        if fm.fileExists(atPath: destination.deletingLastPathComponent().path) { try fm.removeItem(at: destination.deletingLastPathComponent()) }
        try fm.createDirectory(at: destination.deletingLastPathComponent(), withIntermediateDirectories: true)
        try command("/usr/bin/ditto", [app.path, destination.path])
        try store.activate(version, validate: { try self.validate($0, version: version) })
        return "已下载并校验 OpenD \(version)；退出官方 OpenD 后重新启动即可使用，旧版可回退"
    }
}
