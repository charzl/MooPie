import SwiftUI
import AppKit

struct MooSwiftApp: App {
    @StateObject private var model = MarketModel()
    var body: some Scene {
        WindowGroup("MooSwift") {
            ContentView(model: model)
                .frame(minWidth: 1150, minHeight: 680)
                .preferredColorScheme(.dark)
        }
        .defaultSize(width: 1500, height: 900)
        .windowStyle(.hiddenTitleBar)
        .commands {
            CommandGroup(replacing: .newItem) {}
            CommandMenu("行情") {
                Button("刷新行情") { Task { await model.refresh() } }.keyboardShortcut("r")
                Button("切换演示数据") { model.showDemo() }
                Button("断开 OpenD") { model.disconnect() }.disabled(!model.connected)
            }
        }
    }
}

@main
enum Launcher {
    @MainActor static func main() {
        if let index = CommandLine.arguments.firstIndex(of: "--render-preview"), CommandLine.arguments.count > index + 1 {
            let application = NSApplication.shared
            application.setActivationPolicy(.prohibited)
            let model = MarketModel()
            let content = ContentView(model: model).frame(width: 1500, height: 900).environment(\.colorScheme, .dark)
            let host = NSHostingView(rootView: content)
            let window = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 1500, height: 900),
                                  styleMask: [.borderless], backing: .buffered, defer: false)
            window.contentView = host
            host.frame = NSRect(x: 0, y: 0, width: 1500, height: 900)
            host.layoutSubtreeIfNeeded()
            RunLoop.main.run(until: Date().addingTimeInterval(0.4))
            host.displayIfNeeded()
            guard let bitmap = host.bitmapImageRepForCachingDisplay(in: host.bounds) else { fatalError("preview rendering failed") }
            host.cacheDisplay(in: host.bounds, to: bitmap)
            guard let png = bitmap.representation(using: .png, properties: [:]) else { fatalError("PNG encoding failed") }
            do { try png.write(to: URL(fileURLWithPath: CommandLine.arguments[index + 1])) }
            catch { fatalError(error.localizedDescription) }
            return
        }
        MooSwiftApp.main()
    }
}

enum Palette {
    static let background = Color(red: 0.080, green: 0.085, blue: 0.103)
    static let panel = Color(red: 0.10, green: 0.11, blue: 0.135)
    static let sidebar = Color(red: 0.135, green: 0.17, blue: 0.21)
    static let grid = Color(red: 0.13, green: 0.14, blue: 0.18)
    static let border = Color(red: 0.23, green: 0.26, blue: 0.31)
    static let text = Color(red: 0.86, green: 0.88, blue: 0.92)
    static let muted = Color(red: 0.57, green: 0.61, blue: 0.68)
    static let orange = Color(red: 1, green: 0.43, blue: 0.03)
    static let red = Color(red: 0.93, green: 0.19, blue: 0.34)
    static let green = Color(red: 0.02, green: 0.66, blue: 0.39)
}
