import AppKit
import SwiftUI
import MooCore
import MooBridge
import Darwin

@MainActor
enum Benchmark {
    static func cpuSeconds() -> Double {
        var usage = rusage(); getrusage(0, &usage)
        return Double(usage.ru_utime.tv_sec + usage.ru_stime.tv_sec) + Double(usage.ru_utime.tv_usec + usage.ru_stime.tv_usec) / 1_000_000
    }
    static func run(output: String) {
        let app = NSApplication.shared; app.setActivationPolicy(.prohibited)
        precondition(moo_cpp_validate_request(3004, #"{"c2s":{"securityList":[{"market":11,"code":"AAPL"}]}}"#) == 1)
        let model = MarketModel(benchmark: true)
        let host = NSHostingView(rootView: ContentView(model: model).frame(width: 1500, height: 900).environment(\.colorScheme, .dark))
        let window = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 1500, height: 900), styleMask: [.borderless], backing: .buffered, defer: false)
        window.contentView = host; host.frame = NSRect(x: 0, y: 0, width: 1500, height: 900)
        let outputURL = URL(fileURLWithPath: output), phaseURL = URL(fileURLWithPath: output + ".phase.json")
        func write(_ value: [String: Any], to url: URL) { try! JSONSerialization.data(withJSONObject: value, options: [.sortedKeys]).write(to: url, options: .atomic) }
        func snapshot() {
            host.layoutSubtreeIfNeeded(); host.displayIfNeeded()
            let bitmap = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: 1500, pixelsHigh: 900, bitsPerSample: 8, samplesPerPixel: 4, hasAlpha: true, isPlanar: false, colorSpaceName: .deviceRGB, bytesPerRow: 0, bitsPerPixel: 0)!
            bitmap.size = host.bounds.size
            host.cacheDisplay(in: host.bounds, to: bitmap)
        }
        let symbols = model.watchlist
        let quotes = Dictionary(uniqueKeysWithValues: symbols.map { ($0.id, DemoMarket.quote(for: $0)) })
        let bars = Dictionary(uniqueKeysWithValues: symbols.map { ($0.id, DemoMarket.candles(for: $0, period: .day)) })
        snapshot()
        let idleStart = ProcessInfo.processInfo.systemUptime, idleCPU = cpuSeconds()
        write(["phase": "idle"], to: phaseURL)
        func waitUntil(_ deadline: TimeInterval) {
            while ProcessInfo.processInfo.systemUptime < deadline {
                let remaining = deadline - ProcessInfo.processInfo.systemUptime
                _ = RunLoop.main.run(mode: .default, before: Date().addingTimeInterval(min(0.1, remaining)))
            }
        }
        waitUntil(idleStart + 5)
        let idle: [String: Double] = ["wall_seconds": ProcessInfo.processInfo.systemUptime - idleStart, "cpu_seconds": cpuSeconds() - idleCPU]
        let replayStart = ProcessInfo.processInfo.systemUptime, replayCPU = cpuSeconds()
        write(["phase": "replay"], to: phaseURL)
        var durations: [Double] = []
        for frame in 0..<120 {
            waitUntil(replayStart + Double(frame + 1) * 0.05)
            let begin = ProcessInfo.processInfo.systemUptime, delta = sin(Double(frame) * 0.1) * 0.25
            let security = symbols[(frame / 10) % symbols.count]
            model.quotes = quotes.mapValues { original in var q = original; q.price += delta; return q }
            model.sparks = Dictionary(uniqueKeysWithValues: symbols.map { ($0.id, Array(bars[$0.id]!.suffix(59).map(\.close)) + [model.quotes[$0.id]!.price]) })
            model.selected = security
            var data = bars[security.id]!, last = data.removeLast()
            let close = last.close + delta
            data.append(Candle(time: last.time, open: last.open, high: max(last.high, close), low: min(last.low, close), close: close, volume: last.volume))
            model.candles = data
            snapshot()
            durations.append((ProcessInfo.processInfo.systemUptime - begin) * 1000)
        }
        write(["schema": 1, "implementation": "swiftui-cpp", "render_pixels": [1500,900], "frame_count": 120,
               "idle": idle, "replay": ["wall_seconds": ProcessInfo.processInfo.systemUptime - replayStart, "cpu_seconds": cpuSeconds() - replayCPU],
               "update_and_snapshot_ms": durations, "sdk_loaded": true, "opend_connected": false,
               "fixture_first_quote": quotes[symbols[0].id]!.price], to: outputURL)
        write(["phase": "done"], to: phaseURL); model.disconnect()
        withExtendedLifetime(window) {}
    }
}
