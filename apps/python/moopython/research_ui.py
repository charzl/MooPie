"""Small cross-platform desktop: one symbol, Put ranking and trend evidence."""
import html
import json
from pathlib import Path
import sys
import tempfile

from PySide6.QtCore import QProcess, QProcessEnvironment, QSettings, QTimer, Qt
from PySide6.QtGui import QFontDatabase, QAction
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QTextBrowser, QSpinBox, QFileDialog, QMessageBox,
    QDialog, QComboBox, QTabWidget, QFrame, QToolButton, QMenu)

from .market_collection import us_symbols
from .runtime import OpenDRuntime
from .research_explanation import explanation_html, sort_description, score_breakdown_html
from .research import load_rules
from .research_controls import FilterDialog
from .research_table import CandidateTable
from .watchlist_store import WatchlistStore
from .symbol_search import SymbolSuggestions
from .watchlist_dialog import WatchlistDialog

STYLE = '''
QWidget {background:#101116;color:#e4e7ef;font-size:13px;font-family:"Noto Sans SC";}
QLabel#eyebrow {color:#8c9ab3;font-size:11px;font-weight:bold;}
QLabel#title {font-size:27px;font-weight:bold;}
QLabel#muted {color:#949bad;font-size:12px;}
QLineEdit,QSpinBox,QDoubleSpinBox,QComboBox {background:#1b1f28;border:1px solid #303542;border-radius:8px;padding:9px;}
QListWidget#symbolSuggestions {background:#191c24;color:#e4e7ef;border:1px solid #465576;border-radius:8px;}
QListWidget#symbolSuggestions::item {padding:7px 12px;}
QListWidget#symbolSuggestions::item:selected {background:#303b55;}
QComboBox QAbstractItemView {background:#1b1f28;color:#e4e7ef;selection-background-color:#303b55;}
QTabWidget::pane {border:0;}
QTabBar::tab {background:#101116;color:#949bad;padding:12px 22px;border-bottom:2px solid transparent;}
QTabBar::tab:selected {color:#e4e7ef;border-bottom:2px solid #8b9bff;}
QTabBar::tab:hover {color:#e4e7ef;}
QPushButton,QToolButton {background:#1b1f28;border:1px solid #303542;border-radius:10px;padding:10px 18px;font-weight:bold;}
QPushButton:hover,QToolButton:hover {background:#293142;}
QPushButton#primary {background:#e8ebf3;color:#141820;border:0;}
QPushButton#primary:hover {background:#cfd9ef;}
QPushButton:disabled,QToolButton:disabled {background:#1b1f28;color:#626c80;}
QMenu {background:#1b1f28;border:1px solid #303542;padding:6px;}
QMenu::item {padding:9px 18px;border-radius:5px;}
QMenu::item:selected {background:#303b55;}
QMenu::item:disabled {color:#626c80;}
QMenu::separator {height:1px;background:#303542;margin:5px 8px;}
QTextBrowser {background:#191c24;border:1px solid #2c313c;border-radius:12px;padding:18px;font-size:14px;}
QFrame#rankingCard {background:#191c24;border:1px solid #2c313c;border-radius:14px;}
QFrame#rankingCard QLabel {background:transparent;}
QLabel#cardTitle {font-size:17px;font-weight:bold;}
QLabel#badge {color:#e9b45f;background:#352b1d;border:1px solid #654b25;border-radius:12px;padding:5px 12px;font-size:11px;}
QLabel#dataState {color:#8da89d;font-size:12px;}
QTableWidget {background:#191c24;border:0;outline:0;selection-background-color:#252e42;selection-color:#e4e7ef;}
QTableWidget::item {border-bottom:1px solid #2b303a;padding:9px 8px;}
QTableWidget::item:selected {background:#252e42;}
QTableWidget::item:hover {background:#202632;}
QHeaderView {background:#171a21;}
QHeaderView::section {background:#171a21;color:#929bad;border:0;border-top:1px solid #2c313c;border-bottom:1px solid #2c313c;padding:12px 8px;text-align:left;font-size:11px;}
QTableCornerButton::section {background:#171a21;border:0;}
QScrollBar:vertical {background:#191c24;width:8px;}
QScrollBar:horizontal {background:#191c24;height:8px;}
QScrollBar::handle {background:#3d4556;border-radius:4px;min-height:24px;min-width:24px;}
QScrollBar::add-line,QScrollBar::sub-line {width:0;height:0;}
'''

def esc(value):
    return html.escape(str(value))


def trend_html(result):
    trend = result['trend']; outlook = trend['outlook']
    content = f'<h3>{esc(outlook["heading"])}</h3><p>{esc(outlook["horizon"])}</p>'
    content += '<ul>' + ''.join(f'<li>{esc(r)}</li>' for r in outlook['reasons']) + '</ul>'
    content += '<h3>关键价位</h3>' + ''.join(f'<p>{esc(r["label"])}：<b>{r["value"]:.2f}</b></p>' for r in outlook['levels'])
    content += f'<h3>什么会改变判断</h3><p>{esc(outlook["change_condition"])}</p><p>日线截至 {esc(trend["as_of"])} · 纽约交易日</p><p>{esc(outlook["limitation"])}</p>'
    content += '<p>采集时间：' + esc(result['collected_at']) + '</p>'
    return content


class ResearchWindow(QMainWindow):
    def __init__(self, settings=None, port=11111, auto_load=False):
        super().__init__()
        font_path = Path(__file__).with_name('fonts') / 'NotoSansSC.ttf'
        if QFontDatabase.addApplicationFont(str(font_path)) < 0:
            raise RuntimeError('Bundled Chinese font is missing or unreadable; reinstall the desktop package.')
        self.setWindowTitle('MooPie · 股票研究')
        self.resize(1480, 940)
        self.setMinimumSize(900, 660)
        self.settings = settings or QSettings('MooClients', 'Research')
        self.process = None
        self.results = {}
        self.put_dataset = None
        self.watchlist = WatchlistStore()
        try:
            saved_config = self.settings.value('put_recommendation_configuration_v1', '')
            self.configuration = load_rules().recommendation_configuration(json.loads(saved_config) if saved_config else None)
        except (ValueError, TypeError): self.configuration = load_rules().recommendation_configuration()
        self.output = bytearray()
        self.errors = bytearray()
        self.action = None
        self.cancelled = False
        self.workspace = tempfile.TemporaryDirectory(prefix='moomoo-research-')
        self.result_path = Path(self.workspace.name) / 'result.json'
        self.runtime = OpenDRuntime(self)
        self.runtime.status.connect(lambda text: self.status.setText(text))
        root = QWidget()
        layout = QVBoxLayout(root)
        layout.setContentsMargins(28, 22, 28, 18)
        layout.setSpacing(12)
        eyebrow = QLabel('MOOPIE   /   STOCK RESEARCH'); eyebrow.setObjectName('eyebrow')
        layout.addWidget(eyebrow)
        title = QLabel('找到值得研究的下一张 Put。'); title.setObjectName('title'); layout.addWidget(title)
        subtitle = QLabel('先明确风险边界，再按收益、风险、到期时长或担保成本比较。')
        subtitle.setObjectName('muted'); layout.addWidget(subtitle)
        controls = QHBoxLayout()
        self.symbol = QLineEdit()
        self.symbol.setPlaceholderText('输入代码 / 公司名 / 别名，支持 * 和 ?；留空查看 Watchlist')
        self.symbol.setMinimumWidth(220)
        self.symbol.returnPressed.connect(lambda: self.start('put'))
        controls.addWidget(self.symbol, 1)
        self.put_button = QPushButton('筛选卖出 Put'); self.put_button.setObjectName('primary')
        self.trend_button = QPushButton('分析走势')
        self.put_button.clicked.connect(lambda: self.start('put'))
        self.trend_button.clicked.connect(lambda: self.start('trend'))
        controls.addWidget(self.put_button); controls.addWidget(self.trend_button)
        self.refresh_button = QToolButton()
        self.refresh_button.setText('更新行情')
        self.refresh_button.setPopupMode(QToolButton.ToolButtonPopupMode.MenuButtonPopup)
        self.refresh_button.setToolTip('增量更新：复用有效缓存，只抓缺失或过期股票。盘中缓存60秒；右侧菜单可强制刷新全部。')
        self.refresh_button.clicked.connect(lambda: self.start('trend' if self.tabs.currentIndex() == 2 else 'put', update=True))
        refresh_menu = QMenu(self.refresh_button)
        self.force_refresh_action = QAction('强制刷新全部', refresh_menu)
        self.force_refresh_action.triggered.connect(lambda: self.start('trend' if self.tabs.currentIndex() == 2 else 'put', refresh=True))
        refresh_menu.addAction(self.force_refresh_action)
        self.refresh_button.setMenu(refresh_menu)
        controls.addWidget(self.refresh_button)
        self.opend_button = QPushButton('启动 OpenD')
        self.opend_button.clicked.connect(lambda: self.runtime.run('launch'))
        controls.addWidget(self.opend_button)
        layout.addLayout(controls)
        self.symbol_search = SymbolSuggestions(self.symbol, self)
        layout.addWidget(self.symbol_search.view)
        settings_row = QHBoxLayout()
        hint = QLabel('美股 · 未来三个月期权 · 现金担保 Put'); hint.setObjectName('muted')
        settings_row.addWidget(hint); settings_row.addStretch()
        self.ranking_mode = QComboBox()
        for label, key in [('收益优先', 'return'), ('低风险优先', 'risk'), ('到期时长：短到长', 'duration'),
                           ('担保成本：低到高', 'cost'), ('收益 / 风险综合', 'balanced'), ('表头排序', 'custom')]:
            self.ranking_mode.addItem(label, key)
        self.ranking_mode.model().item(self.ranking_mode.findData('custom')).setEnabled(False)
        self.sync_ranking_mode()
        self.ranking_mode.currentIndexChanged.connect(self.change_ranking_mode)
        settings_row.addWidget(self.ranking_mode)
        settings_row.addWidget(QLabel('Top'))
        self.top_count = QComboBox()
        for count in (5, 10, 20): self.top_count.addItem(str(count), count)
        try: saved_count = int(self.settings.value('put_top_n', 10))
        except (ValueError, TypeError): saved_count = 10
        self.top_count.setCurrentIndex(self.top_count.findData(saved_count if saved_count in (5, 10, 20) else 10))
        self.top_count.currentIndexChanged.connect(self.change_top_count)
        settings_row.addWidget(self.top_count)
        self.rules_button = QPushButton('Filter / 评分设置')
        self.rules_button.clicked.connect(self.show_rules)
        settings_row.addWidget(self.rules_button)
        settings_row.addWidget(QLabel('OpenD 端口'))
        self.port = QSpinBox(); self.port.setRange(1, 65535); self.port.setValue(port)
        self.port.valueChanged.connect(self.reset_panels)
        settings_row.addWidget(self.port)
        layout.addLayout(settings_row)
        self.tabs = QTabWidget()
        self.ranking_card = QFrame(); self.ranking_card.setObjectName('rankingCard')
        card = QVBoxLayout(self.ranking_card); card.setContentsMargins(0, 16, 0, 12); card.setSpacing(10)
        card_header = QHBoxLayout(); card_header.setContentsMargins(20, 0, 20, 0)
        self.ranking_title = QLabel('候选排行榜 · Top 10'); self.ranking_title.setObjectName('cardTitle')
        card_header.addWidget(self.ranking_title)
        badge = QLabel('现金担保 PUT'); badge.setObjectName('badge'); card_header.addWidget(badge)
        card_header.addStretch()
        self.data_state = QLabel('等待查询'); self.data_state.setObjectName('dataState'); card_header.addWidget(self.data_state)
        self.watchlist_button = QToolButton()
        self.watchlist_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.watchlist_menu = QMenu(self.watchlist_button)
        self.view_watchlist_action = self.watchlist_menu.addAction('查看 Watchlist')
        self.view_watchlist_action.triggered.connect(self.search_watchlist)
        self.add_watchlist_action = self.watchlist_menu.addAction('加入 Watchlist')
        self.add_watchlist_action.setToolTip('将输入的股票加入名单；只核验证券资料，不抓取期权行情。')
        self.add_watchlist_action.triggered.connect(lambda: self.start('add'))
        self.manage_watchlist_action = self.watchlist_menu.addAction('管理 Watchlist')
        self.manage_watchlist_action.triggered.connect(self.manage_watchlist)
        self.watchlist_menu.addSeparator()
        self.directory_action = self.watchlist_menu.addAction('更新股票目录')
        self.directory_action.setToolTip('连接 OpenD 同步美股和 ETF 的代码、公司名；不抓取报价。')
        self.directory_action.triggered.connect(lambda: self.start('sync-directory'))
        self.watchlist_menu.setToolTipsVisible(True)
        self.watchlist_button.setMenu(self.watchlist_menu)
        self.update_watchlist_label()
        card_header.addWidget(self.watchlist_button)
        card.addLayout(card_header)
        self.ranking_summary = QLabel(); self.ranking_summary.setObjectName('muted')
        self.ranking_summary.setContentsMargins(20, 0, 20, 0); self.ranking_summary.setWordWrap(True)
        card.addWidget(self.ranking_summary)
        self.candidate_table = CandidateTable()
        self.candidate_table.itemSelectionChanged.connect(self.select_candidate)
        self.candidate_table.cellDoubleClicked.connect(lambda _row, _column: self.tabs.setCurrentIndex(1))
        self.candidate_table.sort_requested.connect(self.sort_candidates)
        card.addWidget(self.candidate_table, 1)
        self.ranking_message = QLabel(); self.ranking_message.setWordWrap(True)
        self.ranking_message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.ranking_message.setObjectName('muted'); self.ranking_message.setContentsMargins(20, 12, 20, 12)
        card.addWidget(self.ranking_message)
        list_footer = QHBoxLayout(); list_footer.setContentsMargins(20, 0, 20, 0)
        self.selection_hint = QLabel('点击选中合约，双击查看评分与筛选依据。'); self.selection_hint.setObjectName('muted')
        self.selection_hint.setWordWrap(True); list_footer.addWidget(self.selection_hint, 1)
        self.details_button = QPushButton('查看所选合约 →'); self.details_button.setEnabled(False)
        self.details_button.clicked.connect(lambda: self.tabs.setCurrentIndex(1)); list_footer.addWidget(self.details_button)
        card.addLayout(list_footer)
        note = QLabel('收益按 Bid 与全额现金担保计算，未扣费用。蓝色条表示综合分；财报未验证或事件风险以琥珀色标注。')
        note.setObjectName('muted'); note.setWordWrap(True); note.setContentsMargins(20, 0, 20, 0); card.addWidget(note)
        self.put_result = QTextBrowser(); self.trend_result = QTextBrowser()
        for panel in (self.put_result, self.trend_result):
            panel.setOpenExternalLinks(False)
        self.tabs.addTab(self.ranking_card, '候选列表')
        self.tabs.addTab(self.put_result, '合约详情 / 筛选依据')
        self.tabs.addTab(self.trend_result, '走势分析')
        layout.addWidget(self.tabs, 1)
        self.reset_panels()
        self.symbol.textChanged.connect(self.reset_panels)
        footer = QHBoxLayout()
        self.status = QLabel('盘中读取 OpenD 并保存，盘后读取本地数据库。首次无数据时请登录 OpenD 并点击「更新行情」。'); self.status.setObjectName('muted')
        self.status.setWordWrap(True); footer.addWidget(self.status, 1)
        self.cancel_button = QPushButton('取消'); self.cancel_button.hide()
        self.cancel_button.clicked.connect(self.cancel); footer.addWidget(self.cancel_button)
        self.export_button = QPushButton('导出结果'); self.export_button.setEnabled(False)
        self.export_button.clicked.connect(self.export); footer.addWidget(self.export_button)
        layout.addLayout(footer)
        self.setCentralWidget(root); self.setStyleSheet(STYLE)
        if auto_load: QTimer.singleShot(0, lambda: self.start('put'))

    def update_watchlist_label(self):
        try:
            count = len(self.watchlist.symbols())
            self.watchlist_button.setText(f'Watchlist ({count})')
            self.view_watchlist_action.setText(f'查看 Watchlist ({count})')
        except (ValueError, OSError):
            self.watchlist_button.setText('Watchlist（需检查）')
            self.view_watchlist_action.setText('查看 Watchlist（需检查）')
        self.watchlist_button.setToolTip('查看、添加、管理 Watchlist，或更新股票目录。\nSQLite：' + str(self.watchlist.store.path))

    def search_watchlist(self):
        if self.process is not None: return
        action = 'trend' if self.tabs.currentIndex() == 2 else 'put'
        self.symbol.clear()
        self.update_watchlist_label()
        self.start(action)

    def manage_watchlist(self):
        if self.process is not None: return
        self.symbol_search.dismiss()
        try:
            dialog = WatchlistDialog(self.watchlist, self)
            if dialog.exec() != QDialog.DialogCode.Accepted: return
            self.update_watchlist_label()
            self.reset_panels()
            self.status.setText(f'Watchlist 已保存，删除 {dialog.removal_result["removed_count"]} 项。从菜单选择「查看 Watchlist」查看最新结果。')
        except (ValueError, RuntimeError, OSError) as error:
            self.status.setText('无法打开 Watchlist：' + str(error))

    def reset_panels(self):
        self.results.clear()
        self.put_dataset = None
        self.clear_candidates('输入代码搜索单股，或留空查看默认 Watchlist。')
        self.put_result.setHtml(f'<h2>卖出 Put · Top {self.top_count.currentData()}</h2><p>先按 Filter 过滤，再按到期时长、担保成本、收益、风险或综合得分排序。</p><p style="color:#9aaab7">点击表头切换排序方向；设置页调整 Filter 和评分参数。</p>')
        self.trend_result.setHtml('<h2>走势分析</h2><p>均线 · RSI · MACD · 成交量</p><p style="color:#9aaab7">显示趋势、关键价位和改判条件。数据来自已完成日线。</p>')
        if hasattr(self, 'export_button'): self.export_button.setEnabled(False)

    def clear_candidates(self, message):
        self.candidate_table.setRowCount(0)
        self.candidate_table.order = []
        self.ranking_title.setText(f'候选排行榜 · Top {self.top_count.currentData()}')
        self.ranking_summary.setText('先过滤完整合约，再排序并选取 Top 数量。')
        self.data_state.setText('等待查询')
        self.ranking_message.setText(message); self.ranking_message.show()
        self.selection_hint.setText('点击选中合约，双击查看评分与筛选依据。')
        self.details_button.setEnabled(False)

    def busy(self, value):
        if value: self.symbol_search.dismiss()
        for control in (self.symbol, self.port, self.put_button, self.trend_button, self.refresh_button, self.opend_button, self.watchlist_button, self.view_watchlist_action, self.add_watchlist_action, self.manage_watchlist_action, self.directory_action, self.rules_button, self.ranking_mode, self.top_count, self.candidate_table): control.setEnabled(not value)
        self.cancel_button.setVisible(value)

    def start(self, action, reuse=False, refresh=False, update=False):
        if self.process is not None: return
        text = self.symbol.text().strip()
        try:
            code = None if action == 'sync-directory' else self.symbol_search.query_code()
            if action == 'add' and code is None: raise ValueError('请先输入要加入 Watchlist 的股票代码。')
        except ValueError as error:
            self.status.setText(str(error)); return
        dataset = self.put_dataset if action == 'put' and reuse else None
        if reuse and dataset is None:
            self.status.setText('没有可复用的数据，请先抓取。'); return
        if action == 'put' and not reuse: self.put_dataset = None
        if code: self.settings.setValue('symbol', code.removeprefix('US.'))
        self.action = action
        self.cancelled = False
        self.results.pop(action, None)
        if action == 'put':
            self.clear_candidates('正在用已有数据重新过滤和排序…' if reuse else '正在按交易时段读取行情并筛选合约…')
        if action not in ('add', 'sync-directory'): self.tabs.setCurrentIndex(0 if action == 'put' else 2)
        self.export_button.setEnabled(bool(self.results))
        if action not in ('add', 'sync-directory'): self.panel(action).setHtml(f'<h2>{esc(code or "Watchlist")}</h2><p>正在抓取和分析…</p>')
        self.status.setText('正在用已采集的数据重新过滤和排序，不重新抓取行情。' if reuse else
                            '正在刷新 OpenD 并保存数据库…' if refresh else '正在判断交易时段；盘后读取 SQLite，盘中抓取并保存…')
        if action == 'add': self.status.setText('正在核验证券基本资料并加入 Watchlist…')
        if update: self.status.setText('正在逐股检查缓存，只补抓缺失或过期股票，再合并 Top 20…')
        if action == 'sync-directory': self.status.setText('正在更新股票和 ETF 目录；不抓取期权或股票报价…')
        self.output.clear(); self.errors.clear()
        self.result_path.unlink(missing_ok=True)
        process = QProcess(self); self.process = process
        environment = QProcessEnvironment.systemEnvironment()
        environment.insert('PYTHONUTF8', '1'); environment.insert('PYTHONUNBUFFERED', '1')
        process.setProcessEnvironment(environment)
        process.readyReadStandardOutput.connect(lambda: self.output.extend(bytes(process.readAllStandardOutput())))
        process.readyReadStandardError.connect(lambda: self.read_progress(process))
        process.finished.connect(self.finished)
        process.errorOccurred.connect(self.process_error)
        args = (['research'] if getattr(sys, 'frozen', False) else ['-X', 'utf8', '-m', 'moopython.research_cli'])
        extra = []
        if refresh: extra.append('--refresh')
        if update: extra.append('--update')
        if action == 'add': extra.append('--refresh')
        if action == 'put':
            config_path = Path(self.workspace.name) / 'configuration.json'
            config_path.write_text(json.dumps(self.configuration, allow_nan=False), encoding='utf-8')
            extra += ['--config', str(config_path), '--top', str(self.top_count.currentData())]
            if dataset is not None:
                dataset_path = Path(self.workspace.name) / 'dataset.json'
                dataset_path.write_text(json.dumps(dataset, allow_nan=False), encoding='utf-8')
                extra += ['--input', str(dataset_path)]
        self.busy(True)
        process.start(sys.executable, [*args, action, *([code] if code else []), '--port', str(self.port.value()), '--output', str(self.result_path), *extra])

    def panel(self, action):
        return self.put_result if action == 'put' else self.trend_result

    def read_progress(self, process):
        data = bytes(process.readAllStandardError())
        self.errors.extend(data)
        self.errors = self.errors[-8000:]
        lines = data.decode('utf-8', errors='replace').strip().splitlines()
        if lines: self.status.setText(lines[-1][-200:])

    def process_error(self, error):
        if error == QProcess.ProcessError.FailedToStart:
            message = self.process.errorString()
            self.show_error(message)
            self.release_process()

    def finished(self, exit_code, _status):
        process = self.process
        if process is None: return
        self.output.extend(bytes(process.readAllStandardOutput()))
        self.read_progress(process)
        if self.cancelled:
            if self.action in ('add', 'sync-directory'):
                self.update_watchlist_label()
                self.status.setText('已停止操作；以当前保存的 Watchlist / 股票目录为准。')
                self.release_process()
                return
            if self.action == 'put': self.clear_candidates('本次分析已取消，没有生成候选。')
            self.panel(self.action).setPlainText('本次分析已取消。可以重新输入股票并开始查询。')
            self.status.setText('已取消；没有生成本次分析结果。')
            self.release_process()
            return
        try:
            result = json.loads(self.result_path.read_text(encoding='utf-8')) if self.result_path.exists() else json.loads(self.output.decode('utf-8'))
            if exit_code or result.get('error'):
                raise ValueError(result.get('error', f'分析进程退出：{exit_code}'))
            if result.get('action') == 'directory_sync':
                skipped = len(result.get('skipped', []))
                self.status.setText(f'股票目录已更新：{result["securities"]} 条证券，{result["aliases"]} 个别名。'
                                    + (f'跳过 {skipped} 个格式不支持的代码。' if skipped else '')
                                    + '可输入公司名或代码选择。')
            elif result.get('action') == 'watchlist_add':
                self.update_watchlist_label()
                self.status.setText(result['symbol'] + (' 已加入 Watchlist。' if result['added'] else ' 已在 Watchlist 中，没有重复添加。'))
            else:
                self.display(result)
        except (ValueError, KeyError, TypeError) as error:
            detail = str(error) or self.errors.decode('utf-8', errors='replace')[-1500:]
            self.show_error(detail or f'分析进程退出：{exit_code}')
        self.release_process()

    def release_process(self):
        if self.process:
            self.process.deleteLater(); self.process = None
        self.busy(False)

    def show_error(self, message):
        if self.action in ('add', 'sync-directory'):
            self.status.setText(('股票目录更新失败，保留原目录：' if self.action == 'sync-directory' else '未加入 Watchlist：') + message)
            return
        self.results.pop(self.action, None)
        if self.action == 'put':
            self.clear_candidates('分析未完成。请到「合约详情 / 筛选依据」查看数据缺失或连接错误。')
            self.data_state.setText('本次查询失败')
        self.export_button.setEnabled(bool(self.results))
        self.panel(self.action).setPlainText('分析未完成\n\n' + message + '\n\n盘后缺少快照时，请登录 OpenD 并点击「更新行情」。连接失败时检查端口和行情权限。')
        self.status.setText('分析未完成；没有生成候选或走势结论。')

    def display(self, result):
        action = result['action']
        self.results[action] = result
        heading = f'<h2>{esc(result["symbol"])} · {"卖出 Put" if action == "put" else "走势"}</h2>'
        if action == 'trend':
            content = (''.join('<h2>' + esc(item['symbol']) + '</h2>' + trend_html(item) for item in result['items'])
                       if 'items' in result else trend_html(result))
            content += ''.join('<p>查询失败：' + esc(item['symbol']) + ' · ' + esc(item['error']) + '</p>' for item in result.get('collection_errors', []))
        else:
            report = result['report']; ranked = report['ranked']
            self.put_dataset = result.get('input_dataset')
            self.configuration = report.get('configuration', self.configuration)
            self.sync_ranking_mode()
            requested = report.get('top_n_requested', 10)
            if requested in (5, 10, 20):
                self.top_count.blockSignals(True)
                self.top_count.setCurrentIndex(self.top_count.findData(requested))
                self.top_count.blockSignals(False)
            shown = len(report.get('recommendations', []))
            self.ranking_title.setText(('Watchlist · ' if result.get('query_scope') == 'watchlist' else '候选排行榜 · ') + f'Top {requested}')
            self.ranking_summary.setText(f'检查 {report["total_contracts"]} 个合约 · {report["qualified_count"]} 个通过 Filter · 显示 {shown} 个\nSort：' + sort_description(report['sort_order']))
            access = result.get('data_access', {})
            source = {'database': 'SQLite', 'OpenD': 'OpenD', 'mixed': '混合来源'}.get(access.get('source'), '已保存数据')
            self.data_state.setText('● ' + source + ' · ' + report['session_date'])
            self.data_state.setToolTip('原始采集时间：' + result['collected_at'] + '\n' + access.get('note', '') + '\n离线重新排序不会刷新行情。')
            self.ranking_message.setVisible(not ranked)
            self.ranking_message.setText('没有符合当前 Filter 的 Put。请查看「合约详情 / 筛选依据」，再自行决定是否调整条件。')
            self.candidate_table.show_report(report)
            if not shown: self.select_candidate()
            self.tabs.setCurrentIndex(0)
        if action == 'trend':
            access = result.get('data_access', {})
            content += '<p>' + esc(access.get('note', '')) + ' · ' + esc(access.get('source', '已保存数据')) + '</p>'
            self.trend_result.setHtml(heading + content)
            self.tabs.setCurrentIndex(2)
        failures = result.get('collection_errors', [])
        access = result.get('data_access', {})
        reuse_note = (f' · 复用 {len(access["reused_symbols"])} 只，抓取 {len(access["fetched_symbols"])} 只'
                      if 'reused_symbols' in access else '')
        self.status.setText(('部分结果：' + '；'.join(item['symbol'] + ' 查询失败' for item in failures) if failures else '分析完成')
                            + reuse_note + ' · 数据采集：' + result['collected_at'] + ' · ' + access.get('note', '可导出数据、Filter、Sort 和规则证据'))
        self.export_button.setEnabled(True)

    def select_candidate(self):
        result = self.results.get('put')
        if not result: return
        report = result['report']
        index = self.candidate_table.currentRow()
        choices = report.get('recommendations', [])
        choice = choices[index] if 0 <= index < len(choices) else None
        self.details_button.setEnabled(choice is not None)
        content = f'<h2>{esc(result["symbol"])} · 合约详情</h2>'
        content += '<p>' + esc(result.get('data_access', {}).get('note', '')) + '</p>'
        content += ''.join('<p>查询失败：' + esc(item['symbol']) + ' · ' + esc(item['error']) + '</p>' for item in result.get('collection_errors', []))
        content += f'<p>检查 {report["total_contracts"]} 个合约，{report["qualified_count"]} 个通过当前 Filter。</p>'
        content += '<p>Sort：' + esc(sort_description(report['sort_order'])) + '</p>'
        if choice:
            row = next(r for r in report['ranked'] if r['code'] == choice['code'])
            m = row['metrics']
            self.selection_hint.setText(f'已选 #{choice["overall_rank"]}  ·  {row["code"]}  ·  双击查看依据')
            content += f'<h3>#{choice["overall_rank"]} · {esc(row["code"])}</h3><p>到期 {esc(row["expiration"])} · {m["days_to_expiry"]} 天</p>'
            fields = [('行权价', f'${m["strike"]:,.2f}'), ('参考 Bid / Ask', f'${m["bid"]:.2f} / ${m["ask"]:.2f}'),
                      ('每张权利金（费用前）', f'${m["premium_per_contract_before_costs"]:,.2f}'),
                      ('现金担保要求', f'${m["cash_collateral"]:,.2f}'),
                      ('日均毛收益率（完整保留权利金）', f'{m["daily_gross_return_pct"]:.4f}%'),
                      ('收益分 / 风险分 / 综合分', f'{m["return_score"]:.2f} / {m["risk_score"]:.2f} / {m["composite_score"]:.2f}'),
                      ('权利金 / 本金 · 简单年化', f'{m["gross_return_pct"]:.2f}% / {m["annualized_gross_return_pct"]:.2f}%'),
                      ('盈亏平衡价', f'${m["breakeven_before_costs"]:.2f}'),
                      ('价外幅度 / Delta', f'{m["otm_pct"]:.2f}% / {-m["abs_delta"]:.2f}'),
                      ('买卖价差 / 未平仓量', f'{m["spread_pct_of_mid"]:.2f}% / {m["open_interest"]:,.0f}'),
                      ('最大亏损（股价归零）', f'${m["max_loss_before_costs"]:,.2f}')]
            content += ''.join(f'<p>{label}：<b>{value}</b></p>' for label, value in fields)
            content += score_breakdown_html(choice, heading='所选合约的评分依据')
            for warning in row.get('warnings', []): content += '<p><b>需复核：' + esc(warning) + '</b></p>'
            content += f'<p>合约快照：{esc(row["snapshot_update_time"])} · 纽约时间</p>'
            if not row['live_review_ready']: content += '<p><b>仅供研究；交易前需核对上述风险并刷新报价。</b></p>'
            content += '<p>日均毛收益率假设完整保留权利金，不是实际每天到账的收益，股价下跌可产生亏损。</p>'
        else:
            content += '<h3>没有符合当前 Filter 的 Put</h3><p>可打开 Filter / 评分设置，自行关闭条件或调整阈值；程序不会自动放宽。</p>'
            unknown = len(report['earnings_unverified_watchlist'])
            if unknown: content += f'<p>{unknown} 个合约仅因财报日期尚未验证，保留在导出结果的观察名单中。</p>'
        missing = len(report['missing_quote_codes'])
        if missing: content += f'<p>另有 {missing} 个合约缺少报价，未参与排名。</p>'
        if report['calendar_errors']: content += '<p>财报日历读取不完整，已保留风险提示；启用财报 Filter 时会排除相关合约。</p>'
        content += explanation_html(report)
        content += f'<p>交易日 {esc(report["session_date"])} · 规则 {esc(report["ruleset_version"])}</p><p>按一张标准合约全额现金担保计算；未校验个人资金预算。收益不含费用、不保证成交，规则尚未经回测。</p>'
        self.put_result.setHtml(content)

    def sort_candidates(self, metric, direction):
        config = load_rules().recommendation_configuration(self.configuration)
        # Keep subsequent tie-breakers, removing the new primary if it was one.
        config['sort_order'] = ([[metric, direction]] + [entry for entry in config['sort_order'] if entry[0] != metric])[:3]
        self.apply_configuration(config)

    def show_rules(self):
        report = self.results.get('put', {}).get('report')
        dialog = FilterDialog(self.configuration, report, self.put_dataset is not None, self)
        if dialog.exec() != QDialog.DialogCode.Accepted: return
        self.apply_configuration(dialog.selected_configuration)

    def sync_ranking_mode(self):
        primary, direction = self.configuration['sort_order'][0]
        key = {('daily_gross_return_pct', 'desc'): 'return', ('risk_score', 'asc'): 'risk',
               ('days_to_expiry', 'asc'): 'duration', ('cash_collateral', 'asc'): 'cost',
               ('composite_score', 'desc'): 'balanced'}.get((primary, direction), 'custom')
        self.ranking_mode.blockSignals(True)
        self.ranking_mode.setCurrentIndex(self.ranking_mode.findData(key))
        self.ranking_mode.blockSignals(False)

    def change_ranking_mode(self, _index):
        key = self.ranking_mode.currentData()
        if key == 'custom': return
        config = load_rules().recommendation_configuration(self.configuration)
        config['sort_order'] = [list(item) for item in load_rules().RANKING_SORT_ORDERS[key]]
        self.apply_configuration(config)

    def change_top_count(self, _index):
        self.settings.setValue('put_top_n', self.top_count.currentData())
        self.apply_configuration(self.configuration)

    def apply_configuration(self, configuration):
        self.configuration = configuration
        self.sync_ranking_mode()
        self.settings.setValue('put_recommendation_configuration_v1', json.dumps(self.configuration))
        if self.put_dataset is not None: self.start('put', reuse=True)
        else:
            self.results.pop('put', None)
            self.clear_candidates('设置已保存。点击「筛选卖出 Put」抓取并分析。')
            self.put_result.setPlainText(f'研究设置已保存：Top {self.top_count.currentData()}。点击“筛选卖出 Put”抓取并分析。')
            self.export_button.setEnabled(bool(self.results))
            self.status.setText('设置已保存；尚未重新抓取行情。')

    def cancel(self):
        if self.process:
            self.cancelled = True
            self.process.kill()

    def export(self):
        path, _ = QFileDialog.getSaveFileName(self, '导出研究结果', 'moomoo-research.json', 'JSON (*.json)')
        if path:
            try: Path(path).write_text(json.dumps(self.results, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
            except OSError as error: QMessageBox.warning(self, '导出失败', str(error))

    def closeEvent(self, event):
        if self.process:
            self.process.kill(); self.process.waitForFinished(2000)
        self.workspace.cleanup()
        event.accept()


def main():
    import argparse
    from PySide6.QtWidgets import QApplication
    parser = argparse.ArgumentParser(description='MooPie stock research desktop')
    parser.add_argument('--port', type=int, default=11111)
    args = parser.parse_args()
    app = QApplication([sys.argv[0]])
    app.setApplicationName('MooPie')
    window = ResearchWindow(port=args.port, auto_load=True)
    window.show()
    return app.exec()
