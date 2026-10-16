"""Read-only options, watchlists and market overview backed by official OpenD."""
import math
from PySide6.QtCore import Qt, QPointF, QRectF
from PySide6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton,
    QLineEdit, QComboBox, QTableWidget, QTableWidgetItem, QAbstractItemView, QTabWidget,
    QHeaderView, QSplitter, QGridLayout, QCheckBox)
from PySide6.QtGui import QPainter, QColor, QPainterPath, QPen, QLinearGradient
from .account_ui import QueryDialog, display
from .market import symbol, display_symbol, NAMES

SNAPSHOT_COLUMNS = [('code','代码'),('name','名称'),('last_price','最新价'),('change','涨跌额'),
    ('change_pct','涨跌幅 %'),('bid_price','买入价'),('ask_price','卖出价'),('bid_vol','买量'),
    ('ask_vol','卖量'),('volume','成交量'),('turnover','成交额'),('open_price','今开'),
    ('prev_close_price','昨收'),('high_price','最高'),('low_price','最低'),
    ('turnover_rate','换手率 %'),('pe_ttm_ratio','市盈率 TTM'),('pb_ratio','市净率'),('update_time','更新时间'),('quote_status','行情状态')]


def snapshot_rows(rows):
    result = []
    for row in rows:
        row = dict(row)
        last, previous = row.get('last_price'), row.get('prev_close_price')
        if isinstance(last, (int,float)) and isinstance(previous, (int,float)) and math.isfinite(last) and math.isfinite(previous) and previous > 0:
            row['change'] = last - previous; row['change_pct'] = (last / previous - 1) * 100
        result.append(row)
    return result


def make_table(columns):
    table = QTableWidget(0,len(columns)); table.setHorizontalHeaderLabels([label for _,label in columns])
    table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
    table.verticalHeader().hide(); table.setShowGrid(False)
    table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
    table.horizontalHeader().setStretchLastSection(True)
    return table


def fill(table, rows, columns):
    table.setSortingEnabled(False); table.setRowCount(len(rows))
    for i,row in enumerate(rows):
        for j,(key,_) in enumerate(columns):
            value = display_symbol(row.get(key)) if key == 'code' else row.get(key)
            item = QTableWidgetItem(display(value,4 if key in ('last_price','bid_price','ask_price','strike_price') else 2))
            if isinstance(value,(int,float)) and math.isfinite(value): item.setData(Qt.ItemDataRole.DisplayRole,value)
            if key in ('change','change_pct') and isinstance(value,(int,float)) and math.isfinite(value):
                from PySide6.QtGui import QColor
                item.setForeground(QColor('#f04458' if value > 0 else '#00b879' if value < 0 else '#939caa'))
            item.setData(Qt.ItemDataRole.UserRole,row.get('code'))
            table.setItem(i,j,item)
    table.setSortingEnabled(True)


class DataPage(QueryDialog):
    def __init__(self, window, title):
        super().__init__(window,title); self.setWindowFlags(Qt.WindowType.Widget)
        heading = QLabel(title); heading.setStyleSheet('font-size:20px;font-weight:bold;padding:12px 0;'); self.layout.addWidget(heading)
        self.rows = []

    def reject(self): self.window.show_charts()

    def ready(self):
        if self.window.mode != 'live':
            self.status.setText('请先在图表页连接 OpenD，再刷新本页。'); return False
        return True

    def open_row(self, table, index):
        item = table.item(index,0)
        if item and item.data(Qt.ItemDataRole.UserRole): self.window.open_chart_code(item.data(Qt.ItemDataRole.UserRole))


class ObservePage(DataPage):
    def __init__(self, window):
        super().__init__(window,'观察 · 自选')
        bar = QHBoxLayout(); self.groups = QComboBox(); self.groups.addItem('本地自选 · 此 Mac',None); bar.addWidget(self.groups)
        groups = QPushButton('账号自选分组'); groups.clicked.connect(self.load_groups); bar.addWidget(groups)
        refresh = QPushButton('刷新行情'); refresh.clicked.connect(self.load_group); bar.addWidget(refresh)
        self.search = QLineEdit(); self.search.setPlaceholderText('搜索代码 / 名称'); self.search.textChanged.connect(self.render); bar.addWidget(self.search,1)
        self.market = QComboBox(); self.market.addItems(['全部','美股','港股','沪深']); self.market.currentIndexChanged.connect(self.render); bar.addWidget(self.market)
        self.layout.addLayout(bar)
        self.table = make_table(SNAPSHOT_COLUMNS); self.table.cellDoubleClicked.connect(lambda row,col:self.open_row(self.table,row)); self.layout.addWidget(self.table,1)
        footer = QHBoxLayout(); self.previous = QPushButton('上一页'); self.next = QPushButton('下一页')
        self.previous.clicked.connect(lambda:self.move_page(-1)); self.next.clicked.connect(lambda:self.move_page(1))
        footer.addWidget(self.previous); footer.addWidget(self.next); footer.addWidget(self.status,1); self.layout.addLayout(footer)
        self.controls = [self.groups,groups,refresh,self.previous,self.next]
        self.group_rows = []; self.page = 0; self.groups.currentIndexChanged.connect(self.load_group)
        if self.ready(): self.load_groups()

    def clear_data(self):
        self.rows = []; self.table.setRowCount(0)

    def render(self,*_):
        query = self.search.text().strip().lower(); market = self.market.currentText()
        prefixes = {'美股':('US.',),'港股':('HK.',),'沪深':('SH.','SZ.')}.get(market,('',))
        fill(self.table,[row for row in self.rows if str(row.get('code','')).startswith(prefixes) and query in (str(row.get('code',''))+' '+str(row.get('name',''))).lower()],SNAPSHOT_COLUMNS)

    def load_groups(self):
        if self.ready(): self.send('watchlist_groups')

    def load_group(self,*_):
        self.page = 0; self.clear_data(); self.group_rows = []
        if not self.ready(): return
        if self.groups.currentData() is None:
            self.group_rows = [dict(code=code,name=self.window.state.names.get(code,NAMES.get(code,''))) for code in self.window.state.symbols]; self.load_snapshots()
        else: self.send('watchlist',group=self.groups.currentData())

    def move_page(self,delta):
        candidate = self.page + delta
        if candidate >= 0 and candidate*200 < len(self.group_rows): self.page = candidate; self.load_snapshots()

    def load_snapshots(self):
        self.clear_data(); codes = [row['code'] for row in self.group_rows[self.page*200:(self.page+1)*200]]
        if codes: self.send('market_snapshots',codes=codes)
        else: self.status.setText('此分组暂无标的')

    def result(self,data):
        if data['op'] == 'watchlist_groups':
            self.groups.blockSignals(True); self.groups.clear(); self.groups.addItem('本地自选 · 此 Mac',None)
            for row in data['rows']: self.groups.addItem(row['group_name']+' · 云端',row['group_name'])
            if self.groups.count()>1: self.groups.setCurrentIndex(1)
            self.groups.blockSignals(False); self.load_group()
        elif data['op'] == 'watchlist':
            self.group_rows = data['rows']; self.load_snapshots()
        else:
            names = {row['code']:row.get('name','') for row in self.group_rows}
            returned = {row['code']:row for row in data['rows']}
            failures = {code:failure['error'] for failure in data.get('errors',[]) for code in failure['codes']}
            view = []
            for stock in self.group_rows[self.page*200:(self.page+1)*200]:
                code = stock['code']; row = dict(returned.get(code,dict(code=code)))
                row['name'] = row.get('name') or names.get(code,'')
                row['quote_status'] = failures.get(code,'快照' if code in returned else '暂无行情')
                view.append(row)
            self.rows = snapshot_rows(view); self.render()
            source = 'moomoo 云端分组（只读）' if self.groups.currentData() is not None else '本地自选（仅此 Mac）'
            self.status.setText(f'{source} · 共 {len(self.group_rows)} 个标的 · 第 {self.page+1} 页 · 快照，点击刷新更新；双击打开图表')


OPTION_COLUMNS = [('code','合约代码'),('name','名称'),('strike_price','行权价'),('strike_time','到期日'),('lot_size','合约乘数')]
OPTION_QUOTE = [('last_price','最新价'),('bid_price','买价'),('ask_price','卖价'),('volume','成交量'),
    ('option_open_interest','未平仓量'),('option_implied_volatility','隐含波动率 %'),('option_delta','Delta'),
    ('option_gamma','Gamma'),('option_theta','Theta'),('option_vega','Vega'),('update_time','更新时间')]


class OptionsPage(DataPage):
    def __init__(self, window):
        super().__init__(window,'期权')
        ranges = QPushButton('按日期范围查询 · 未来三个月 / 导出')
        ranges.clicked.connect(lambda: window.show_option_range(self.underlying.text()))
        self.layout.addWidget(ranges)
        bar = QHBoxLayout(); self.underlying = QLineEdit(display_symbol(window.selected)); self.underlying.setPlaceholderText('PLTR / AAPL / HK.00700'); bar.addWidget(self.underlying)
        dates = QPushButton('获取到期日'); dates.clicked.connect(self.load_dates); bar.addWidget(dates)
        self.dates = QComboBox(); bar.addWidget(self.dates)
        chain = QPushButton('查询期权链'); chain.clicked.connect(self.load_chain); bar.addWidget(chain)
        quote = QPushButton('查询选中合约报价'); quote.clicked.connect(self.load_quote); bar.addWidget(quote); self.layout.addLayout(bar)
        self.search = QLineEdit(); self.search.setPlaceholderText('筛选行权价 / 合约'); self.search.textChanged.connect(self.render); self.layout.addWidget(self.search)
        split = QSplitter(); self.tables = {}
        for key,label in [('CALL','看涨 Call'),('PUT','看跌 Put')]:
            box = QWidget(); layout = QVBoxLayout(box); layout.addWidget(QLabel(label)); table = make_table(OPTION_COLUMNS)
            table.cellDoubleClicked.connect(lambda row,col,t=table:self.load_quote(t,row))
            table.itemSelectionChanged.connect(lambda t=table:self.choose_table(t)); layout.addWidget(table,1); split.addWidget(box); self.tables[key] = table
        self.layout.addWidget(split,1); self.active_table = self.tables['CALL']
        self.quote_table = make_table([('field','报价项目'),('value','数值')]); self.quote_table.setMaximumHeight(250); self.layout.addWidget(self.quote_table)
        self.layout.addWidget(self.status); self.controls = [self.underlying,dates,self.dates,chain,quote]
        self.underlying.textChanged.connect(self.invalidate_underlying); self.dates.currentIndexChanged.connect(self.clear_data)
        self.load_dates()

    def choose_table(self,table):
        if table.selectedItems(): self.active_table = table

    def clear_data(self,*_):
        self.rows = []
        for table in self.tables.values(): table.setRowCount(0)
        self.quote_table.setRowCount(0)

    def invalidate_underlying(self,*_):
        self.request = ''; self.dates.clear(); self.clear_data()

    def load_dates(self):
        self.dates.clear(); self.clear_data()
        if not self.ready(): return
        try:
            code = symbol(self.underlying.text())
            if not code.startswith(('US.','HK.')): raise ValueError('期权页目前支持美股和港股标的')
        except ValueError as error: self.status.setText(str(error)); return
        self.send('option_dates',code=code)

    def load_chain(self):
        self.clear_data()
        if self.ready() and self.dates.currentText(): self.send('option_chain',code=symbol(self.underlying.text()),date=self.dates.currentText())

    def render(self,*_):
        query = self.search.text().strip().lower()
        for kind,table in self.tables.items(): fill(table,[row for row in self.rows if row.get('option_type') == kind and query in (str(row.get('code',''))+' '+str(row.get('strike_price',''))).lower()],OPTION_COLUMNS)

    def load_quote(self,table=None,row=None):
        if not self.ready(): return
        table = table if isinstance(table,QTableWidget) else self.active_table
        row = table.currentRow() if row is None else row
        if row < 0: self.status.setText('先选择一个合约'); return
        code = table.item(row,0).data(Qt.ItemDataRole.UserRole)
        self.quote_table.setRowCount(0); self.send('snapshots',codes=[code]); self.status.setText('读取合约 '+display_symbol(code)+' 报价…')

    def result(self,data):
        if data['op'] == 'option_dates':
            self.dates.addItems(sorted({row['strike_time'] for row in data['rows']}))
            if self.dates.count(): self.load_chain()
            else: self.status.setText('此标的没有返回到期日，请检查标的和权限')
        elif data['op'] == 'option_chain':
            self.rows = data['rows']; self.render(); self.status.setText(f'{len(self.rows)} 个合约 · 双击合约查询报价与 Greeks；报价实时性取决于权限')
        else:
            row = data['rows'][0] if data['rows'] else {}
            if not row: self.status.setText('未返回合约报价'); return
            fill(self.quote_table,[dict(field=label,value=row.get(key)) for key,label in OPTION_QUOTE],[('field','报价项目'),('value','数值')])
            self.status.setText('合约 '+display_symbol(row.get('code',''))+' · '+str(row.get('update_time','—'))+' · 快照，点击查询更新')


MARKETS = {
    '美股': [('US.DIA','道琼斯 ETF'),('US.QQQ','纳斯达克 100 ETF'),('US.SPY','标普 500 ETF')],
    '港股': [('HK.800000','恒生指数')],
    '沪深': [('SH.000001','上证指数'),('SZ.399001','深证成指'),('SZ.399006','创业板指')]
}


class MarketMap(QWidget):
    """Decorative dotted world outline; markers contain only returned index quotes."""
    def __init__(self):
        super().__init__(); self.rows = []; self.setMinimumHeight(290)

    def paintEvent(self,event):
        painter = QPainter(self); painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        bounds = QRectF(5,5,self.width()-10,self.height()-10)
        gradient = QLinearGradient(0,0,0,self.height()); gradient.setColorAt(0,QColor('#222d3b')); gradient.setColorAt(1,QColor('#11161c'))
        painter.setPen(QPen(QColor('#334150'),1)); painter.setBrush(gradient); painter.drawRoundedRect(bounds,18,18)
        def point(lon,lat): return QPointF(20+(lon+180)/360*(self.width()-40),25+(85-lat)/155*(self.height()-50))
        outlines = [
            [(-168,68),(-140,72),(-120,60),(-100,55),(-65,52),(-52,45),(-80,25),(-98,15),(-110,29),(-128,48)],
            [(-81,12),(-65,10),(-47,-5),(-35,-10),(-48,-27),(-68,-55),(-76,-32)],
            [(-17,35),(10,37),(35,30),(50,12),(40,-15),(20,-35),(10,-20),(-5,5)],
            [(-10,36),(-9,60),(30,70),(70,73),(110,68),(160,60),(180,50),(135,35),(120,5),(100,0),(80,20),(55,25),(40,42),(10,40)],
            [(112,-12),(140,-10),(154,-26),(135,-40),(113,-30)],
            [(-52,60),(-20,65),(-30,82),(-55,80)]]
        for outline in outlines:
            path = QPainterPath(); path.moveTo(point(*outline[0]))
            for coordinates in outline[1:]: path.lineTo(point(*coordinates))
            path.closeSubpath()
            for x in range(20,self.width()-20,7):
                for y in range(25,self.height()-25,7):
                    if path.contains(QPointF(x,y)):
                        painter.setPen(Qt.PenStyle.NoPen); painter.setBrush(QColor('#344252')); painter.drawEllipse(QPointF(x,y),1.7,1.7)
        markers = {'US.DIA':(-120,35,-65,-24),'US.QQQ':(-100,40,8,-20),'US.SPY':(-95,25,8,18),
                   'HK.800000':(114,22,-80,30),'SH.000001':(121,31,8,-16),'SZ.399001':(114,24,-90,-20),'SZ.399006':(116,20,12,30)}
        for row in self.rows:
            code = row.get('code'); position = markers.get(code)
            if position is None: continue
            lon,lat,dx,dy = position; p = point(lon,lat); change = row.get('change_pct'); color = QColor('#939caa' if change is None else '#f04458' if change>0 else '#00b879' if change<0 else '#939caa')
            painter.setPen(Qt.PenStyle.NoPen); painter.setBrush(color); painter.drawEllipse(p,3,3)
            painter.setPen(QColor('#dce0e9')); painter.drawText(QPointF(p.x()+dx,p.y()+dy),row.get('name',code))
            painter.setPen(color); painter.drawText(QPointF(p.x()+dx,p.y()+dy+15),display(change)+'%')
        painter.setPen(QColor('#939caa')); painter.drawText(QPointF(18,self.height()-12),'市场总览 · 美股以 ETF 展示；未返回的市场不显示报价')


class MarketPage(DataPage):
    def __init__(self,window):
        super().__init__(window,'市场')
        bar = QHBoxLayout(); bar.addWidget(QLabel('关注市场：')); self.market_checks = {}
        saved = window.settings.value('selected_markets',['美股'])
        if isinstance(saved,str): saved = [saved]
        for name in MARKETS:
            check = QCheckBox(name); check.setChecked(name in saved); self.market_checks[name] = check; bar.addWidget(check)
        refresh = QPushButton('刷新市场快照'); refresh.clicked.connect(self.load); bar.addWidget(refresh); bar.addStretch(); self.layout.addLayout(bar)
        overview = QSplitter(); self.map = MarketMap(); overview.addWidget(self.map)
        self.cards_widget = QWidget(); self.cards = QGridLayout(self.cards_widget); overview.addWidget(self.cards_widget); overview.setSizes([850,400]); self.layout.addWidget(overview,2)
        self.table = make_table(SNAPSHOT_COLUMNS); self.table.cellDoubleClicked.connect(lambda row,col:self.open_row(self.table,row)); self.layout.addWidget(self.table,1)
        self.layout.addWidget(self.status); self.controls = [*self.market_checks.values(),refresh]
        for check in self.market_checks.values(): check.toggled.connect(self.selection_changed)
        self.load()

    def selected_symbols(self):
        return [stock for name,stocks in MARKETS.items() if self.market_checks[name].isChecked() for stock in stocks]

    def selection_changed(self,*_):
        self.window.settings.setValue('selected_markets',[name for name,check in self.market_checks.items() if check.isChecked()])
        self.load()

    def clear_data(self):
        self.rows = []; self.table.setRowCount(0); self.map.rows = []; self.map.update()
        while self.cards.count():
            item = self.cards.takeAt(0)
            if item.widget(): item.widget().deleteLater()

    def load(self,*_):
        self.request = ''; self.clear_data()
        stocks = self.selected_symbols()
        if not stocks:
            self.busy = False
            for control in self.controls: control.setEnabled(True)
            self.status.setText('请选择至少一个市场'); return
        if self.ready(): self.send('market_snapshots',codes=[code for code,name in stocks])

    def result(self,data):
        self.clear_data(); names = dict(self.selected_symbols()); self.rows = snapshot_rows([dict(row,name=names[row['code']],quote_status='快照') for row in data['rows'] if row['code'] in names])
        fill(self.table,self.rows,SNAPSHOT_COLUMNS); self.map.rows = self.rows; self.map.update()
        failures = {code:failure['error'] for failure in data.get('errors',[]) for code in failure['codes']}
        available = {row['code']:row for row in self.rows}
        for index,(code,name) in enumerate(self.selected_symbols()):
            row = available.get(code,dict(code=code,name=name))
            card = QWidget(); card.setStyleSheet('QWidget { border:1px solid #28313d; border-radius:5px; } QLabel { border:0; }'); box = QVBoxLayout(card)
            box.addWidget(QLabel(row['name'])); price = QLabel(display(row.get('last_price'))+'   '+display(row.get('change_pct'))+'%')
            change = row.get('change_pct',0); price.setStyleSheet('font-size:20px;color:'+('#f04458' if change > 0 else '#00b879' if change < 0 else '#939caa')+';border:0;'); box.addWidget(price)
            note = QLabel('暂无权限或数据' if code in failures else str(row.get('update_time','—')))
            if code in failures: note.setToolTip(failures[code]); card.setToolTip(failures[code])
            box.addWidget(note); self.cards.addWidget(card,index//2,index%2)
        details = '；'.join(failure['market']+': '+failure['error'] for failure in data.get('errors',[]))
        self.status.setText(f'已显示 {len(self.rows)} 个标的 · '+(details if details else '市场快照 · 双击标的打开图表'))
