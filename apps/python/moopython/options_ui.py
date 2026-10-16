"""Embedded option-chain page. SDK work stays on the gateway worker thread."""
from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (
    QAbstractItemView, QComboBox, QDateEdit, QFileDialog, QHBoxLayout, QHeaderView,
    QLabel, QLineEdit, QPushButton, QTableWidget, QTableWidgetItem,
)

from .account_ui import QueryDialog
from .market import display_symbol
from .options import OptionQuery, add_months, write_result


class OptionRangePage(QueryDialog):
    def __init__(self, window):
        super().__init__(window, '期权链')
        self.setWindowFlags(Qt.WindowType.Widget)
        self.layout.setContentsMargins(24, 20, 24, 16)
        self.result_data = None
        self.visible_rows = []
        heading = QHBoxLayout()
        title = QLabel('期权链 · 到期日与行权价')
        title.setStyleSheet('font-size:20px;font-weight:600;')
        heading.addWidget(title)
        heading.addStretch()
        back = QPushButton('单个到期日 / 合约报价')
        back.clicked.connect(lambda: window.show_data_page('期权'))
        heading.addWidget(back)
        self.layout.addLayout(heading)
        note = QLabel('输入股票或 ETF 代码，查询已挂牌期权。日期按标的市场时区，支持导出 CSV / JSON。')
        note.setWordWrap(True)
        note.setStyleSheet('color:#939caa;padding:8px 0;')
        self.layout.addWidget(note)

        filters = QHBoxLayout()
        filters.addWidget(QLabel('标的'))
        self.code = QLineEdit(display_symbol(window.selected))
        self.code.setPlaceholderText('AAPL / US.NVDA / HK.00700')
        self.code.setMinimumWidth(220)
        filters.addWidget(self.code, 1)
        filters.addWidget(QLabel('类型'))
        self.kind = QComboBox()
        for label, value in [('全部 Call + Put', 'ALL'), ('看涨 Call', 'CALL'), ('看跌 Put', 'PUT')]:
            self.kind.addItem(label, value)
        filters.addWidget(self.kind)
        self.read = QPushButton('查询期权链')
        self.read.setObjectName('connect')
        self.read.clicked.connect(self.load_chain)
        self.code.returnPressed.connect(self.load_chain)
        filters.addWidget(self.read)
        self.cancel = QPushButton('取消')
        self.cancel.setEnabled(False)
        self.cancel.clicked.connect(self.cancel_query)
        filters.addWidget(self.cancel)
        self.layout.addLayout(filters)

        dates = QHBoxLayout()
        dates.addWidget(QLabel('到期日范围'))
        self.start_date = QDateEdit()
        self.end_date = QDateEdit()
        initial = OptionQuery.upcoming(window.selected if window.selected.startswith(('US.', 'HK.')) else 'US.AAPL')
        for control, value in ((self.start_date, initial.start), (self.end_date, initial.end)):
            control.setCalendarPopup(True)
            control.setDisplayFormat('yyyy-MM-dd')
            control.setDate(QDate(value.year, value.month, value.day))
        dates.addWidget(self.start_date)
        dates.addWidget(QLabel('至'))
        dates.addWidget(self.end_date)
        self.months = QComboBox()
        for value in (1, 3, 6, 12, 24):
            self.months.addItem(f'{value} 个月', value)
        self.months.setCurrentIndex(1)
        self.months.currentIndexChanged.connect(self.update_end_date)
        self.start_date.dateChanged.connect(self.update_end_date)
        dates.addWidget(self.months)
        dates.addStretch()
        self.expiry = QComboBox()
        self.expiry.addItem('全部到期日', '')
        self.expiry.currentIndexChanged.connect(self.filter_rows)
        dates.addWidget(self.expiry)
        self.export = QPushButton('导出…')
        self.export.setEnabled(False)
        self.export.clicked.connect(self.export_result)
        dates.addWidget(self.export)
        self.layout.addLayout(dates)

        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(['到期日', '类型', '行权价', '合约代码', '名称', '每份合约股数', '标准类型'])
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet('QTableView { alternate-background-color:#1d2129; } QTableView::item:selected { background:#303a49; color:#dce0e9; }')
        self.table.setShowGrid(False)
        self.table.verticalHeader().hide()
        self.table.setSortingEnabled(True)
        self.table.sortItems(0, Qt.SortOrder.AscendingOrder)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.layout.addWidget(self.table, 1)
        self.layout.addWidget(self.status)
        self.controls = [self.code, self.kind, self.read, self.start_date, self.end_date, self.months]
        self.code.textChanged.connect(self.clear_data)
        self.kind.currentIndexChanged.connect(self.clear_data)
        self.start_date.dateChanged.connect(self.clear_data)
        self.end_date.dateChanged.connect(self.clear_data)
        self.status.setText('选择标的和时间范围，然后点击“查询期权链”。默认查询未来三个自然月。')

    def reject(self):
        self.window.show_data_page('期权')

    def update_end_date(self, *_):
        last = add_months(self.start_date.date().toPython(), self.months.currentData())
        self.end_date.setDate(QDate(last.year, last.month, last.day))

    def load_chain(self):
        if self.busy:
            return
        self.clear_data()
        try:
            query = OptionQuery.upcoming(
                self.code.text(), option_type=self.kind.currentData(),
                start=self.start_date.date().toString('yyyy-MM-dd'),
                end=self.end_date.date().toString('yyyy-MM-dd'))
        except ValueError as error:
            self.status.setText(str(error))
            return
        self.code.setText(display_symbol(query.code))
        self.send('options', code=query.code, start=query.start.isoformat(),
                  end=query.end.isoformat(), option_type=query.option_type)
        self.cancel.setEnabled(self.busy)

    def cancel_query(self):
        self.window.gateway.cancel_options(self.request)
        self.request = ''
        self.busy = False
        self.cancel.setEnabled(False)
        for control in self.controls:
            control.setEnabled(True)
        self.status.setText('查询已取消')

    def check_session(self):
        if self.window.token != self.session or self.window.mode != 'live':
            if self.request:
                self.window.gateway.cancel_options(self.request)
            self.cancel.setEnabled(False)
        super().check_session()

    def receive(self, token, kind, data):
        if token == self.session == self.window.token and kind == 'options_progress' and data.get('request') == self.request:
            self.status.setText(f'已完成 {data["completed"]}/{data["total"]} 个日期分段，正在读取 {data["start"]} 至 {data["end"]}…')
            return
        super().receive(token, kind, data)
        self.cancel.setEnabled(self.busy and self.window.token == self.session and self.window.mode == 'live')

    def clear_data(self, *_):
        self.request = ''
        self.result_data = None
        self.visible_rows = []
        self.table.setRowCount(0)
        self.export.setEnabled(False)
        self.expiry.blockSignals(True)
        self.expiry.clear()
        self.expiry.addItem('全部到期日', '')
        self.expiry.blockSignals(False)

    def result(self, data):
        self.result_data = {key: value for key, value in data.items() if key not in ('op', 'request')}
        self.expiry.blockSignals(True)
        self.expiry.clear()
        self.expiry.addItem('全部到期日', '')
        for expiry in data['expirations']:
            self.expiry.addItem(expiry, expiry)
        self.expiry.blockSignals(False)
        self.filter_rows()

    def filter_rows(self, *_):
        if self.result_data is None:
            return
        expiry = self.expiry.currentData()
        self.visible_rows = [row for row in self.result_data['contracts'] if not expiry or row['strike_time'] == expiry]
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(self.visible_rows))
        for index, row in enumerate(self.visible_rows):
            for column, key in enumerate(('strike_time', 'option_type', 'strike_price', 'code', 'name', 'lot_size', 'option_standard_type')):
                item = QTableWidgetItem()
                value = row.get(key)
                if key == 'code':
                    value = display_symbol(value)
                item.setData(Qt.ItemDataRole.DisplayRole, value if value is not None else '—')
                self.table.setItem(index, column, item)
        self.table.setSortingEnabled(True)
        self.export.setEnabled(bool(self.visible_rows))
        self.status.setText(f'{self.result_data["symbol"]} · {len(self.result_data["expirations"])} 个到期日 · 显示 {len(self.visible_rows)} / {len(self.result_data["contracts"])} 个合约 · 日期时区 {self.result_data["timezone"]}'
                            if self.result_data['contracts'] else '此标的在所选日期范围内没有返回期权合约。')

    def save_result(self, path, format):
        result = dict(self.result_data, contracts=self.visible_rows)
        if self.expiry.currentData():
            result['expirations'] = [self.expiry.currentData()]
        with open(path, 'w', encoding='utf-8', newline='') as stream:
            write_result(result, stream, format)

    def export_result(self):
        if not self.result_data or not self.visible_rows:
            return
        path, selected = QFileDialog.getSaveFileName(
            self, '导出当前显示的期权合约', f'{self.result_data["symbol"]}-options.csv', 'CSV (*.csv);;JSON (*.json)')
        if path:
            format = 'json' if selected.startswith('JSON') else 'csv'
            if not path.lower().endswith('.' + format):
                path += '.' + format
            try:
                self.save_result(path, format)
                self.status.setText(f'已导出 {len(self.visible_rows)} 个合约：{path}')
            except OSError as error:
                self.status.setText(f'导出失败：{error}')

    def cleanup(self):
        if self.request:
            self.window.gateway.cancel_options(self.request)
        super().cleanup()
