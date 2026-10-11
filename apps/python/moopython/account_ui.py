"""On-demand, asynchronous account and official watchlist dialogs."""
import math
import uuid
from PySide6.QtCore import QTimer, Qt, QSize
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox, QTableWidget, QTableWidgetItem, QAbstractItemView, QWidget, QTabWidget, QListWidget, QSplitter


def display(value, precision=2):
    if value is None or isinstance(value, str) and value in ('N/A', 'nan'): return '—'
    if isinstance(value, (int, float)):
        return f'{value:,.{precision}f}' if math.isfinite(value) and abs(value) < 1e100 else '—'
    return str(value)


def table_rows(table, rows, columns):
    table.setRowCount(len(rows))
    for index, row in enumerate(rows):
        for column, key in enumerate(columns):
            precision = 4 if key in ('nominal_price', 'average_cost_price') else 3 if key in ('qty', 'can_sell_qty') else 2
            table.setItem(index, column, QTableWidgetItem(display(row.get(key), precision)))
    table.resizeColumnsToContents()


class PositionsTable(QTableWidget):
    def __init__(self, columns):
        super().__init__(0, columns)
        self.empty = QLabel('暂无持仓数据', self.viewport())
        self.empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty.setStyleSheet('color:#939caa;font-size:13px;')

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.empty.setGeometry(self.viewport().rect())

    def setRowCount(self, count):
        super().setRowCount(count)
        if hasattr(self, 'empty'): self.empty.setVisible(count == 0)


class QueryDialog(QDialog):
    def __init__(self, window, title):
        super().__init__(window)
        self.window = window; self.session = window.token; self.request = ''; self.busy = False
        self.setWindowTitle(title); self.resize(850, 540)
        self.layout = QVBoxLayout(self); self.status = QLabel(); self.status.setWordWrap(True)
        self.controls = []
        window.gateway.event.connect(self.receive)
        self.finished.connect(self.cleanup)
        self.guard = QTimer(self); self.guard.setInterval(250)
        self.guard.timeout.connect(self.check_session); self.guard.start()

    def check_session(self):
        if self.window.token != self.session or self.window.mode != 'live':
            self.request = ''; self.clear_data()
            self.status.setText('连接已断开或改变，请关闭此窗口并重新连接')
            for control in self.controls: control.setEnabled(False)
            if hasattr(self, 'apply'): self.apply.setEnabled(False)

    def send(self, op, **fields):
        if self.window.mode != 'live' or self.window.token != self.session:
            self.status.setText('连接已断开或改变，请重新连接并打开此窗口'); self.clear_data(); return
        self.request = uuid.uuid4().hex; self.busy = True
        for control in self.controls: control.setEnabled(False)
        self.status.setText('读取 OpenD 数据…')
        self.window.gateway.send(op, self.session, request=self.request, **fields)

    def receive(self, token, kind, data):
        if token != self.session: return
        if kind in ('connection_error', 'lost', 'disconnected'):
            self.request = ''; self.clear_data(); self.status.setText('连接已断开，请重新连接后再打开此窗口'); return
        if kind not in ('user_data', 'user_data_error') or data.get('request') != self.request: return
        if self.window.token != self.session:
            self.clear_data(); self.status.setText('连接已改变，旧结果已忽略'); return
        self.busy = False
        for control in self.controls: control.setEnabled(True)
        if kind == 'user_data_error':
            self.clear_data(); self.status.setText('读取失败：' + data['error'])
        else: self.result(data)

    def cleanup(self):
        self.request = ''
        self.guard.stop()
        try: self.window.gateway.event.disconnect(self.receive)
        except RuntimeError: pass

    def clear_data(self): pass


class WatchlistDialog(QueryDialog):
    def __init__(self, window):
        super().__init__(window, 'moomoo 账号自选股')
        self.rows = []
        text = QLabel('读取当前 OpenD 登录账号的自选分组。导入后替换客户端本地列表；官方自选不会被修改。')
        text.setWordWrap(True); self.layout.addWidget(text)
        top = QHBoxLayout(); self.groups = QComboBox(); top.addWidget(self.groups, 1)
        refresh = QPushButton('获取分组'); refresh.clicked.connect(self.load_groups); top.addWidget(refresh)
        read = QPushButton('读取分组'); read.clicked.connect(self.load_group); top.addWidget(read)
        self.layout.addLayout(top)
        self.table = QTableWidget(0, 2); self.table.setHorizontalHeaderLabels(['股票代码', '名称'])
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers); self.layout.addWidget(self.table)
        self.layout.addWidget(self.status)
        self.apply = QPushButton('导入此分组'); self.apply.setEnabled(False); self.apply.clicked.connect(self.import_group)
        self.layout.addWidget(self.apply); self.controls = [self.groups, refresh, read]
        self.groups.currentIndexChanged.connect(self.clear_data)
        self.load_groups()

    def clear_data(self, *_):
        self.rows = []; self.table.setRowCount(0); self.apply.setEnabled(False)

    def load_groups(self):
        self.clear_data(); self.groups.clear(); self.send('watchlist_groups')

    def load_group(self):
        self.clear_data()
        if self.groups.currentText(): self.send('watchlist', group=self.groups.currentText())

    def result(self, data):
        if data['op'] == 'watchlist_groups':
            self.groups.clear()
            for row in data['rows']: self.groups.addItem(row['group_name'])
            self.status.setText(f'找到 {self.groups.count()} 个分组，选择后点击“读取分组”')
        else:
            self.rows = data['rows']; table_rows(self.table, self.rows, ['code', 'name'])
            self.apply.setEnabled(bool(self.rows)); self.status.setText(f'分组包含 {len(self.rows)} 个标的')

    def import_group(self):
        if self.window.token != self.session or self.window.mode != 'live':
            self.clear_data(); self.status.setText('连接已改变，请重新读取'); return
        self.window.import_watchlist(self.rows, self.groups.currentText()); self.accept()


class AccountsDialog(QueryDialog):
    def reject(self):
        if self.window.account_page is self:
            self.window.show_charts()
        else:
            super().reject()

    def __init__(self, window):
        super().__init__(window, '账户资产与持仓（只读）')
        self.setWindowFlags(Qt.WindowType.Widget)
        self.setObjectName('accountPage')
        self.setStyleSheet("QWidget#accountPage, QWidget#accountPage QWidget { background:#13181d; } QListWidget { border:0; } QListWidget::item { border:1px solid #28313d; padding:14px; margin:5px 0; } QListWidget::item:selected { border:1px solid #8995a7; background:#1c232d; } QTabWidget::pane { border:0; } QTabBar::tab { padding:10px 15px; border:0; } QTabBar::tab:selected { border-bottom:2px solid #aab6c6; } QHeaderView::section { background:#13181d; color:#939caa; border:0; border-bottom:1px solid #28313d; padding:10px; }")
        self.layout.setContentsMargins(0,0,0,0)
        split = QSplitter(Qt.Orientation.Horizontal); self.layout.addWidget(split)
        left = QWidget(); left.setMinimumWidth(250); left.setMaximumWidth(360)
        rail = QVBoxLayout(left); rail.setContentsMargins(14,14,14,14); rail.setSpacing(14)
        self.firm = QComboBox()
        for title, key in [('moomoo US', 'FUTUINC'), ('富途香港', 'FUTUSECURITIES'), ('moomoo SG', 'FUTUSG'), ('moomoo AU', 'FUTUAU'), ('moomoo CA', 'FUTUCA'), ('moomoo MY', 'FUTUMY')]: self.firm.addItem(title, key)
        rail.addWidget(self.firm)
        self.asset_title = QLabel('所选账户总资产 · USD'); rail.addWidget(self.asset_title)
        self.asset_value = QLabel('—'); self.asset_value.setStyleSheet('font-size:25px;font-weight:600;'); rail.addWidget(self.asset_value)
        filters = QHBoxLayout(); self.market = QComboBox(); self.market.addItems(['US', 'HK', 'SG', 'AU', 'CA', 'MY'])
        self.currency = QComboBox(); self.currency.addItems(['USD', 'HKD', 'SGD', 'AUD', 'CAD', 'MYR', 'CNH'])
        filters.addWidget(self.market); filters.addWidget(self.currency); rail.addLayout(filters)
        refresh = QPushButton('刷新账户列表'); refresh.clicked.connect(self.load_accounts); rail.addWidget(refresh)
        self.accounts = QComboBox(); rail.addWidget(self.accounts)
        self.cards = QListWidget(); self.cards.currentRowChanged.connect(self.choose_card); rail.addWidget(self.cards,1)
        read = QPushButton('刷新资产与持仓'); read.clicked.connect(self.load_details); rail.addWidget(read)
        rail.addWidget(QLabel('只读账户 · 通过官方 OpenD 查询'))
        split.addWidget(left)
        right = QWidget(); content = QVBoxLayout(right); content.setContentsMargins(12,0,12,12)
        self.tabs = QTabWidget(); content.addWidget(self.tabs,1)
        holdings = QWidget(); holding_layout = QVBoxLayout(holdings); holding_layout.setContentsMargins(0,10,0,0)
        self.summary = QLabel('尚未查询资产'); self.summary.setWordWrap(True); holding_layout.addWidget(self.summary)
        self.table = PositionsTable(10)
        self.table.setHorizontalHeaderLabels(['名称/代码', '名称', '数量', '可用数量', '市价', '平均成本', '今日盈亏', '持仓盈亏', '市值', '币种'])
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers); self.table.setShowGrid(False)
        self.table.verticalHeader().hide(); holding_layout.addWidget(self.table,1)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.tabs.addTab(holdings,'持仓')
        self.funds_table = QTableWidget(0,2); self.funds_table.setHorizontalHeaderLabels(['资产项目', '金额'])
        self.funds_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers); self.funds_table.verticalHeader().hide()
        self.tabs.addTab(self.funds_table,'资产')
        for title in ('订单','历史','资金明细'):
            index = self.tabs.addTab(QWidget(),title); self.tabs.setTabEnabled(index,False)
            self.tabs.setTabToolTip(index,'此接口尚未接入')
        content.addWidget(self.status); split.addWidget(right); split.setSizes([280,950])
        self.controls = [self.firm, self.market, self.currency, self.accounts, self.cards, refresh, read]
        for control in (self.firm, self.market): control.currentIndexChanged.connect(self.selection_changed)
        self.accounts.currentIndexChanged.connect(self.clear_data); self.currency.currentIndexChanged.connect(self.clear_data)
        self.load_accounts()

    def choose_card(self, index):
        if index >= 0 and not self.busy:
            self.accounts.setCurrentIndex(index); self.load_details()

    def parameters(self): return dict(firm=self.firm.currentData(), market=self.market.currentText(), currency=self.currency.currentText())

    def clear_data(self, *_):
        self.summary.setText('尚未查询资产'); self.table.setRowCount(0); self.funds_table.setRowCount(0)
        self.asset_value.setText('—'); self.asset_title.setText('所选账户总资产 · '+self.currency.currentText())

    def selection_changed(self):
        self.accounts.clear(); self.cards.clear(); self.clear_data(); self.status.setText('券商或市场已改变，请重新获取账户')

    def load_accounts(self):
        self.accounts.clear(); self.cards.clear(); self.clear_data(); self.send('accounts', **self.parameters())

    def load_details(self):
        self.clear_data()
        if self.accounts.currentData() is not None:
            self.send('account_details', acc_id=self.accounts.currentData(), **self.parameters())
        else: self.status.setText('请先获取并选择账户')

    def result(self, data):
        if data['op'] == 'accounts':
            self.accounts.clear(); self.cards.blockSignals(True); self.cards.clear()
            for row in data['accounts']:
                identifier = row['acc_id']; env = '实盘' if row['trd_env'] == 'REAL' else '模拟'
                label = f'{env} · 账户尾号 {identifier[-4:]}'
                self.accounts.addItem(label, identifier); self.cards.addItem(label+'\n'+str(row.get('acc_type','证券账户')))
                self.cards.item(self.cards.count()-1).setSizeHint(QSize(200,72))
            self.cards.blockSignals(False)
            self.status.setText(f'找到 {self.accounts.count()} 个账户，请选择并查询' if self.accounts.count() else '未返回账户，请核对开户券商、交易市场与 OpenD 登录账号')
        else:
            funds = data['funds'][0] if data['funds'] else {}
            self.summary.setText('资产展示币种：' + data['currency'] + '\n' + '   '.join(title + ': ' + display(funds.get(key)) for title, key in [('总资产', 'total_assets'), ('现金', 'cash'), ('证券市值', 'market_val'), ('购买力', 'power')]))
            self.asset_value.setText(display(funds.get('total_assets')))
            table_rows(self.funds_table, [dict(field=k, value=v) for k,v in funds.items()], ['field','value'])
            table_rows(self.table, data['positions'], ['code', 'stock_name', 'qty', 'can_sell_qty', 'nominal_price', 'average_cost_price', 'today_pl_val', 'pl_val', 'market_val', 'currency'])
            self.status.setText(f'已读取 {len(data["positions"])} 条持仓；未返回的字段显示 —，持仓金额按各自币种展示')
