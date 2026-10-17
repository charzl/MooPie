import Foundation
import OpenDRuntime
let args = CommandLine.arguments
func value(_ key: String) -> String? { guard let i = args.firstIndex(of: key), i+1 < args.count else { return nil }; return args[i+1] }
do {
    let root = value("--root").map { URL(fileURLWithPath: $0) } ?? FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0].appendingPathComponent("MooClients/OpenD")
    let manager = try Manager(root: root)
    if args.contains("--verify") {
        guard let bundle = value("--bundle"), let version = value("--version") else { throw RuntimeError.invalid("Missing --bundle / --version") }
        try manager.validate(URL(fileURLWithPath: bundle), version: version); print("官方 OpenD \(version) 签名及架构验证通过") }
    else {
        if let metadata = value("--metadata") {
            struct Metadata: Decodable { let version: String; let sha256: String }
            let meta = try JSONDecoder().decode(Metadata.self, from: Data(contentsOf: URL(fileURLWithPath: metadata)))
            print("正在准备官方 OpenD；已有安装将复用，首次使用可能需要下载…"); fflush(stdout)
            try manager.ensureInstalled(version: meta.version, sha256: meta.sha256, allowDownload: !args.contains("--offline"))
        } else {
            guard let bundle = value("--bundle"), let version = value("--version") else { throw RuntimeError.invalid("Missing --metadata or --bundle / --version") }
            try manager.bootstrap(bundle: URL(fileURLWithPath: bundle), version: version)
        }
        if args.contains("--rollback") { try manager.store.rollback(validate: { try manager.validate($0) }); print("已回退；重新启动官方 OpenD 生效") }
        else {
            if args.contains("--launch") { try manager.launch(); print("官方 OpenD 已启动；请在其窗口登录，再连接行情"); fflush(stdout) }
            if !args.contains("--offline") { print(try manager.update(force: args.contains("--force"))) }
        }
    }
} catch { fputs("\(error.localizedDescription)\n", stderr); exit(1) }
