import SwiftUI
import MooCore

struct ContentView: View {
    @ObservedObject var model: MarketModel
    @State private var settings = false
    @State private var addSheet = false
    @State private var search = ""
    @State private var filter = "全部"
    @State private var sort = "默认"
    @State private var showMA = true
    @State private var lineMode = false
    @State private var visibleCount = 160
    @State private var showHelp = false
    @State private var watchWidth: CGFloat = 460
    @State private var dragStart: CGFloat?
    var body: some View {
        HStack(spacing: 0) {
            sidebar
            VStack(spacing: 0) {
                topbar
                HStack(spacing: 0) {
                    watchlist.frame(width: watchWidth)
                    Rectangle().fill(Palette.border).frame(width: 3)
                        .onHover { inside in if inside { NSCursor.resizeLeftRight.push() } else { NSCursor.pop() } }
                        .gesture(DragGesture().onChanged { value in
                            if dragStart == nil { dragStart = watchWidth }
                            watchWidth = min(650, max(330, (dragStart ?? watchWidth) + value.translation.width))
                        }.onEnded { _ in dragStart = nil })
                    chartArea.frame(maxWidth: .infinity, maxHeight: .infinity)
                }
                statusbar
            }
        }
        .background(Palette.background).foregroundStyle(Palette.text)
        .font(.system(size: 12))
        .sheet(isPresented: $settings) { ConnectionSettings(model: model) }
        .sheet(isPresented: $addSheet) { AddSecurity(model: model) }
        .alert("原生看盘客户端", isPresented: $showHelp) {
            Button("知道了", role: .cancel) {}
        } message: {
            Text("当前版本已实现自选股、报价、K 线、均线、成交量与 OpenD 行情连接。账户、期权交易、社区和下单尚未实现。")
        }
    }
    private var sidebar: some View {
        VStack(alignment: .leading, spacing: 10) {
            Spacer().frame(height: 26)
            Image(systemName: "person.crop.circle.fill").font(.system(size: 27)).foregroundStyle(Palette.muted).padding(12)
            nav("账户", "wallet.pass", active: false)
            nav("图表", "chart.bar.xaxis", active: true)
            nav("期权", "chart.xyaxis.line", active: false)
            nav("观察", "binoculars", active: false)
            nav("市场", "globe.asia.australia", active: false)
            nav("自定义", "rectangle.split.2x2", active: false)
            nav("发现", "safari", active: false)
            Spacer()
            Button { addSheet = true } label: { Label("添加自选", systemImage: "plus.circle").padding(12) }
            Button { settings = true } label: { Label("设置", systemImage: "gearshape").padding(12) }
        }
        .buttonStyle(.plain).padding(.horizontal, 7).padding(.bottom, 14)
        .frame(width: 112).frame(maxHeight: .infinity).background(Palette.sidebar)
    }
    private func nav(_ title: String, _ icon: String, active: Bool) -> some View {
        Button { if !active { showHelp = true } } label: {
            HStack(spacing: 10) {
                Image(systemName: icon).font(.system(size: 18)).frame(width: 20).foregroundStyle(active ? Palette.orange : Palette.text)
                Text(title).fontWeight(active ? .semibold : .regular)
            }.padding(.horizontal, 9).frame(height: 39).frame(maxWidth: .infinity, alignment: .leading)
                .background(active ? Palette.background : .clear).clipShape(RoundedRectangle(cornerRadius: 3))
        }.help(active ? "行情图表" : "此功能尚未实现")
    }
    private var topbar: some View {
        HStack(spacing: 16) {
            Button { Task { await model.refresh() } } label: { Image(systemName: "arrow.clockwise") }.help("刷新行情 ⌘R")
            HStack {
                Image(systemName: "magnifyingglass").foregroundStyle(Palette.muted)
                TextField("搜索自选股", text: $search).textFieldStyle(.plain)
                if !search.isEmpty { Button { search = "" } label: { Image(systemName: "xmark.circle.fill") } }
            }.padding(7).frame(width: 200).overlay(RoundedRectangle(cornerRadius: 18).stroke(Palette.border))
            Spacer()
            HStack(spacing: 5) {
                Image(systemName: "chart.line.uptrend.xyaxis").foregroundStyle(Palette.orange).font(.system(size: 21, weight: .bold))
                Text("MooSwift C++").font(.system(size: 18, weight: .bold))
                Text("C++ SDK").font(.system(size: 9, weight: .bold)).padding(3).foregroundStyle(Palette.orange).background(Palette.orange.opacity(0.15)).clipShape(RoundedRectangle(cornerRadius: 2))
            }
            Spacer()
            Text(model.mode).font(.system(size: 11)).foregroundStyle(model.connected ? Palette.green : Palette.orange)
            Button { settings = true } label: { Text(model.connected ? "连接设置" : "连接 OpenD").fontWeight(.semibold).padding(.horizontal, 16).padding(.vertical, 7).background(Palette.orange).foregroundStyle(.white).clipShape(Capsule()) }
        }.buttonStyle(.plain).padding(.horizontal, 14).frame(height: 48)
            .overlay(alignment: .bottom) { Divider().overlay(Palette.border) }
    }
    private var filtered: [Security] {
        var list = model.watchlist.filter { security in
            let market = filter == "全部" || filter == "特别关注" ||
                (filter == "美股" && security.market == 11) || (filter == "港股" && security.market == 1) ||
                (filter == "沪深" && [21, 22].contains(security.market))
            let favorite = filter != "特别关注" || model.favorites.contains(security.id)
            let text = search.isEmpty || security.id.localizedCaseInsensitiveContains(search) ||
                (model.quotes[security.id]?.name ?? "").localizedCaseInsensitiveContains(search)
            return market && favorite && text
        }
        if sort == "涨跌幅" { list.sort { (model.quotes[$0.id]?.changePercent ?? -.infinity) > (model.quotes[$1.id]?.changePercent ?? -.infinity) } }
        if sort == "最新价" { list.sort { (model.quotes[$0.id]?.price ?? -.infinity) > (model.quotes[$1.id]?.price ?? -.infinity) } }
        return list
    }
    private var watchlist: some View {
        VStack(spacing: 0) {
            HStack {
                Text("自选股").fontWeight(.semibold)
                Text("\(filtered.count)").foregroundStyle(Palette.muted)
                Spacer()
                Menu { Picker("排序", selection: $sort) { ForEach(["默认", "最新价", "涨跌幅"], id: \.self) { Text($0) } } } label: { Image(systemName: "slider.horizontal.3") }.menuStyle(.borderlessButton).frame(width: 22)
                Button { addSheet = true } label: { Image(systemName: "plus") }.buttonStyle(.plain)
            }.padding(.horizontal, 13).frame(height: 40)
            HStack(spacing: 6) {
                ForEach(["全部", "特别关注", "美股", "港股", "沪深"], id: \.self) { title in
                    Button { filter = title } label: {
                        Text(title).font(.system(size: 11)).padding(.horizontal, 8).padding(.vertical, 5)
                            .overlay(RoundedRectangle(cornerRadius: 3).stroke(filter == title ? Palette.text : Palette.border))
                    }.buttonStyle(.plain)
                }
                Spacer(minLength: 0)
            }.padding(.horizontal, 10).padding(.vertical, 10)
            HStack {
                Text("名称代码").frame(maxWidth: .infinity, alignment: .leading)
                Text("最新价").frame(width: 75, alignment: .trailing)
                Text("涨跌幅").frame(width: 74, alignment: .trailing)
                Text("涨跌额").frame(width: 66, alignment: .trailing)
            }.foregroundStyle(Palette.muted).font(.system(size: 10)).padding(.horizontal, 13).frame(height: 25)
            ScrollView {
                LazyVStack(spacing: 1) {
                    ForEach(filtered) { security in stockRow(security) }
                    if filtered.isEmpty { Text("没有匹配的自选股").foregroundStyle(Palette.muted).padding(28) }
                }.padding(.horizontal, 4)
            }
            HStack {
                Text(model.mode == "演示数据" ? "合成示例 · 非实际行情" : "报价时间以 OpenD 返回为准").font(.system(size: 10)).foregroundStyle(Palette.muted)
                Spacer()
            }.padding(10)
        }
    }
    private func stockRow(_ security: Security) -> some View {
        let quote = model.quotes[security.id]
        let color = model.color(quote?.change ?? 0)
        return Button { model.select(security) } label: {
            HStack(spacing: 7) {
                VStack(alignment: .leading, spacing: 5) {
                    Text(quote?.name ?? DemoMarket.names[security.code] ?? security.code).lineLimit(1).fontWeight(.medium)
                    HStack(spacing: 3) {
                        Text(security.code).foregroundStyle(Palette.muted)
                        if model.favorites.contains(security.id) { Image(systemName: "star.fill").foregroundStyle(.yellow).font(.system(size: 9)) }
                    }.font(.system(size: 10))
                }.frame(width: 100, alignment: .leading)
                Sparkline(values: model.sparks[security.id] ?? [], color: color).frame(maxWidth: .infinity).frame(height: 27)
                VStack(alignment: .trailing, spacing: 4) {
                    Text(quote.map { String(format: "%.3f", $0.price) } ?? "—").foregroundStyle(color).fontWeight(.semibold)
                    Text(quote?.afterPrice.map { String(format: "%.3f", $0) } ?? "").foregroundStyle(Palette.muted).font(.system(size: 9))
                }.frame(width: 75, alignment: .trailing)
                Text(quote.map { String(format: "%+.2f%%", $0.changePercent) } ?? "—")
                    .font(.system(size: 11, weight: .semibold)).foregroundStyle(quote == nil ? Palette.muted : Color.white)
                    .frame(width: 67, height: 23).background(color.opacity(quote == nil ? 0 : 0.65)).clipShape(RoundedRectangle(cornerRadius: 2))
                Text(quote.map { String(format: "%+.3f", $0.change) } ?? "—").foregroundStyle(color).frame(width: 61, alignment: .trailing)
            }.monospacedDigit().padding(.horizontal, 8).frame(height: 58)
                .background(model.selected == security ? Palette.panel : Palette.background)
                .overlay(RoundedRectangle(cornerRadius: 3).stroke(model.selected == security ? Palette.text.opacity(0.75) : .clear))
        }.buttonStyle(.plain)
            .contextMenu {
                Button(model.favorites.contains(security.id) ? "取消特别关注" : "特别关注") { model.favorite(security) }
                Button("移除自选", role: .destructive) { model.remove(security) }
            }
    }
    private var chartArea: some View {
        VStack(spacing: 0) {
            HStack(spacing: 10) {
                Image(systemName: "magnifyingglass").foregroundStyle(Palette.muted)
                Text("\(model.selected.code)  \(model.currentQuote?.name ?? DemoMarket.names[model.selected.code] ?? "")").fontWeight(.semibold)
                if let quote = model.currentQuote {
                    Text(String(format: "%.3f  %+.3f  %+.2f%%", quote.price, quote.change, quote.changePercent)).foregroundStyle(model.color(quote.change)).monospacedDigit()
                }
                Spacer(minLength: 0)
                Text("图表").fontWeight(.semibold).padding(.vertical, 10).overlay(alignment: .bottom) { Rectangle().fill(Palette.text).frame(height: 2) }
            }.padding(.horizontal, 12).frame(height: 40).overlay(alignment: .bottom) { Divider().overlay(Palette.border) }
            HStack(spacing: 6) {
                ForEach(Period.allCases) { period in
                    Button { model.setPeriod(period) } label: {
                        Text(period.rawValue).font(.system(size: 11, weight: .medium)).padding(.horizontal, 7).padding(.vertical, 5)
                            .background(model.period == period ? Palette.text : .clear)
                            .foregroundStyle(model.period == period ? Palette.background : Palette.text).clipShape(RoundedRectangle(cornerRadius: 3))
                    }.buttonStyle(.plain)
                }
                Spacer(minLength: 0)
                Button { lineMode.toggle() } label: { Image(systemName: lineMode ? "chart.bar.xaxis" : "waveform.path") }.help("切换 K 线 / 收盘价曲线")
                Button { visibleCount = max(30, visibleCount - 30) } label: { Image(systemName: "plus.magnifyingglass") }.help("放大")
                Button { visibleCount = min(200, visibleCount + 30) } label: { Image(systemName: "minus.magnifyingglass") }.help("缩小")
            }.buttonStyle(.plain).padding(.horizontal, 10).frame(height: 38)
            HStack(spacing: 12) {
                if let q = model.currentQuote {
                    stat("开", q.open, change: q.open - q.previousClose)
                    stat("高", q.high, change: q.high - q.previousClose)
                    stat("低", q.low, change: q.low - q.previousClose)
                    stat("收", q.price, change: q.change)
                    Text("量 \(compactVolume(q.volume))").foregroundStyle(Palette.muted)
                    Text("额 \(compactVolume(q.turnover))").foregroundStyle(Palette.muted)
                } else { Text("等待行情数据").foregroundStyle(Palette.muted) }
                Spacer(minLength: 0)
            }.font(.system(size: 10)).monospacedDigit().padding(.horizontal, 12).frame(height: 28)
            ZStack {
                CandleChart(candles: model.candles, redUp: model.redUp, showMA: showMA, lineMode: lineMode, visibleCount: visibleCount, period: model.period)
                if model.loadingChart { ProgressView("加载 K 线…").padding(20).background(Palette.panel).clipShape(RoundedRectangle(cornerRadius: 8)) }
                else if let error = model.chartError {
                    VStack(spacing: 12) { Image(systemName: "exclamationmark.circle").font(.system(size: 24)); Text(error).multilineTextAlignment(.center); Button("重试") { Task { await model.loadChart() } } }
                        .foregroundStyle(Palette.muted).padding(30).frame(maxWidth: 500).background(Palette.panel)
                } else if model.candles.isEmpty { Text("连接 OpenD 以获取 K 线").foregroundStyle(Palette.muted) }
            }.frame(maxWidth: .infinity, maxHeight: .infinity).padding(.horizontal, 10)
            HStack(spacing: 18) {
                Button { showMA.toggle() } label: { Text("MA").foregroundStyle(showMA ? Palette.orange : Palette.muted) }
                Text("MA5 / MA10 / MA20 / MA60").foregroundStyle(Palette.muted)
                Text("成交量").foregroundStyle(Palette.text)
                Spacer()
                Text("前复权").foregroundStyle(Palette.muted)
                Text("\(model.candles.count) 根").foregroundStyle(Palette.muted)
            }.buttonStyle(.plain).font(.system(size: 10)).padding(.horizontal, 15).frame(height: 30)
        }
    }
    private func stat(_ label: String, _ value: Double, change: Double) -> some View {
        HStack(spacing: 4) { Text(label).foregroundStyle(Palette.muted); Text(String(format: "%.3f", value)).foregroundStyle(model.color(change)) }
    }
    private var statusbar: some View {
        HStack(spacing: 8) {
            Circle().fill(model.connected ? Palette.green : Palette.orange).frame(width: 6, height: 6)
            Text(model.message).lineLimit(1).help(model.message)
            Spacer(minLength: 8)
            if let q = model.currentQuote { Text(q.updated).monospacedDigit() }
            Text("SwiftUI").foregroundStyle(Palette.muted)
        }.font(.system(size: 10)).padding(.horizontal, 12).frame(height: 27)
            .overlay(alignment: .top) { Divider().overlay(Palette.border) }
    }
}

struct ConnectionSettings: View {
    @ObservedObject var model: MarketModel
    @Environment(\.dismiss) private var dismiss
    @State private var host = UserDefaults.standard.string(forKey: "host") ?? "127.0.0.1"
    @State private var port = UserDefaults.standard.string(forKey: "port") ?? "11111"
    var body: some View {
        VStack(alignment: .leading, spacing: 18) {
            Text("连接 OpenD").font(.title2).fontWeight(.semibold)
            Text("在 moomoo OpenD 中登录账户，再连接本机网关。客户端不保存账号或密码。")
                .foregroundStyle(Palette.muted).fixedSize(horizontal: false, vertical: true)
            HStack { Text("地址").frame(width: 40, alignment: .leading); TextField("127.0.0.1", text: $host) }
            HStack { Text("端口").frame(width: 40, alignment: .leading); TextField("11111", text: $port) }
            Text("当前仅支持本机 TCP / JSON、未配置 RSA 加密的 OpenD。行情权限及延迟由账户决定。")
                .font(.system(size: 11)).foregroundStyle(Palette.muted).fixedSize(horizontal: false, vertical: true)
            Link("下载官方 moomoo OpenD ↗", destination: URL(string: "https://www.moomoo.com/download/OpenAPI")!)
            Divider()
            Toggle("红涨绿跌", isOn: $model.redUp)
            Text(model.message).font(.system(size: 11)).foregroundStyle(Palette.orange).textSelection(.enabled).fixedSize(horizontal: false, vertical: true)
            HStack {
                Button("演示数据") { model.showDemo(); dismiss() }
                if model.connected || model.connecting { Button("断开") { model.disconnect() } }
                Spacer()
                Button("关闭") { dismiss() }.keyboardShortcut(.cancelAction)
                Button(model.connecting ? "连接中…" : "连接") {
                    Task { await model.connect(host: host.trimmingCharacters(in: .whitespaces), port: port); if model.connected { dismiss() } }
                }.buttonStyle(.borderedProminent).tint(Palette.orange).disabled(model.connecting).keyboardShortcut(.defaultAction)
            }
        }.padding(28).frame(width: 460).background(Palette.background).foregroundStyle(Palette.text)
    }
}

struct AddSecurity: View {
    @ObservedObject var model: MarketModel
    @Environment(\.dismiss) private var dismiss
    @State private var symbol = ""
    @State private var error: String?
    var body: some View {
        VStack(alignment: .leading, spacing: 18) {
            Text("添加自选股").font(.title2).fontWeight(.semibold)
            TextField("US.AAPL", text: $symbol).textFieldStyle(.roundedBorder).onSubmit(add)
            Text("美股 US.AAPL · 港股 HK.00700\n沪股 SH.600519 · 深股 SZ.000001").foregroundStyle(Palette.muted)
            if let error { Text(error).foregroundStyle(Palette.orange) }
            HStack { Spacer(); Button("取消") { dismiss() }.keyboardShortcut(.cancelAction); Button("添加", action: add).buttonStyle(.borderedProminent).tint(Palette.orange).keyboardShortcut(.defaultAction) }
        }.padding(28).frame(width: 390).background(Palette.background).foregroundStyle(Palette.text)
    }
    private func add() { error = model.add(symbol); if error == nil { dismiss() } }
}
