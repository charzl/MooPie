import Foundation
import Combine
@MainActor final class OpenDService: ObservableObject {
    static let shared = OpenDService()
    @Published var status = "内置官方 OpenD · 自动检查更新"
    @Published var busy = false
    private var process: Process?
    private var timer: Timer?
    private var started = false
    func start() {
        guard !started else { return }; started = true
        run("launch")
        timer = Timer.scheduledTimer(withTimeInterval: 86400, repeats: true) { [weak self] _ in Task { @MainActor in self?.run("check") } }
    }
    func run(_ action: String) {
        guard !busy else { return }
        guard let directory = Bundle.main.resourceURL?.appendingPathComponent("OpenD"), let metadata = try? Data(contentsOf: directory.appendingPathComponent("opend.json")), let object = try? JSONSerialization.jsonObject(with: metadata) as? [String: String], let version = object["version"] else { status = "源码运行请连接已安装的 OpenD；打包版提供内置 OpenD"; return }
        let child = Process(); child.executableURL = directory.appendingPathComponent("OpenDManager")
        let flags: [String] = action == "launch" ? ["--launch"] : action == "update" ? ["--force"] : action == "rollback" ? ["--rollback"] : []
        child.arguments = ["--bundle", directory.appendingPathComponent("moomoo_OpenD.app").path, "--version", version] + flags
        let pipe = Pipe(); child.standardOutput = pipe; child.standardError = pipe
        pipe.fileHandleForReading.readabilityHandler = { [weak self] handle in
            let data = handle.availableData
            if data.isEmpty { handle.readabilityHandler = nil; return }
            let text = String(decoding: data, as: UTF8.self).trimmingCharacters(in: .whitespacesAndNewlines)
            Task { @MainActor in self?.status = text }
        }
        child.terminationHandler = { [weak self] _ in
            Task { @MainActor in self?.busy = false; self?.process = nil }
        }
        process = child; busy = true; status = action == "launch" ? "正在启动官方 OpenD…" : "正在管理 OpenD 更新…"
        do { try child.run() } catch { pipe.fileHandleForReading.readabilityHandler = nil; process = nil; busy = false; status = error.localizedDescription }
    }
}
