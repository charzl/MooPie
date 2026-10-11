import uuid
from types import SimpleNamespace
from PySide6.QtCore import Qt, QSettings, QTimer, QUrl, QItemSelectionModel
from PySide6.QtGui import QDesktopServices, QShortcut, QKeySequence
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTableView, QHeaderView, QAbstractItemView, QSplitter, QDialog, QFormLayout,
    QSpinBox, QCheckBox, QDialogButtonBox, QInputDialog, QMessageBox, QMenu, QStackedWidget)
from .market import (DEFAULT_SYMBOLS, NAMES, PERIODS, symbol, demo_quote, demo_candles,
                     Quote, parse_candles, merge_candles, compact)
from .gateway import Gateway
from .runtime import OpenDRuntime
from .account_ui import WatchlistDialog, AccountsDialog
from .chart import CandleChart, BG, TEXT, MUTED, RED, GREEN, ORANGE
from .table import QuoteTableModel, QuoteDelegate

STYLE = """
QWidget { background:#15161b; color:#dce0e9; font-family:'Arial'; font-size:12px; }
QPushButton { border:1px solid #343d4b; border-radius:4px; padding:6px 10px; background:transparent; }
QPushButton:hover { background:#242934; }
QPushButton:checked { background:#dce0e9; color:#15161b; border-color:#dce0e9; }
QPushButton#connect { background:#ff7109; color:white; border:0; border-radius:15px; font-weight:bold; padding:7px 18px; }
QPushButton#nav { text-align:left; border:0; font-size:14px; padding:12px 9px; }
QPushButton#nav:checked { background:#15161b; color:#ff7109; }
QWidget#sidebar, QWidget#sidebar QLabel, QWidget#sidebar QPushButton { background:#222c37; }
QWidget#sidebar QPushButton:checked { background:#15161b; }
QLineEdit,QSpinBox { background:#1b1e24; border:1px solid #343d4b; padding:7px; border-radius:5px; }
QTableView { border:0; background:#15161b; gridline-color:#15161b; outline:none; }
QHeaderView::section { background:#15161b; color:#939caa; border:0; padding:8px 5px; font-size:10px; }
QScrollBar:vertical { background:#15161b; width:7px; }
QScrollBar::handle:vertical { background:#394252; border-radius:3px; min-height:30px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height:0; }
QSplitter::handle { background:#343d4b; width:3px; }
QMenu { background:#222731; border:1px solid #343d4b; }
QMenu::item { padding:8px 20px; }
QMenu::item:selected { background:#343d4b; }
"""

class MainWindow(QMainWindow):
    def __init__(self, settings=None):
        super().__init__()
        self.setWindowTitle("MooPython — Python + Qt + 官方 SDK")
        self.resize(1500,900)
        self.setMinimumSize(1150,680)
        self.settings = settings or QSettings("MooClients", "MooPython")
        saved = self.settings.value("symbols", DEFAULT_SYMBOLS)
        if isinstance(saved,str):
            saved = [saved]
        codes=[]
        for value in saved:
            try:
                code = symbol(value)
                if code not in codes: codes.append(code)
            except ValueError:
                pass
        self.state = SimpleNamespace(symbols=codes or list(DEFAULT_SYMBOLS), names=self.settings.value('names', {}) or {}, favorites=set(self.settings.value("favorites",["US.PLTR","US.NVDA","US.AAPL"])),
                                     quotes={}, sparks={}, red_up=self.settings.value("red_up",True,type=bool))
        self.selected = self.state.symbols[0]
        self.period="日K"
        self.token=uuid.uuid4().hex
        self.chart_request=""
        self.mode="demo"
        self.closing=False
        self.closed=False
        self.pending_quotes={}
        self.account_page = None
        self.gateway=Gateway(self)
        self.runtime = OpenDRuntime(self)
        self.runtime.status.connect(self.set_message)
        self.gateway.event.connect(self.on_event)
        self.gateway.stopped.connect(self.shutdown_finished)
        self.build_ui()
        self.flush_timer=QTimer(self)
        self.flush_timer.setSingleShot(True)
        self.flush_timer.setInterval(250)
        self.flush_timer.timeout.connect(self.flush_quotes)
        self.health_timer=QTimer(self)
        self.health_timer.setInterval(30_000)
        self.health_timer.timeout.connect(lambda:self.gateway.send("state",self.token) if self.mode == "live" else None)
        self.show_demo()
        QShortcut(QKeySequence("Ctrl+R"),self,activated=self.refresh)

    def build_ui(self):
        root=QWidget(); outer=QHBoxLayout(root); outer.setContentsMargins(0,0,0,0); outer.setSpacing(0)
        sidebar=QWidget(); sidebar.setObjectName("sidebar"); sidebar.setFixedWidth(112)
        side=QVBoxLayout(sidebar); side.setContentsMargins(7,20,7,15); side.setSpacing(8)
        avatar=QLabel("◉"); avatar.setStyleSheet("font-size:32px;color:#939caa;padding:10px;"); side.addWidget(avatar)
        self.nav_buttons = {}
        for name,icon in [("账户","▣"),("图表","▥"),("期权","⌁"),("观察","◎"),("市场","◉"),("自定义","⊞"),("发现","◈")]:
            b=QPushButton(f"{icon}  {name}"); b.setObjectName("nav"); b.setCheckable(name in ('账户','图表')); b.setChecked(name=="图表")
            self.nav_buttons[name] = b
            if name == '账户': b.clicked.connect(self.show_accounts)
            elif name == '图表': b.clicked.connect(self.show_charts)
            elif name != "图表": b.clicked.connect(lambda:QMessageBox.information(self,"看盘客户端","当前实现行情、自选分组导入及只读账户查询。交易、期权链与社区尚未实现。"))
            side.addWidget(b)
        side.addStretch()
        b=QPushButton("⊕  添加自选"); b.clicked.connect(self.add_symbol); side.addWidget(b)
        b=QPushButton("⚙  设置"); b.clicked.connect(self.connection_settings); side.addWidget(b)
        outer.addWidget(sidebar)
        body=QWidget(); vertical=QVBoxLayout(body); vertical.setContentsMargins(0,0,0,0); vertical.setSpacing(0)
        top=QWidget(); top.setFixedHeight(48); topbox=QHBoxLayout(top); topbox.setContentsMargins(14,0,14,0)
        refresh=QPushButton("↻"); refresh.setToolTip("刷新行情 ⌘R"); refresh.clicked.connect(self.refresh); topbox.addWidget(refresh)
        self.search=QLineEdit(); self.search.setPlaceholderText("⌕ 搜索自选股"); self.search.setFixedWidth(210); self.search.textChanged.connect(self.search_changed); topbox.addWidget(self.search)
        topbox.addStretch()
        title=QLabel("<span style='color:#ff7109'>⌁</span> <b>MooPython</b> <span style='font-size:10px;color:#ff7109'>Qt</span>")
        title.setStyleSheet("font-size:20px;"); topbox.addWidget(title); topbox.addStretch()
        self.mode_label=QLabel("演示数据"); self.mode_label.setStyleSheet("color:#ff7109;"); topbox.addWidget(self.mode_label)
        self.connect_button=QPushButton("连接 OpenD"); self.connect_button.setObjectName("connect"); self.connect_button.clicked.connect(self.connection_settings); topbox.addWidget(self.connect_button)
        vertical.addWidget(top)
        self.splitter=QSplitter(Qt.Orientation.Horizontal)
        watch=QWidget(); watchbox=QVBoxLayout(watch); watchbox.setContentsMargins(5,0,5,0); watchbox.setSpacing(0)
        heading=QHBoxLayout(); heading.setContentsMargins(9,10,9,10)
        self.count_label=QLabel("自选股"); heading.addWidget(self.count_label); heading.addStretch()
        cloud=QPushButton('moomoo 自选'); cloud.clicked.connect(self.show_watchlist); heading.addWidget(cloud)
        add=QPushButton("+"); add.setFixedSize(24,24); add.clicked.connect(self.add_symbol); heading.addWidget(add); watchbox.addLayout(heading)
        filters=QHBoxLayout(); filters.setContentsMargins(6,5,6,10); filters.setSpacing(5)
        self.filter_buttons={}
        for name in ("全部","特别关注","美股","港股","沪深"):
            b=QPushButton(name); b.setCheckable(True); b.setChecked(name=="全部"); b.setStyleSheet("font-size:11px;padding:5px 8px;")
            b.clicked.connect(lambda checked,n=name:self.change_filter(n)); self.filter_buttons[name]=b; filters.addWidget(b)
        filters.addStretch(); watchbox.addLayout(filters)
        self.table_model=QuoteTableModel(self.state)
        self.table=QTableView(); self.table.setModel(self.table_model); self.table.setItemDelegate(QuoteDelegate(self.state,self.table))
        self.table.verticalHeader().hide(); self.table.verticalHeader().setDefaultSectionSize(58)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers); self.table.setShowGrid(False)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        header=self.table.horizontalHeader(); header.setSectionResizeMode(0,QHeaderView.ResizeMode.Fixed); header.resizeSection(0,110)
        header.setSectionResizeMode(1,QHeaderView.ResizeMode.Stretch)
        for i,w in [(2,83),(3,82),(4,74)]: header.setSectionResizeMode(i,QHeaderView.ResizeMode.Fixed); header.resizeSection(i,w)
        header.setSectionsClickable(True); header.sectionClicked.connect(self.sort_column)
        self.table.clicked.connect(self.table_clicked)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu); self.table.customContextMenuRequested.connect(self.row_menu)
        watchbox.addWidget(self.table)
        self.watch_footer=QLabel("合成示例 · 非实际行情"); self.watch_footer.setStyleSheet("color:#939caa;font-size:10px;padding:9px;"); watchbox.addWidget(self.watch_footer)
        watch.setMinimumWidth(410); self.splitter.addWidget(watch)
        chart_panel=QWidget(); charts=QVBoxLayout(chart_panel); charts.setContentsMargins(10,0,10,0); charts.setSpacing(0)
        self.quote_heading=QLabel(); self.quote_heading.setFixedHeight(40); self.quote_heading.setStyleSheet("font-size:13px;border-bottom:1px solid #343d4b;"); charts.addWidget(self.quote_heading)
        periods=QHBoxLayout(); periods.setContentsMargins(0,6,0,6); periods.setSpacing(5)
        self.period_buttons={}
        for period in PERIODS:
            b=QPushButton(period); b.setCheckable(True); b.setChecked(period==self.period); b.setStyleSheet("font-size:11px;padding:5px 8px;")
            b.clicked.connect(lambda checked,p=period:self.set_period(p)); self.period_buttons[period]=b; periods.addWidget(b)
        periods.addStretch()
        self.line_button=QPushButton("⌁"); self.line_button.setToolTip("切换收盘价曲线 / K 线"); self.line_button.clicked.connect(self.toggle_line); periods.addWidget(self.line_button)
        for title,delta in [("＋",-30),("－",30)]:
            b=QPushButton(title); b.setFixedWidth(30); b.clicked.connect(lambda checked,d=delta:self.chart.zoom(d)); periods.addWidget(b)
        charts.addLayout(periods)
        self.stats=QLabel(); self.stats.setFixedHeight(28); self.stats.setStyleSheet("font-size:10px;"); charts.addWidget(self.stats)
        self.chart=CandleChart(); charts.addWidget(self.chart,1)
        indicators=QHBoxLayout(); indicators.setContentsMargins(0,0,0,0)
        self.ma_button=QPushButton("MA"); self.ma_button.setCheckable(True); self.ma_button.setChecked(True); self.ma_button.clicked.connect(self.toggle_ma); indicators.addWidget(self.ma_button)
        indicators.addWidget(QLabel("MA5 / MA10 / MA20 / MA60    成交量")); indicators.addStretch(); indicators.addWidget(QLabel("前复权")); charts.addLayout(indicators)
        self.splitter.addWidget(chart_panel); self.splitter.setSizes([460,920]); self.splitter.setStretchFactor(1,1)
        vertical.addWidget(self.splitter,1)
        statusrow=QHBoxLayout(); statusrow.setContentsMargins(10,0,10,0)
        self.status=QLabel(); self.status.setStyleSheet("font-size:10px;"); statusrow.addWidget(self.status,1)
        self.time_label=QLabel(); self.time_label.setStyleSheet("color:#939caa;font-size:10px;"); statusrow.addWidget(self.time_label)
        bottom=QWidget(); bottom.setFixedHeight(27); bottom.setLayout(statusrow); vertical.addWidget(bottom)
        self.pages = QStackedWidget(); self.pages.addWidget(body)
        outer.addWidget(self.pages,1); self.setCentralWidget(root); self.setStyleSheet(STYLE)

    def set_message(self,text):
        self.status.setText(text[:160]); self.status.setToolTip(text)

    def persist(self):
        self.settings.setValue("symbols",self.state.symbols)
        self.settings.setValue('names', self.state.names)
        self.settings.setValue("favorites",list(self.state.favorites))
        self.settings.setValue("red_up",self.state.red_up)

    def update_table(self,rebuild=False):
        if rebuild or self.table_model.sort_column>=0:
            self.table_model.rebuild()
        elif self.table_model.rows:
            self.table_model.dataChanged.emit(self.table_model.index(0,0),self.table_model.index(len(self.table_model.rows)-1,4))
        if self.selected in self.table_model.rows:
            index=self.table_model.index(self.table_model.rows.index(self.selected),0)
            self.table.selectionModel().select(index,QItemSelectionModel.SelectionFlag.ClearAndSelect | QItemSelectionModel.SelectionFlag.Rows)
        else:
            self.table.clearSelection()
        self.count_label.setText(f"自选股  {len(self.table_model.rows)}")

    def show_demo(self):
        self.token=uuid.uuid4().hex; self.chart_request=""; self.pending_quotes.clear()
        self.gateway.send("disconnect",self.token); self.mode="demo"; self.health_timer.stop()
        self.state.quotes={c:demo_quote(c) for c in self.state.symbols}
        self.state.sparks={c:[b.close for b in demo_candles(c)[-60:]] for c in self.state.symbols}
        self.chart.message=""; self.chart.set_bars(demo_candles(self.selected,self.period),self.period)
        self.mode_label.setText("演示数据"); self.connect_button.setText("连接 OpenD")
        self.watch_footer.setText("合成示例 · 非实际行情")
        self.set_message("演示数据 · 所有价格均为合成示例，连接 OpenD 后显示实际行情")
        self.update_table(True); self.update_heading()

    def disconnect(self):
        self.token=uuid.uuid4().hex; self.chart_request=""; self.pending_quotes.clear()
        self.gateway.send("disconnect",self.token); self.health_timer.stop(); self.mode="disconnected"
        self.mode_label.setText("已断开 · 数据停更"); self.connect_button.setText("连接 OpenD")
        self.chart.message=""; self.chart.update()
        self.set_message("连接已断开；保留上次数据")

    def connect_gateway(self,host,port):
        if host not in ("127.0.0.1","localhost","::1"):
            self.set_message("仅支持本机 OpenD：127.0.0.1 / localhost / ::1"); return
        self.token=uuid.uuid4().hex; self.chart_request=""; self.pending_quotes.clear()
        self.mode="connecting"; self.state.quotes.clear(); self.state.sparks.clear(); self.chart.set_bars([])
        self.chart.message="正在连接 OpenD…"; self.mode_label.setText("连接中"); self.health_timer.stop()
        self.set_message("正在连接本机 OpenD…"); self.update_table(); self.update_heading()
        self.settings.setValue("host",host); self.settings.setValue("port",port)
        self.gateway.send("connect",self.token,host=host,port=port,symbols=list(self.state.symbols[:30]))

    def on_event(self,token,kind,data):
        if token != self.token or self.closing:
            return
        if kind == "connected":
            self.mode="live"; self.mode_label.setText("OpenD 行情"); self.connect_button.setText("连接设置"); self.watch_footer.setText("报价时间以 OpenD 返回为准")
            self.set_message("已连接 · 行情实时性取决于账户权限和市场状态"); self.health_timer.start(); self.load_chart()
        elif kind == "quotes":
            for row in data:
                try:
                    quote=Quote.from_row(row)
                    if quote.code in self.state.symbols: self.pending_quotes[quote.code]=quote
                except (ValueError,KeyError): pass
            if not self.flush_timer.isActive(): self.flush_timer.start()
        elif kind == "candles" and data["request"] == self.chart_request:
            bars=parse_candles(data["rows"])
            self.chart.message="" if bars else "OpenD 暂未返回 K 线，请检查行情权限"
            self.chart.set_bars(bars,self.period)
        elif kind == "candle_push":
            rows=[r for r in data if r.get("code")==self.selected and r.get("k_type")==PERIODS[self.period]]
            if rows:
                self.chart.set_bars(merge_candles(self.chart.bars,parse_candles(rows)),self.period)
        elif kind == "chart_error" and data["request"] == self.chart_request:
            self.chart.message=data["message"]; self.chart.update()
        elif kind in ("connection_error","lost"):
            self.mode="disconnected"; self.chart_request=""; self.health_timer.stop()
            self.mode_label.setText("连接失败" if kind=="connection_error" else "数据停更")
            self.chart.message="连接失败，请检查 OpenD 是否运行并登录" if not self.chart.bars else ""
            self.chart.update(); self.set_message(data)
        elif kind in ("message","refreshed"):
            self.set_message(str(data))

    def flush_quotes(self):
        if self.mode not in ("live","connecting"):
            self.pending_quotes.clear(); return
        for code,quote in self.pending_quotes.items():
            self.state.quotes[code]=quote
            self.state.sparks[code]=(self.state.sparks.get(code,[])+[quote.price])[-80:]
        self.pending_quotes.clear(); self.update_table(); self.update_heading()

    def update_heading(self):
        q=self.state.quotes.get(self.selected)
        name=q.name if q else self.state.names.get(self.selected, NAMES.get(self.selected,""))
        color=RED if q and (q.change>0)==self.state.red_up else GREEN
        suffix=f"<span style='color:{color}'>{q.price:.3f}  {q.change:+.3f}  {q.percent:+.2f}%</span>" if q else ""
        from html import escape
        self.quote_heading.setText(f"<b>⌕  {escape(self.selected.split('.',1)[1])}  {escape(name)}</b>   {suffix}")
        if q:
            self.stats.setText(f"开 {q.open:.3f}    高 {q.high:.3f}    低 {q.low:.3f}    收 {q.price:.3f}    量 {compact(q.volume)}    额 {compact(q.turnover)}")
            self.time_label.setText(q.updated+"  ·  Python / Qt")
        else:
            self.stats.setText("等待行情数据"); self.time_label.setText("Python / Qt")

    def select_symbol(self,code):
        self.selected=code; self.chart_request=uuid.uuid4().hex; self.update_table(); self.update_heading()
        if self.mode=="demo":
            self.chart.message=""; self.chart.set_bars(demo_candles(code,self.period),self.period)
        elif self.mode=="live":
            self.gateway.send('refresh', self.token, symbols=[code]); self.load_chart()
        else: self.chart.set_bars([]); self.chart.message="连接 OpenD 以获取 K 线"

    def load_chart(self):
        if self.mode != "live": return
        self.chart_request=uuid.uuid4().hex; self.chart.set_bars([]); self.chart.message="加载 K 线…"
        self.gateway.send("chart",self.token,code=self.selected,period=self.period,request=self.chart_request)

    def refresh(self):
        if self.mode=="live":
            codes = [self.selected] + [c for c in self.state.symbols if c != self.selected][:29]
            self.gateway.send("refresh",self.token,symbols=codes); self.load_chart()
        elif self.mode=="demo": self.select_symbol(self.selected)
        else: self.connection_settings()

    def table_clicked(self,index):
        self.select_symbol(index.data(Qt.ItemDataRole.UserRole))

    def search_changed(self,value):
        self.table_model.search=value; self.update_table(True)

    def change_filter(self,value):
        self.table_model.filter=value
        for name,button in self.filter_buttons.items(): button.setChecked(name==value)
        self.update_table(True)

    def sort_column(self,column):
        order=Qt.SortOrder.AscendingOrder if self.table_model.sort_column==column and self.table_model.sort_order==Qt.SortOrder.DescendingOrder else Qt.SortOrder.DescendingOrder
        self.table_model.sort(column,order); self.update_table()

    def set_period(self,period):
        self.period=period
        for name,b in self.period_buttons.items(): b.setChecked(name==period)
        self.select_symbol(self.selected)

    def toggle_line(self): self.chart.line_mode=not self.chart.line_mode; self.chart.invalidate()
    def toggle_ma(self): self.chart.show_ma=self.ma_button.isChecked(); self.chart.invalidate()

    def add_symbol(self):
        value,ok=QInputDialog.getText(self,"添加自选股","US.AAPL / HK.00700 / SH.600519 / SZ.000001")
        if not ok: return
        try:
            code=symbol(value)
            if code not in self.state.symbols:
                self.state.symbols.append(code); self.persist()
                if self.mode=="demo":
                    self.state.quotes[code]=demo_quote(code); self.state.sparks[code]=[b.close for b in demo_candles(code)[-60:]]
                elif self.mode=="live": self.gateway.send("refresh",self.token,symbols=[code])
            self.update_table(True); self.select_symbol(code)
        except ValueError as error: QMessageBox.warning(self,"代码格式",str(error))

    def row_menu(self,point):
        index=self.table.indexAt(point)
        if not index.isValid(): return
        code=index.data(Qt.ItemDataRole.UserRole); menu=QMenu(self)
        favorite=menu.addAction("取消特别关注" if code in self.state.favorites else "特别关注")
        remove=menu.addAction("移除自选"); action=menu.exec(self.table.viewport().mapToGlobal(point))
        if action==favorite:
            if code in self.state.favorites: self.state.favorites.remove(code)
            else: self.state.favorites.add(code)
        elif action==remove:
            if len(self.state.symbols)<=1: self.set_message("至少保留一只自选股"); return
            self.state.symbols.remove(code); self.state.quotes.pop(code,None); self.state.favorites.discard(code)
            if self.mode=="live": self.gateway.send("remove",self.token,code=code)
            if self.selected==code: self.select_symbol(self.state.symbols[0])
        self.persist(); self.update_table(True)

    def show_accounts(self):
        if self.mode != 'live':
            self.nav_buttons['账户'].setChecked(False)
            self.set_message('请先连接 OpenD，再读取账户'); self.connection_settings(); return
        if self.account_page is None or self.account_page.session != self.token:
            if self.account_page is not None:
                self.account_page.cleanup(); self.pages.removeWidget(self.account_page); self.account_page.deleteLater()
            self.account_page = AccountsDialog(self); self.pages.addWidget(self.account_page)
        self.pages.setCurrentWidget(self.account_page)
        self.nav_buttons['账户'].setChecked(True); self.nav_buttons['图表'].setChecked(False)

    def show_charts(self):
        self.pages.setCurrentIndex(0)
        self.nav_buttons['账户'].setChecked(False); self.nav_buttons['图表'].setChecked(True)

    def show_watchlist(self):
        if self.mode != 'live':
            self.set_message('请先连接 OpenD，再读取账号自选股'); self.connection_settings(); return
        WatchlistDialog(self).exec()

    def import_watchlist(self, rows, group):
        codes = []; names = {}; skipped = 0
        for row in rows:
            try: code = symbol(row.get('code', ''))
            except (ValueError, AttributeError): skipped += 1; continue
            if code not in codes: codes.append(code)
            if isinstance(row.get('name'), str): names[code] = row['name']
        if not codes:
            self.set_message('分组为空或没有当前支持的 US/HK/SH/SZ 标的，本地列表保留'); return
        self.settings.setValue('watchlist_backup', self.state.symbols)
        for code in self.state.symbols:
            if code not in codes: self.gateway.send('remove', self.token, code=code)
        self.state.symbols = codes; self.state.names = names
        self.state.quotes.clear(); self.state.sparks.clear(); self.pending_quotes.clear()
        self.search.clear(); self.change_filter('全部'); self.selected = codes[0]
        self.persist(); self.update_table(True); self.select_symbol(codes[0])
        self.gateway.send('refresh', self.token, symbols=codes[1:30])
        self.set_message(f'已导入 {group}：{len(codes)} 个标的；跳过 {skipped} 个不支持的标的。最多同时订阅 30 只报价，其余选中后读取')

    def connection_settings(self):
        dialog=QDialog(self); dialog.setWindowTitle("连接 OpenD"); dialog.setFixedWidth(450)
        layout=QVBoxLayout(dialog); layout.setContentsMargins(24,24,24,24); layout.setSpacing(15)
        text=QLabel("先在官方 moomoo OpenD 中登录。客户端不保存账户密码，仅连接本机网关。"); text.setWordWrap(True); layout.addWidget(text)
        form=QFormLayout(); host=QLineEdit(self.settings.value("host","127.0.0.1")); port=QSpinBox(); port.setRange(1,65535); port.setValue(int(self.settings.value("port",11111)))
        form.addRow("地址",host); form.addRow("端口",port); layout.addLayout(form)
        for title,action in [("启动内置 OpenD / 登录","launch"),("检查 OpenD 更新","update"),("回退上一版 OpenD","rollback")]:
            button=QPushButton(title); button.clicked.connect(lambda checked,a=action:self.runtime.run(a)); layout.addWidget(button)
        runtime_status=QLabel("内置官方 OpenD · 自动检查更新"); runtime_status.setWordWrap(True); self.runtime.status.connect(runtime_status.setText); layout.addWidget(runtime_status)
        download=QPushButton("官方 OpenD 下载页 ↗"); download.clicked.connect(lambda:QDesktopServices.openUrl(QUrl("https://www.moomoo.com/download/OpenAPI"))); layout.addWidget(download)
        colors=QCheckBox("红涨绿跌"); colors.setChecked(self.state.red_up); layout.addWidget(colors)
        text=QLabel("此版本仅支持本机、未配置 RSA 加密的 OpenD。实际行情权限、订阅配额和延迟由账户决定。"); text.setWordWrap(True); text.setStyleSheet("color:#939caa;font-size:11px;"); layout.addWidget(text)
        buttons=QHBoxLayout()
        demo=QPushButton("演示数据"); demo.clicked.connect(lambda:(self.show_demo(),dialog.accept())); buttons.addWidget(demo)
        if self.mode in ("live","connecting"):
            disconnect=QPushButton("断开"); disconnect.clicked.connect(lambda:(self.disconnect(),dialog.accept())); buttons.addWidget(disconnect)
        buttons.addStretch(); cancel=QPushButton("关闭"); cancel.clicked.connect(dialog.reject); buttons.addWidget(cancel)
        connect=QPushButton("连接"); connect.setObjectName("connect"); connect.clicked.connect(lambda:(self.connect_gateway(host.text().strip(),port.value()),dialog.accept())); buttons.addWidget(connect)
        layout.addLayout(buttons); dialog.exec()
        self.state.red_up=colors.isChecked(); self.chart.red_up=self.state.red_up; self.chart.invalidate(); self.persist(); self.update_table(); self.update_heading()

    def shutdown_finished(self):
        self.closed=True
        if self.closing: self.close()

    def closeEvent(self,event):
        if self.closed:
            self.persist(); event.accept(); return
        event.ignore()
        if not self.closing:
            self.closing=True; self.health_timer.stop(); self.flush_timer.stop(); self.setEnabled(False)
            if self.account_page is not None: self.account_page.cleanup(); self.account_page.clear_data()
            self.gateway.shutdown()
