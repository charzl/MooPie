import SwiftUI
import MooCore

struct CandleChart: View {
    let candles: [Candle]
    let redUp: Bool
    let showMA: Bool
    let lineMode: Bool
    let visibleCount: Int
    let period: Period
    @State private var hover: CGPoint?
    private var bars: [Candle] { Array(candles.suffix(visibleCount)) }
    private let maColors: [Color] = [Palette.orange, Color.pink, Palette.green, Color.cyan]
    var body: some View {
        GeometryReader { geo in
            let data = bars
            Canvas { context, size in
                guard !data.isEmpty else { return }
                let left: CGFloat = 10, right: CGFloat = 68
                let width = max(1, size.width - left - right)
                let top: CGFloat = 35, priceHeight = max(60, size.height * 0.76 - top)
                let volumeTop = top + priceHeight + 30, volumeHeight = max(20, size.height - volumeTop - 26)
                let lower = data.map(\.low).min()!, upper = data.map(\.high).max()!
                let padding = max((upper - lower) * 0.07, upper * 0.002)
                let low = lower - padding, high = upper + padding, span = max(high - low, 0.001)
                let dx = width / CGFloat(data.count), bodyWidth = max(1, dx * 0.65)
                func y(_ value: Double) -> CGFloat { top + CGFloat((high - value) / span) * priceHeight }
                func x(_ index: Int) -> CGFloat { left + (CGFloat(index) + 0.5) * dx }
                func stroke(_ from: CGPoint, _ to: CGPoint, color: Color, dashed: Bool = false) {
                    var path = Path(); path.move(to: from); path.addLine(to: to)
                    context.stroke(path, with: .color(color), style: StrokeStyle(lineWidth: 0.7, dash: dashed ? [3, 3] : []))
                }
                func text(_ value: String, _ point: CGPoint, color: Color = Palette.muted, anchor: UnitPoint = .leading) {
                    context.draw(Text(value).font(.system(size: 10, design: .monospaced)).foregroundColor(color), at: point, anchor: anchor)
                }
                for i in 0...8 {
                    let value = high - span * Double(i) / 8
                    let yy = y(value)
                    stroke(CGPoint(x: left, y: yy), CGPoint(x: left + width, y: yy), color: Palette.grid)
                    text(String(format: "%.3f", value), CGPoint(x: left + width + 8, y: yy))
                }
                for i in 0...6 {
                    let xx = left + width * CGFloat(i) / 6
                    stroke(CGPoint(x: xx, y: top), CGPoint(x: xx, y: size.height - 24), color: Palette.grid)
                    let index = min(data.count - 1, i * data.count / 6)
                    let time = data[index].time
                    let label = [.minute, .five, .fifteen].contains(period)
                        ? String(time.dropFirst(11).prefix(5)) : String(time.dropFirst(5).prefix(5))
                    text(label, CGPoint(x: xx, y: size.height - 9), anchor: i == 6 ? .trailing : i == 0 ? .leading : .center)
                }
                let maxVolume = max(1, data.map(\.volume).max()!)
                if lineMode {
                    var line = Path()
                    for (i, bar) in data.enumerated() {
                        let p = CGPoint(x: x(i), y: y(bar.close))
                        if i == 0 { line.move(to: p) } else { line.addLine(to: p) }
                    }
                    context.stroke(line, with: .color(Color.cyan), lineWidth: 1.3)
                }
                for (i, bar) in data.enumerated() {
                    let rising = bar.close >= bar.open
                    let color = rising == redUp ? Palette.red : Palette.green
                    if !lineMode {
                        stroke(CGPoint(x: x(i), y: y(bar.high)), CGPoint(x: x(i), y: y(bar.low)), color: color)
                        let rect = CGRect(x: x(i) - bodyWidth / 2, y: min(y(bar.open), y(bar.close)), width: bodyWidth,
                                          height: max(1, abs(y(bar.open) - y(bar.close))))
                        if rising { context.stroke(Path(rect), with: .color(color), lineWidth: 1) }
                        else { context.fill(Path(rect), with: .color(color)) }
                    }
                    let h = CGFloat(bar.volume / maxVolume) * volumeHeight
                    context.fill(Path(CGRect(x: x(i) - bodyWidth / 2, y: volumeTop + volumeHeight - h, width: bodyWidth, height: h)), with: .color(color))
                }
                if showMA {
                    // Calculate on full history so zooming does not change moving averages.
                    let offset = candles.count - data.count
                    for (j, period) in [5, 10, 20, 60].enumerated() {
                        var path = Path(), started = false
                        for i in data.indices {
                            let end = offset + i
                            guard end + 1 >= period else { continue }
                            let average = candles[(end - period + 1)...end].map(\.close).reduce(0, +) / Double(period)
                            let point = CGPoint(x: x(i), y: y(average))
                            if started { path.addLine(to: point) } else { path.move(to: point); started = true }
                        }
                        context.stroke(path, with: .color(maColors[j]), lineWidth: 1)
                        if candles.count >= period {
                            let average = candles.suffix(period).map(\.close).reduce(0, +) / Double(period)
                            text(String(format: "MA%d: %.3f", period, average), CGPoint(x: 12 + CGFloat(j) * 132, y: 16), color: maColors[j])
                        }
                    }
                }
                let last = data.last!
                stroke(CGPoint(x: left, y: y(last.close)), CGPoint(x: left + width, y: y(last.close)),
                       color: (last.close >= last.open) == redUp ? Palette.red : Palette.green, dashed: true)
                text("成交量", CGPoint(x: left, y: volumeTop - 12))
                text(compactVolume(last.volume), CGPoint(x: left + 54, y: volumeTop - 12))
                if let hover, hover.x >= left, hover.x <= left + width {
                    let index = min(data.count - 1, max(0, Int((hover.x - left) / dx)))
                    let bar = data[index], xx = x(index)
                    stroke(CGPoint(x: xx, y: top), CGPoint(x: xx, y: volumeTop + volumeHeight), color: Palette.muted, dashed: true)
                    let yy = max(top, min(top + priceHeight, hover.y))
                    stroke(CGPoint(x: left, y: yy), CGPoint(x: left + width, y: yy), color: Palette.muted, dashed: true)
                    let label = String(format: "%@  开 %.3f  高 %.3f  低 %.3f  收 %.3f", bar.time, bar.open, bar.high, bar.low, bar.close)
                    context.fill(Path(CGRect(x: 8, y: 0, width: min(width, 610), height: 28)), with: .color(Palette.panel))
                    text(label, CGPoint(x: 14, y: 14), color: Palette.text)
                }
            }
            .onContinuousHover { phase in
                switch phase { case .active(let point): hover = point; case .ended: hover = nil }
            }
            .accessibilityLabel("K 线图，\(data.count) 根；末值 \(data.last?.close ?? 0)")
        }
    }
}

struct Sparkline: View {
    let values: [Double]
    let color: Color
    var body: some View {
        Canvas { context, size in
            guard values.count > 1, let min = values.min(), let max = values.max() else { return }
            let range = Swift.max(0.001, max - min)
            var line = Path()
            for (i, value) in values.enumerated() {
                let p = CGPoint(x: CGFloat(i) / CGFloat(values.count - 1) * size.width,
                                y: 3 + CGFloat(1 - (value - min) / range) * (size.height - 6))
                if i == 0 { line.move(to: p) } else { line.addLine(to: p) }
            }
            var area = line; area.addLine(to: CGPoint(x: size.width, y: size.height)); area.addLine(to: CGPoint(x: 0, y: size.height)); area.closeSubpath()
            context.fill(area, with: .linearGradient(Gradient(colors: [color.opacity(0.22), color.opacity(0)]),
                                                     startPoint: .zero, endPoint: CGPoint(x: 0, y: size.height)))
            context.stroke(line, with: .color(color), lineWidth: 1)
        }
    }
}

func compactVolume(_ value: Double) -> String {
    if value >= 100_000_000 { return String(format: "%.2f亿", value / 100_000_000) }
    if value >= 10_000 { return String(format: "%.2f万", value / 10_000) }
    return String(format: "%.0f", value)
}
