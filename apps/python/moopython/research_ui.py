"""Small cross-platform desktop: one symbol, Put ranking and trend evidence."""
import html
import json
from pathlib import Path
import sys
import tempfile

from PySide6.QtCore import QProcess, QProcessEnvironment, QSettings, QTimer, Qt, QSize
from PySide6.QtGui import QFontDatabase, QAction, QActionGroup, QColor, QPalette
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QTextBrowser, QSpinBox, QDoubleSpinBox, QFileDialog, QMessageBox,
    QDialog, QComboBox, QTabWidget, QFrame, QToolButton, QMenu, QListWidget,
    QListWidgetItem, QWidgetAction, QSplitter, QStackedWidget, QTableWidget,
    QTableWidgetItem, QAbstractItemView, QHeaderView, QStyledItemDelegate, QStyleOptionViewItem)

from .market_collection import us_symbols
from .runtime import OpenDRuntime
from .research_explanation import explanation_html, sort_description, score_breakdown_html
from .research import load_rules
from .research_controls import FilterDialog
from .research_table import CandidateTable
from .watchlist_store import WatchlistStore
from .symbol_search import SymbolSuggestions
from .watchlist_dialog import WatchlistDialog
from .price_signal_view import signals_html
from .buy_plan import calculate_plan
from .buy_alert_store import BuyAlertStore
from .security_directory import SecurityDirectory
from .order_book_chart import OrderBookChart
from .chart import CandleChart
from .market import Candle
from .data_status import detail_data_status
from .desktop_preferences import DesktopPreferences
from .paper_ui import PaperPanel
from .desktop_widgets import SelectBox
from .efficiency_dialog import EfficiencyDialog



def esc(value):
    return html.escape(str(value))


class WatchlistChangeDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        brush = index.data(Qt.ItemDataRole.ForegroundRole)
        if brush:
            option = QStyleOptionViewItem(option)
            option.palette.setBrush(QPalette.ColorRole.Text, brush)
            option.palette.setBrush(QPalette.ColorRole.HighlightedText, brush)
        super().paint(painter, option, index)


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
        self.ui = DesktopPreferences(self.settings, self)
        self.process = None
        self.results = {}
        self.put_dataset = None
        self.watchlist_quotes = {}
        self.watchlist = WatchlistStore()
        self.buy_alerts = BuyAlertStore()
        self.alert_process = None
        self.depth_process = None
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
        self.runtime.status.connect(lambda text: self.ui.set_text(self.status, text, 'setText'))
        root = QWidget()
        layout = QVBoxLayout(root)
        layout.setContentsMargins(20, 12, 20, 12)
        layout.setSpacing(8)
        eyebrow = QLabel('MOOPIE   /   STOCK RESEARCH'); eyebrow.setObjectName('eyebrow')
        header = QHBoxLayout(); header.addWidget(eyebrow); header.addStretch()
        self.preferences_button = QToolButton(); self.ui.set_text(self.preferences_button, '设置', 'setText')
        self.preferences_button.setProperty('compact', True)
        self.preferences_button.setProperty('menuOnly', True)
        self.preferences_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        menu = QMenu(self.preferences_button)
        language_menu = menu.addMenu('语言 / Language')
        self.language_group = QActionGroup(self); self.language_group.setExclusive(True)
        self.language_actions = {}
        for label, value in [('中文', 'zh'), ('English', 'en')]:
            action = language_menu.addAction(label); action.setCheckable(True)
            action.setChecked(self.ui.language == value); self.language_group.addAction(action)
            action.triggered.connect(lambda checked=False, value=value: self.change_language(value))
            self.language_actions[value] = action
        theme_menu = menu.addMenu('外观')
        self.theme_group = QActionGroup(self); self.theme_group.setExclusive(True)
        self.theme_actions = {}
        for label, value in [('跟随系统', 'system'), ('深色', 'dark'), ('浅色', 'light')]:
            action = theme_menu.addAction(label); action.setCheckable(True)
            action.setChecked(self.ui.theme == value); self.theme_group.addAction(action)
            action.triggered.connect(lambda checked=False, value=value: self.change_theme(value))
            self.theme_actions[value] = action
        connection_menu = menu.addMenu('OpenD 连接')
        for settings_menu in (menu,language_menu,theme_menu,connection_menu):
            settings_menu.setProperty('preferencesMenu',True)
            settings_menu.setMinimumWidth(240)
        menu.setMinimumWidth(280)
        connection_menu.setMinimumWidth(360)
        self.preferences_button.setMenu(menu); header.addWidget(self.preferences_button)
        layout.addLayout(header)
        self.main_tabs = QTabWidget()
        self.main_tabs.tabBar().setObjectName('workspaceNavigation')
        self.analysis_page = QWidget()
        self.main_tabs.addTab(self.analysis_page,'分析')
        layout.addWidget(self.main_tabs,1)
        workspace = QHBoxLayout(self.analysis_page)
        workspace.setContentsMargins(0,6,0,0); workspace.setSpacing(16)
        self.scope_panel = QFrame(); self.scope_panel.setObjectName('scopePanel')
        self.scope_panel.setFixedWidth(280)
        scope_layout = QVBoxLayout(self.scope_panel); scope_layout.setContentsMargins(12,12,12,12)
        scope_layout.addWidget(QLabel('研究范围'))
        self.home_button = QPushButton('首页 · Watchlist')
        self.home_button.clicked.connect(self.search_watchlist)
        scope_layout.addWidget(self.home_button)
        self.radar_button = QPushButton('买点雷达')
        self.radar_button.clicked.connect(self.show_radar)
        scope_layout.addWidget(self.radar_button)
        self.scope_list = QListWidget(); self.scope_list.setObjectName('scopeList')
        self.scope_list.setItemDelegate(WatchlistChangeDelegate(self.scope_list))
        self.scope_list.itemClicked.connect(self.choose_scope)
        scope_layout.addWidget(self.scope_list,1)
        self.manage_button = QPushButton('管理 Watchlist'); self.manage_button.clicked.connect(self.manage_watchlist)
        scope_layout.addWidget(self.manage_button)
        workspace.addWidget(self.scope_panel)
        analysis_content = QWidget(); workspace.addWidget(analysis_content,1)
        layout = QVBoxLayout(analysis_content)
        layout.setContentsMargins(0,0,0,0)
        layout.setSpacing(8)
        self.scope_heading = QLabel('分析 · Watchlist'); self.scope_heading.setObjectName('scopeHeading')
        self.ui.set_text(self.scope_heading,'选择标的 → 比较首选候选 → 查看依据 → 模拟盘评估','setToolTip')
        controls = QHBoxLayout()
        controls.addWidget(self.scope_heading)
        self.symbol = QLineEdit()
        self.symbol.setPlaceholderText('输入代码 / 公司名 / 别名，支持 * 和 ?；留空查看 Watchlist')
        self.symbol.setMinimumWidth(220)
        self.symbol.returnPressed.connect(lambda: self.start('put') if self.symbol.text().strip() else self.search_watchlist())
        controls.addWidget(self.symbol, 1)
        self.put_button = QPushButton('筛选卖出 Put'); self.put_button.setObjectName('primary')
        self.trend_button = QPushButton('分析走势')
        self.put_button.clicked.connect(lambda: self.start('put'))
        self.trend_button.clicked.connect(self.analyze_trend)
        controls.addWidget(self.put_button)
        self.refresh_button = QToolButton()
        self.refresh_button.setProperty('splitMenu',True)
        self.ui.set_text(self.refresh_button, '更新行情', 'setText')
        self.refresh_button.setPopupMode(QToolButton.ToolButtonPopupMode.MenuButtonPopup)
        self.ui.set_text(self.refresh_button, '增量更新：复用有效缓存，只抓缺失或过期股票。盘中缓存60秒；右侧菜单可强制刷新全部。', 'setToolTip')
        self.refresh_button.clicked.connect(lambda: self.refresh_current(update=True))
        refresh_menu = QMenu(self.refresh_button)
        self.force_refresh_action = QAction('强制刷新全部', refresh_menu)
        self.force_refresh_action.triggered.connect(lambda: self.refresh_current(refresh=True))
        refresh_menu.addAction(self.force_refresh_action)
        self.refresh_button.setMenu(refresh_menu)
        self.opend_button = QPushButton('启动 OpenD')
        self.opend_button.clicked.connect(lambda: self.runtime.run('launch'))
        layout.addLayout(controls)
        self.symbol_search = SymbolSuggestions(self.symbol, self)
        self.symbol_search.watchlist_changed.connect(self.update_watchlist_label)
        self.symbol_search.status.connect(self.favorite_status)
        layout.addWidget(self.symbol_search.view)
        settings_row = QHBoxLayout()
        self.ranking_summary = QLabel(); self.ranking_summary.setObjectName('muted')
        self.ranking_summary.setWordWrap(True)
        settings_row.addWidget(self.ranking_summary, 1)
        settings_row.addWidget(QLabel('Top'))
        self.top_count = SelectBox()
        self.top_count.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
        self.top_count.setMinimumWidth(92)
        for count in (5, 10, 20): self.top_count.addItem(str(count), count)
        try: saved_count = int(self.settings.value('put_top_n', 10))
        except (ValueError, TypeError): saved_count = 10
        self.top_count.setCurrentIndex(self.top_count.findData(saved_count if saved_count in (5, 10, 20) else 10))
        self.top_count.currentIndexChanged.connect(self.change_top_count)
        settings_row.addWidget(self.top_count)
        self.rules_button = QPushButton('Filter / 评分设置')
        self.rules_button.clicked.connect(self.show_rules)
        settings_row.addWidget(self.rules_button)
        self.port = QSpinBox(); self.port.setRange(1, 65535); self.port.setValue(port)
        self.port.valueChanged.connect(self.reset_panels)
        connection_widget = QWidget(); connection_layout = QVBoxLayout(connection_widget)
        connection_layout.setContentsMargins(14,12,14,12); connection_layout.setSpacing(12)
        port_row = QHBoxLayout(); port_row.addWidget(QLabel('OpenD 端口')); port_row.addWidget(self.port,1)
        connection_layout.addLayout(port_row)
        connection_layout.addWidget(self.opend_button)
        connection_action = QWidgetAction(connection_menu); connection_action.setDefaultWidget(connection_widget)
        connection_menu.addAction(connection_action)
        self.tabs = QTabWidget()
        self.ranking_card = QFrame(); self.ranking_card.setObjectName('rankingCard')
        card = QVBoxLayout(self.ranking_card); card.setContentsMargins(0, 8, 0, 6); card.setSpacing(6)
        card_header = QHBoxLayout(); card_header.setContentsMargins(20, 0, 20, 0)
        self.ranking_title = QLabel('候选排行榜 · Top 10'); self.ranking_title.setObjectName('cardTitle')
        card_header.addWidget(self.ranking_title)
        badge = QLabel('现金担保 PUT'); badge.setObjectName('badge'); card_header.addWidget(badge)
        card_header.addStretch()
        self.data_state = QLabel('等待查询'); self.data_state.setObjectName('dataState'); card_header.addWidget(self.data_state)
        self.efficiency_button = QPushButton('持仓效率')
        self.efficiency_button.setProperty('compact',True)
        self.efficiency_button.clicked.connect(self.show_efficiency)
        card_header.addWidget(self.efficiency_button)
        self.watchlist_button = QToolButton()
        self.watchlist_button.setProperty('menuOnly', True)
        self.watchlist_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.watchlist_menu = QMenu(self.watchlist_button)
        self.view_watchlist_action = self.watchlist_menu.addAction('查看 Watchlist')
        self.view_watchlist_action.triggered.connect(self.search_watchlist)
        self.add_watchlist_action = self.watchlist_menu.addAction('加入 Watchlist')
        self.ui.set_text(self.add_watchlist_action, '将输入的股票加入名单；只核验证券资料，不抓取期权行情。', 'setToolTip')
        self.add_watchlist_action.triggered.connect(lambda: self.start('add'))
        self.manage_watchlist_action = self.watchlist_menu.addAction('管理 Watchlist')
        self.manage_watchlist_action.triggered.connect(self.manage_watchlist)
        self.watchlist_menu.addSeparator()
        self.directory_action = self.watchlist_menu.addAction('更新股票目录')
        self.ui.set_text(self.directory_action, '连接 OpenD 同步美股和 ETF 的代码、公司名；不抓取报价。', 'setToolTip')
        self.directory_action.triggered.connect(lambda: self.start('sync-directory'))
        self.watchlist_menu.setToolTipsVisible(True)
        self.watchlist_button.setMenu(self.watchlist_menu)
        self.update_watchlist_label()
        scope_layout.insertWidget(1,self.watchlist_button)
        card.addLayout(card_header)
        self.first_card = QFrame(); self.first_card.setObjectName('firstChoice')
        first_layout = QVBoxLayout(self.first_card); first_layout.setContentsMargins(14,8,14,8); first_layout.setSpacing(4)
        first_header = QHBoxLayout()
        first_header.addWidget(QLabel('No.1'))
        self.first_choice = QLabel(); self.first_choice.setObjectName('firstChoiceTitle')
        self.first_choice.setWordWrap(True); first_header.addWidget(self.first_choice, 1)
        self.first_details = QPushButton('查看推荐依据')
        self.first_details.setProperty('compact', True)
        self.first_details.clicked.connect(self.open_first_choice)
        first_header.addWidget(self.first_details); first_layout.addLayout(first_header)
        self.first_metrics = QLabel(); self.first_metrics.setWordWrap(True); first_layout.addWidget(self.first_metrics)
        self.first_card.setContentsMargins(16,0,16,0); card.addWidget(self.first_card)
        self.ui.set_text(self.first_card,'收益按 Bid 与全额现金担保计算，未扣费用。蓝色条表示综合分；财报未验证或事件风险以琥珀色标注。','setToolTip')
        settings_row.setContentsMargins(20,0,20,0); card.addLayout(settings_row)
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
        self.details_button.setProperty('compact', True)
        self.details_button.clicked.connect(lambda: self.tabs.setCurrentIndex(1)); list_footer.addWidget(self.details_button)
        card.addLayout(list_footer)
        self.put_result = QTextBrowser(); self.trend_result = QTextBrowser()
        self.price_signal_result = QTextBrowser()
        self.order_book_result = OrderBookChart()
        self.support_chart = CandleChart()
        self.support_chart.message = '选择个股后显示已完成日线及支撑阻力区。'
        for panel in (self.put_result, self.trend_result, self.price_signal_result):
            panel.setOpenExternalLinks(False)
        self.tabs.addTab(self.ranking_card, '推荐与候选')
        self.tabs.addTab(self.put_result, '合约详情 / 筛选依据')
        technical_page = QWidget(); technical_layout = QVBoxLayout(technical_page)
        technical_header = QHBoxLayout(); technical_header.addWidget(QLabel('个股依据 · 支撑阻力、买卖盘与趋势'))
        technical_header.addStretch(); technical_header.addWidget(self.trend_button)
        technical_layout.addLayout(technical_header)
        self.detail_data_state = QLabel('报价、盘口与日线时间将在个股详情显示。')
        self.detail_data_state.setWordWrap(True)
        technical_layout.addWidget(self.detail_data_state)
        self.depth_tabs = QTabWidget()
        support_page = QWidget(); support_layout = QVBoxLayout(support_page)
        self.timeframe_summary = QLabel('周线与月线价位会在个股分析后显示。')
        self.timeframe_summary.setWordWrap(True)
        support_layout.addWidget(self.timeframe_summary)
        chart_and_details = QSplitter(Qt.Orientation.Horizontal)
        self.support_chart.setMinimumSize(320, 240)
        self.price_signal_result.setMinimumWidth(260)
        chart_and_details.addWidget(self.support_chart)
        chart_and_details.addWidget(self.price_signal_result)
        chart_and_details.setStretchFactor(0, 3)
        chart_and_details.setStretchFactor(1, 2)
        chart_and_details.setSizes([620, 500])
        support_layout.addWidget(chart_and_details, 1)
        self.depth_tabs.addTab(support_page, '支撑阻力')
        self.depth_tabs.addTab(self.order_book_result, '买卖盘变化')
        self.depth_tabs.addTab(self.trend_result, '走势分析')
        plan_page = QWidget(); plan_layout = QVBoxLayout(plan_page)
        plan_controls = QHBoxLayout()
        plan_controls.addWidget(QLabel('计划投入 $'))
        self.plan_budget = QDoubleSpinBox()
        self.plan_budget.setRange(1, 1000000000)
        self.plan_budget.setDecimals(2)
        self.plan_budget.setValue(3000)
        self.plan_budget.setSingleStep(100)
        plan_controls.addWidget(self.plan_budget)
        plan_controls.addWidget(QLabel('风险预算 $'))
        self.plan_risk = QDoubleSpinBox()
        self.plan_risk.setRange(0, 1000000000)
        self.plan_risk.setDecimals(2)
        self.plan_risk.setSpecialValueText('不限')
        self.plan_risk.setToolTip('0 表示不限；仅限制跌至支撑下沿的估算账面损失。')
        plan_controls.addWidget(self.plan_risk)
        self.plan_button = QPushButton('计算分批计划')
        self.plan_button.clicked.connect(self.calculate_buy_plan)
        plan_controls.addWidget(self.plan_button)
        plan_controls.addStretch()
        plan_layout.addLayout(plan_controls)
        alert_controls = QHBoxLayout()
        alert_controls.addWidget(QLabel('确认方式'))
        self.alert_mode = SelectBox()
        self.alert_mode.addItem('后续报价站回上沿', 'quote')
        self.alert_mode.addItem('次交易日收盘站回上沿', 'daily_close')
        self.alert_mode.setToolTip('日线模式先观察到价格进入支撑区，再等下一交易日已完成日线收盘站上上沿。')
        alert_controls.addWidget(self.alert_mode)
        self.alert_button = QPushButton('开启买点提醒')
        self.alert_button.clicked.connect(self.arm_buy_alert)
        alert_controls.addWidget(self.alert_button)
        self.pause_alert_button = QPushButton('暂停提醒')
        self.pause_alert_button.clicked.connect(self.pause_buy_alert)
        alert_controls.addWidget(self.pause_alert_button)
        alert_controls.addStretch()
        plan_layout.addLayout(alert_controls)
        self.plan_result = QLabel('选择个股后，可按已确认支撑区计算假设计划。')
        self.plan_result.setWordWrap(True)
        self.plan_result.setObjectName('muted')
        plan_layout.addWidget(self.plan_result)
        self.alert_result = QLabel('提醒仅在 MooPie 开启且 OpenD 可用时检查新报价。')
        self.alert_result.setWordWrap(True)
        plan_layout.addWidget(self.alert_result)
        plan_layout.addStretch()
        self.depth_tabs.addTab(plan_page, '买入计划与提醒')
        technical_layout.addWidget(self.depth_tabs,1)
        self.tabs.addTab(technical_page, '技术面依据')
        self.paper_panel = PaperPanel(self)
        self.main_tabs.addTab(self.paper_panel, '模拟盘')
        self.overview_page = QWidget()
        overview_layout = QVBoxLayout(self.overview_page)
        overview_layout.addWidget(QLabel('Watchlist · 股价和涨跌'))
        self.overview_note = QLabel('正在读取价格…')
        self.overview_note.setObjectName('muted'); self.overview_note.setWordWrap(True)
        overview_layout.addWidget(self.overview_note)
        self.overview_table = QTableWidget(0, 3)
        self.overview_table.setHorizontalHeaderLabels(['股票', '股价', '涨跌'])
        self.overview_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.overview_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.overview_table.verticalHeader().setVisible(False)
        self.overview_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.overview_table.cellClicked.connect(self.open_overview_row)
        overview_layout.addWidget(self.overview_table, 1)
        self.radar_page = QWidget()
        radar_layout = QVBoxLayout(self.radar_page)
        radar_layout.addWidget(QLabel('买点雷达 · Watchlist'))
        self.radar_note = QLabel('正在读取报价与已保存支撑区…')
        self.radar_note.setObjectName('muted'); self.radar_note.setWordWrap(True)
        radar_layout.addWidget(self.radar_note)
        self.radar_table = QTableWidget(0, 5)
        self.radar_table.setHorizontalHeaderLabels(['股票', '股价', '支撑区', '状态', '距支撑上沿'])
        self.radar_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.radar_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.radar_table.verticalHeader().setVisible(False)
        self.radar_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.radar_table.cellClicked.connect(self.open_radar_row)
        radar_layout.addWidget(self.radar_table, 1)
        self.analysis_stack = QStackedWidget()
        self.analysis_stack.addWidget(self.overview_page)
        self.analysis_stack.addWidget(self.tabs)
        self.analysis_stack.addWidget(self.radar_page)
        layout.addWidget(self.analysis_stack, 1)
        self.reset_panels()
        self.symbol.textChanged.connect(self.reset_panels)
        footer = QHBoxLayout()
        self.status = QLabel('默认查看已保存的收盘结果；点击「更新行情」刷新。首次查询新股票会自动抓取。'); self.status.setObjectName('muted')
        self.status.setWordWrap(True); footer.addWidget(self.status, 1)
        self.cancel_button = QPushButton('取消'); self.cancel_button.hide()
        self.cancel_button.clicked.connect(self.cancel); footer.addWidget(self.cancel_button)
        self.export_button = QPushButton('导出结果'); self.export_button.setEnabled(False)
        self.export_button.clicked.connect(self.export); footer.addWidget(self.export_button)
        footer.addWidget(self.refresh_button)
        layout.addLayout(footer)
        self.setCentralWidget(root)
        self.ui.root = self
        self.candidate_table.ui = self.ui
        self.ui.apply_theme()
        self.alert_timer = QTimer(self)
        self.alert_timer.setInterval(60000)
        self.alert_timer.timeout.connect(self.poll_buy_alerts)
        self.alert_timer.start()
        self.depth_timer = QTimer(self)
        self.depth_timer.setInterval(30000)
        self.depth_timer.timeout.connect(self.poll_depth)
        if auto_load: QTimer.singleShot(0, self.initial_watchlist)

    def initial_watchlist(self):
        self.symbol.clear()
        self.main_tabs.setCurrentIndex(0)
        self.analysis_stack.setCurrentIndex(0)
        self.start('overview')

    def favorite_status(self, message):
        if self.process is None: self.ui.set_text(self.status,message)

    def refresh_current(self, *, update=False, refresh=False):
        action = ('overview' if self.analysis_stack.currentIndex() == 0 else
                  'radar' if self.analysis_stack.currentIndex() == 2 else
                  'trend' if self.tabs.currentIndex() == 2 else 'put')
        self.start(action, update=update, refresh=refresh, depth=action == 'trend' and bool(self.symbol.text().strip()))

    def analyze_trend(self):
        self.start('trend', depth=bool(self.symbol.text().strip()))
        self.depth_tabs.setCurrentIndex(2)

    def change_language(self, value):
        self.ui.set_language(value)
        self.update_watchlist_label()
        if self.analysis_stack.currentIndex() == 2 and self.results.get('radar'):
            self.display_radar(self.results['radar'])
        current = self.results.get('trend', {}).get('symbol')
        if current:
            self.calculate_buy_plan()
            self.show_timeframe_summary(self.current_buy_signal() or {})
            try: self.show_alert_state(self.buy_alerts.get(current))
            except (OSError, RuntimeError): pass
        if self.order_book_result.book:
            self.order_book_result.set_book(self.order_book_result.book, self.order_book_result.quote,
                                            language=value, theme=self.ui.effective_theme,
                                            history=self.order_book_result.history)
        if self.results.get('trend'): self.show_detail_data_status(self.results['trend'])

    def change_theme(self, value):
        self.ui.set_theme(value)
        self.update_watchlist_label()
        if self.analysis_stack.currentIndex() == 2 and self.results.get('radar'):
            self.display_radar(self.results['radar'])
        current = self.results.get('trend', {}).get('symbol')
        if current:
            try: self.show_alert_state(self.buy_alerts.get(current))
            except (OSError, RuntimeError): pass
        if self.order_book_result.book:
            self.order_book_result.set_book(self.order_book_result.book, self.order_book_result.quote,
                                            language=self.ui.language, theme=self.ui.effective_theme,
                                            history=self.order_book_result.history)
        if self.results.get('trend'): self.show_detail_data_status(self.results['trend'])
        for index, row in enumerate(self.results.get('overview', {}).get('rows', [])):
            color = self.change_color(row.get('change_pct'))
            for column in (1, 2):
                item = self.overview_table.item(index, column)
                if item and color: item.setForeground(color)

    def change_color(self, change):
        if change is None or change == 0: return None
        if self.ui.effective_theme == 'dark': return QColor('#48d67f' if change > 0 else '#ff7777')
        return QColor('#167a3e' if change > 0 else '#bd3030')

    def open_stock(self, code):
        if self.process is not None: return
        self.symbol.setText(code.removeprefix('US.'))
        self.analysis_stack.setCurrentIndex(1)
        self.depth_tabs.setCurrentIndex(0)
        self.start('trend', depth=True)

    def current_buy_signal(self):
        result = self.results.get('trend', {})
        return result.get('price_signals', {}).get(result.get('symbol'))

    def calculate_buy_plan(self):
        try:
            plan = calculate_plan(self.current_buy_signal(), self.plan_budget.value(), self.plan_risk.value() or None)
        except ValueError as error:
            self.ui.set_text(self.plan_result, str(error))
            return
        if self.ui.language == 'en':
            cap_note = (f' Risk budget ${plan["risk_budget"]:,.2f} reduced the original ${plan["uncapped_loss_to_stop"]:,.2f} estimate.'
                        if plan['risk_limited'] else '')
            cells = ''.join(f'<td width="33%"><b>Tranche {index} · {weight}%</b><br>'
                            f'<span style="font-size:17px">${row["price"]:,.2f}</span> × {row["shares"]} shares</td>'
                            for index, (weight, row) in enumerate(zip((40, 30, 30), plan['tranches']), 1))
            target = (f'Nearest resistance ${plan["resistance"]:,.2f}; paper gain at that price ${plan["target_gain"]:,.2f}'
                      if plan['resistance'] is not None else 'No confirmed resistance above; target not estimated')
            self.plan_result.setText(
                '<h3 style="margin:2px 0">Hypothetical stock plan</h3><table width="100%" cellpadding="5"><tr>' + cells + '</tr></table>'
                f'<p>All filled: {plan["shares"]} shares · Cost ${plan["cost"]:,.2f} · Unused ${plan["unused"]:,.2f}. '
                f'Support floor ${plan["stop"]:,.2f}; paper loss at that price about ${plan["max_loss_to_stop"]:,.2f}; {target}.{cap_note}</p>'
                '<p style="color:#9c6920">Later tranches assume a retest with support intact. Fees, slippage and gaps are excluded; losses can be larger.</p>')
            return
        cells = ''.join(f'<td width="33%"><b>第 {index} 批 · {weight}%</b><br>'
                        f'<span style="font-size:17px">${row["price"]:,.2f}</span> × {row["shares"]} 股</td>'
                        for index, (weight, row) in enumerate(zip((40, 30, 30), plan['tranches']), 1))
        target = (f'上方阻力 ${plan["resistance"]:,.2f}，至该价账面空间 ${plan["target_gain"]:,.2f}'
                  if plan['resistance'] is not None else '上方暂无已确认阻力，无法估算目标空间')
        cap_note = (f' 风险预算 ${plan["risk_budget"]:,.2f} 将原估算亏损 ${plan["uncapped_loss_to_stop"]:,.2f} 对应的股数缩小。'
                    if plan['risk_limited'] else '')
        self.plan_result.setText(
            '<h3 style="margin:2px 0">假设买入计划</h3><table width="100%" cellpadding="5"><tr>' + cells + '</tr></table>'
            f'<p>全部成交：{plan["shares"]} 股 · 成本 ${plan["cost"]:,.2f} · 未用 ${plan["unused"]:,.2f}。'
            f'支撑下沿 ${plan["stop"]:,.2f}，跌至该价账面亏损约 ${plan["max_loss_to_stop"]:,.2f}；{target}。{cap_note}</p>'
            '<p style="color:#9c6920">后两批仅考虑支撑有效时的回踩；未计费用、滑点或跳空，跌破支撑可能损失更多。</p>')

    def show_alert_state(self, record):
        if not record:
            self.alert_result.setStyleSheet('')
            self.ui.set_text(self.alert_result, '提醒未开启；仅在 MooPie 开启且 OpenD 可用时检查新报价。')
            return
        labels = ({'watching': 'Waiting for price to enter support',
                   'inside': 'Inside support; waiting for a later quote above its upper edge',
                   'confirmed': 'Condition observed: entered support, then reclaimed its upper edge; review before acting',
                   'invalidated': 'Condition invalid: price fell below support', 'paused': 'Alert paused'}
                  if self.ui.language == 'en' else
                  {'watching': '等待价格进入支撑区', 'inside': '已进入支撑区，等待后续新报价重新站上区间上沿',
                   'confirmed': '条件已出现：先入支撑区，后重新站上上沿；请自行复核',
                   'invalidated': '条件失效：价格跌破支撑下沿', 'paused': '提醒已暂停'})
        if record.get('confirmation_mode') == 'daily_close':
            labels['inside'] = ('Inside support; waiting for a completed close above the upper edge on a later trading day'
                                if self.ui.language == 'en' else '已进入支撑区，等待下一交易日已完成日线收盘站上上沿')
            labels['confirmed'] = ('Condition observed: a later daily close reclaimed the upper edge; review before acting'
                                   if self.ui.language == 'en' else '条件已出现：后续日线收盘站上上沿；请自行复核')
        color = ({'inside': '#d5a031', 'confirmed': '#48d67f', 'invalidated': '#ff7777'}
                 if self.ui.effective_theme == 'dark' else
                 {'inside': '#8e6000', 'confirmed': '#167a3e', 'invalidated': '#bd3030'})
        self.alert_result.setStyleSheet('color: '+color[record['status']]+';' if record['status'] in color else '')
        if self.ui.language == 'en':
            self.alert_result.setText(
                f'Buy-point alert: {labels[record["status"]]}. Zone ${record["support_low"]:,.2f}–${record["support_high"]:,.2f}'
                f' (daily bars through {record["signal_as_of"]}); last quote {record["last_quote_time"] or "time unavailable"} (New York).')
        else:
            self.alert_result.setText(
                f'买点提醒：{labels[record["status"]]}。监控区 ${record["support_low"]:,.2f}–${record["support_high"]:,.2f}'
                f'（日线截至 {record["signal_as_of"]}）；最近报价 {record["last_quote_time"] or "未提供时间"}（纽约）。')

    def show_timeframe_summary(self, signal):
        multi = signal.get('multi_timeframe', {})
        if multi.get('status') == 'ok':
            labels = (('Weekly', 'Monthly') if self.ui.language == 'en' else ('周线', '月线'))
            parts = []
            for label, period in zip(labels, ('week', 'month')):
                item = multi['periods'][period]
                if item.get('status') != 'ok':
                    parts.append(f'<b>{label}</b>：{esc(self.ui.translate(item.get("reason", "数据不足")))}')
                    continue
                support = item.get('support_zones', [])
                resistance = item.get('resistance_zones', [])
                support_price = (f'${support[0]["low"]:,.2f}–${support[0]["high"]:,.2f}' if support else '—')
                resistance_price = (f'${resistance[0]["low"]:,.2f}–${resistance[0]["high"]:,.2f}' if resistance else '—')
                lower = 'Support' if self.ui.language == 'en' else '支撑'
                upper = 'Resistance' if self.ui.language == 'en' else '阻力'
                parts.append(f'<b>{label}</b> ({esc(item["as_of"])})：'
                             f'<span style="color:#32b873">{lower} {support_price}</span> · '
                             f'<span style="color:#e26060">{upper} {resistance_price}</span>')
            self.timeframe_summary.setText('<br>'.join(parts))
        else:
            self.ui.set_text(self.timeframe_summary, '周线 / 月线价位暂不可用。')

    def show_buy_plan_context(self, result):
        self.calculate_buy_plan()
        self.show_timeframe_summary(self.current_buy_signal() or {})
        symbol = result.get('symbol')
        if not symbol: return
        try:
            if result.get('quote'):
                record, event = self.buy_alerts.observe(symbol, result['quote'], with_event=True)
            else:
                record, event = self.buy_alerts.get(symbol), False
            trend = result.get('trend', {})
            if record and record['status'] == 'inside' and record['confirmation_mode'] == 'daily_close' and trend.get('status') == 'ok':
                record, close_event = self.buy_alerts.observe_close(symbol, trend.get('metrics', {}).get('close'),
                                                                    trend.get('as_of'), with_event=True)
                event = event or close_event
            if record: self.alert_mode.setCurrentIndex(self.alert_mode.findData(record['confirmation_mode']))
            self.show_alert_state(record)
            if event:
                QMessageBox.information(self, self.ui.translate('买点条件更新'), symbol + '：' + self.alert_result.text())
        except (OSError, RuntimeError, ValueError) as error:
            self.alert_result.setText('读取买点提醒失败：' + str(error))

    def arm_buy_alert(self):
        signal = self.current_buy_signal()
        try:
            result = self.results.get('trend', {})
            record = self.buy_alerts.arm(signal, result.get('quote'), mode=self.alert_mode.currentData())
            self.show_alert_state(record)
            self.poll_buy_alerts()
        except (OSError, RuntimeError, ValueError, TypeError) as error:
            self.alert_result.setText(str(error))

    def pause_buy_alert(self):
        result = self.results.get('trend', {})
        symbol = result.get('symbol')
        if not symbol: return
        try: self.show_alert_state(self.buy_alerts.pause(symbol))
        except (OSError, RuntimeError, ValueError) as error: self.alert_result.setText(str(error))

    def poll_buy_alerts(self):
        if self.alert_process is not None: return
        try:
            if not self.buy_alerts.active_symbols(): return
        except (OSError, RuntimeError): return
        path = Path(self.workspace.name) / 'alerts.json'
        path.unlink(missing_ok=True)
        process = QProcess(self)
        self.alert_process = process
        process.finished.connect(lambda code, _status: self.alert_poll_finished(code, path))
        process.errorOccurred.connect(lambda error: self.alert_poll_error(error))
        args = (['research'] if getattr(sys, 'frozen', False) else ['-X', 'utf8', '-m', 'moopython.research_cli'])
        process.start(sys.executable, [*args, 'alerts', '--port', str(self.port.value()), '--output', str(path)])

    def alert_poll_error(self, error):
        if error == QProcess.ProcessError.FailedToStart:
            self.alert_result.setText('买点提醒查询未启动：' + self.alert_process.errorString())
            self.alert_process.deleteLater(); self.alert_process = None

    def alert_poll_finished(self, exit_code, path):
        process = self.alert_process
        if process is None: return
        try:
            payload = json.loads(path.read_text(encoding='utf-8'))
            if exit_code or payload.get('error'):
                raise ValueError(payload.get('error', f'查询进程退出：{exit_code}'))
            current = self.results.get('trend', {}).get('symbol')
            for row in payload.get('rows', []):
                if row['symbol'] == current: self.show_alert_state(row['alert'])
                if row.get('event'):
                    confirmed = row['alert']['status'] == 'confirmed'
                    daily = row['alert']['confirmation_mode'] == 'daily_close'
                    if self.ui.language == 'en':
                        message = ('A later daily close reclaimed the support upper edge; review the current price.' if daily else
                                   'Reclaimed the support zone upper edge; review the current quote.') if confirmed else 'Fell below the support zone; the original condition is invalid.'
                    else:
                        message = ('后续日线收盘站上支撑区上沿，请复核当前价格。' if daily else
                                   '已重新站上支撑区上沿，请自行复核。') if confirmed else '已跌破支撑区下沿，原条件失效。'
                    QMessageBox.information(self, self.ui.translate('买点条件更新'), row['symbol'] + '：' + message)
            if payload.get('daily_error') and current:
                current_alert = self.buy_alerts.get(current)
                if current_alert and current_alert['confirmation_mode'] == 'daily_close':
                    self.alert_result.setText(self.alert_result.text() + ' · 日线检查失败：' + payload['daily_error'])
        except (OSError, ValueError, KeyError) as error:
            self.alert_result.setText('买点提醒本次未能检查：' + str(error))
        finally:
            process.deleteLater(); self.alert_process = None

    def poll_depth(self):
        if self.depth_process is not None or self.process is not None:
            return
        if (self.main_tabs.currentIndex() != 0 or self.analysis_stack.currentIndex() != 1
                or self.tabs.currentIndex() != 2):
            return
        symbol = self.results.get('trend', {}).get('symbol')
        if not symbol or not self.order_book_result.book:
            return
        path = Path(self.workspace.name) / 'depth.json'
        path.unlink(missing_ok=True)
        process = QProcess(self)
        self.depth_process = process
        process.finished.connect(lambda code, _status: self.depth_poll_finished(code, path, symbol))
        process.errorOccurred.connect(self.depth_poll_error)
        args = (['research'] if getattr(sys, 'frozen', False) else ['-X', 'utf8', '-m', 'moopython.research_cli'])
        process.start(sys.executable, [*args, 'depth', symbol, '--port', str(self.port.value()),
                                       '--output', str(path)])

    def depth_poll_error(self, error):
        if error == QProcess.ProcessError.FailedToStart and self.depth_process:
            self.ui.set_text(self.detail_data_state,
                             '盘口跟踪未启动：' + self.depth_process.errorString())
            self.depth_process.deleteLater(); self.depth_process = None

    def depth_poll_finished(self, exit_code, path, symbol):
        process = self.depth_process
        if process is None: return
        try:
            payload = json.loads(path.read_text(encoding='utf-8'))
            if exit_code or payload.get('error'):
                raise ValueError(payload.get('error', f'盘口查询进程退出：{exit_code}'))
            result = self.results.get('trend', {})
            if result.get('symbol') != symbol or self.analysis_stack.currentIndex() != 1:
                return
            result['order_book'] = payload['order_book']
            result['order_book_history'] = payload.get('order_book_history', [])
            result['order_book_history_error'] = payload.get('order_book_history_error')
            if payload.get('quote'):
                result['quote'] = payload['quote']
            result['quote_error'] = payload.get('quote_error')
            self.order_book_result.set_book(result['order_book'], result.get('quote'),
                                            language=self.ui.language, theme=self.ui.effective_theme,
                                            history=result['order_book_history'])
            self.show_detail_data_status(result)
        except (OSError, ValueError, KeyError) as error:
            self.ui.set_text(self.detail_data_state, '盘口跟踪失败：' + str(error))
        finally:
            process.deleteLater(); self.depth_process = None

    def show_detail_data_status(self, result):
        signal = result.get('price_signals', {}).get(result.get('symbol'))
        status = detail_data_status(result.get('quote'), result.get('order_book'), signal)
        english = self.ui.language == 'en'
        labels = {'regular': 'regular', 'pre': 'pre-market', 'after': 'after-hours',
                  'overnight': 'overnight'} if english else {
                  'regular': '常规交易', 'pre': '盘前', 'after': '盘后', 'overnight': '夜盘'}
        if english:
            message = (f'Data times · quote (New York): {status["quote_time"] or "unknown"} '
                       f'[{labels.get(status["session"], "unknown")}] · '
                       f'book captured (UTC): {status["book_time"] or "unknown"} · '
                       f'daily through: {status["daily_date"] or "unknown"}. '
                       + ('Check source times and session; exact book freshness is unverified.'
                          if status['issues'] else 'Source times appear aligned.'))
        else:
            message = (f'数据时间 · 报价（纽约）：{status["quote_time"] or "未知"}'
                       f'［{labels.get(status["session"], "未知时段")}］ · '
                       f'盘口采集（UTC）：{status["book_time"] or "未知"} · '
                       f'日线截至：{status["daily_date"] or "未知"}。'
                       + ('需核对：' + '；'.join(status['issues']) if status['issues'] else '时间基本对齐。'))
            if signal and signal.get('status') == 'ok' and signal.get('reference', {}).get('time') != status['quote_time']:
                message += ' 支撑阻力距离仍基于上次分析时的报价；刷新个股分析可更新。'
        if result.get('quote_error'):
            message += (' Quote error: ' if english else ' 报价错误：') + str(result['quote_error'])
        if result.get('order_book_history_error'):
            message += (' History error: ' if english else ' 盘口历史错误：') + str(result['order_book_history_error'])
        color = '#d5a031' if status['issues'] else '#32b873'
        self.detail_data_state.setStyleSheet(f'color:{color};font-weight:600;')
        self.ui.set_text(self.detail_data_state, message)

    def show_support_chart(self, result):
        signal = result.get('price_signals', {}).get(result.get('symbol'))
        rows = result.get('chart_bars') or []
        if signal and signal.get('status') == 'ok' and rows:
            self.support_chart.message = ''
            self.support_chart.set_bars([Candle(row['date'], row['open'], row['high'], row['low'],
                                                row['close'], row.get('volume') or 0) for row in rows], '日K')
            self.support_chart.set_zones(signal)
        else:
            self.support_chart.set_bars([])
            self.support_chart.set_zones(None)
            self.support_chart.message = ('已验证日线不足，暂不能绘制支撑阻力图。' if self.ui.language == 'zh' else
                                          'Validated daily bars unavailable; support chart cannot be shown.')

    def open_overview_row(self, row, _column):
        item = self.overview_table.item(row, 0)
        if item: self.open_stock(item.data(Qt.ItemDataRole.UserRole))

    def open_radar_row(self, row, _column):
        item = self.radar_table.item(row, 0)
        if item: self.open_stock(item.data(Qt.ItemDataRole.UserRole))

    def show_radar(self):
        if self.process is not None: return
        self.symbol.clear()
        self.analysis_stack.setCurrentIndex(2)
        self.start('radar', update=True)

    def choose_scope(self, item):
        if self.process is not None: return
        code = item.data(Qt.ItemDataRole.UserRole)
        if code:
            self.open_stock(code)
        else: self.search_watchlist()

    def open_first_choice(self):
        if not self.results.get('put',{}).get('report',{}).get('recommendations'): return
        self.candidate_table.selectRow(0)
        self.tabs.setCurrentIndex(1)

    def show_efficiency(self):
        report=self.results.get('put',{}).get('report',{})
        choices=report.get('recommendations',[])
        index=self.candidate_table.currentRow()
        code=choices[index]['code'] if 0<=index<len(choices) else None
        row=next((row for row in report.get('ranked',[]) if row['code']==code),None)
        EfficiencyDialog(self,row=row,session_date=report.get('session_date')).exec()

    def show_first_choice(self, report=None):
        choices=(report or {}).get('recommendations',[])
        self.first_details.setEnabled(bool(choices))
        if not choices:
            self.ui.set_text(self.first_choice,'暂无首选候选')
            self.ui.set_text(self.first_metrics,'先选择标的并分析；没有符合条件的合约时，不自动放宽 Filter。')
            return
        first=choices[0]
        row=next(r for r in report['ranked'] if r['code']==first['code'])
        m=row['metrics']
        self.ui.set_text(self.first_choice,f'{row["symbol"].removeprefix("US.")} · {row["expiration"]} · Put ${m["strike"]:,.2f}')
        self.ui.set_text(self.first_metrics,f'每张权利金 ${m["premium_per_contract_before_costs"]:,.2f} · 现金担保 ${m["cash_collateral"]:,.0f} · 日均毛收益率 {m["daily_gross_return_pct"]:.4f}% · 风险分 {m["risk_score"]:.1f} / 100 · 综合分 {m["composite_score"]:.1f} / 100')

    def update_watchlist_label(self):
        try:
            symbols = self.watchlist.symbols()
            count = len(symbols)
            names = SecurityDirectory().lookup(symbols)
            self.symbol_search.refresh_membership()
            self.ui.set_text(self.watchlist_button, f'Watchlist ({count})', 'setText')
            self.ui.set_text(self.view_watchlist_action, f'查看 Watchlist ({count})', 'setText')
            current=self.symbol.text().strip().upper().removeprefix('US.')
            self.scope_list.clear()
            all_item=QListWidgetItem('全部 Watchlist'); self.scope_list.addItem(all_item)
            selected=0 if not current else -1
            for code in symbols:
                quote = self.watchlist_quotes.get(code, {})
                name = quote.get('name') or names.get(code, {}).get('name') or code.removeprefix('US.')
                price = f'${quote["price"]:,.2f}' if quote.get('price') is not None else '—'
                change = quote.get('change_pct')
                change_label = f'{change:+.2f}%' if change is not None else '—'
                item=QListWidgetItem(f'{name}\n{price}   {change_label}')
                item.setData(Qt.ItemDataRole.UserRole,code)
                item.setToolTip(f'{code} · 报价时间（纽约）：{quote.get("update_time") or "未提供"}')
                color = self.change_color(change)
                if color: item.setForeground(color)
                item.setSizeHint(QSize(0, max(64, self.scope_list.fontMetrics().lineSpacing()*2+20)))
                self.scope_list.addItem(item)
                if code.removeprefix('US.')==current: selected=self.scope_list.count()-1
            self.scope_list.setCurrentRow(selected)
            self.ui.localize_list(self.scope_list,fresh=True)
        except (ValueError, OSError):
            self.ui.set_text(self.watchlist_button, 'Watchlist（需检查）', 'setText')
            self.ui.set_text(self.view_watchlist_action, '查看 Watchlist（需检查）', 'setText')
        self.ui.set_text(self.watchlist_button, '查看、添加、管理 Watchlist，或更新股票目录。\nSQLite：' + str(self.watchlist.store.path), 'setToolTip')

    def search_watchlist(self):
        if self.process is not None: return
        self.depth_timer.stop()
        self.symbol.clear()
        self.update_watchlist_label()
        self.analysis_stack.setCurrentIndex(0)
        self.start('overview')

    def manage_watchlist(self):
        if self.process is not None: return
        self.symbol_search.dismiss()
        try:
            dialog = WatchlistDialog(self.watchlist, self)
            if dialog.exec() != QDialog.DialogCode.Accepted: return
            self.update_watchlist_label()
            self.reset_panels()
            self.ui.set_text(self.status, f'Watchlist 已保存，删除 {dialog.removal_result["removed_count"]} 项。从菜单选择「查看 Watchlist」查看最新结果。', 'setText')
        except (ValueError, RuntimeError, OSError) as error:
            self.ui.set_text(self.status, '无法打开 Watchlist：' + str(error), 'setText')

    def reset_panels(self):
        if hasattr(self, 'depth_timer'): self.depth_timer.stop()
        self.results.clear()
        self.put_dataset = None
        self.ui.set_text(self.scope_heading,'分析 · '+(self.symbol.text().strip().upper() or 'Watchlist'))
        self.ui.set_text(self.price_signal_result, signals_html({}), 'setHtml')
        self.order_book_result.set_book(None, language=self.ui.language, theme=self.ui.effective_theme)
        self.support_chart.set_bars([])
        self.support_chart.set_zones(None)
        self.support_chart.message = '选择个股后显示已完成日线及支撑阻力区。'
        self.ui.set_text(self.detail_data_state, '报价、盘口与日线时间将在个股详情显示。')
        self.ui.set_text(self.plan_result, '选择个股后，可按已确认支撑区计算假设计划。')
        self.alert_result.setStyleSheet('')
        self.ui.set_text(self.alert_result, '提醒仅在 MooPie 开启且 OpenD 可用时检查新报价。')
        self.ui.set_text(self.timeframe_summary, '周线与月线价位会在个股分析后显示。')
        self.clear_candidates('输入代码搜索单股，或留空查看默认 Watchlist。')
        self.ui.set_text(self.put_result, f'<h2>卖出 Put · Top {self.top_count.currentData()}</h2><p>先按 Filter 过滤，再按到期时长、担保成本、收益、风险或综合得分排序。</p><p style="color:#9aaab7">点击表头切换排序方向；设置页调整 Filter 和评分参数。</p>', 'setHtml')
        self.ui.set_text(self.trend_result, '<h2>走势分析</h2><p>均线 · RSI · MACD · 成交量</p><p style="color:#9aaab7">显示趋势、关键价位和改判条件。数据来自已完成日线。</p>', 'setHtml')
        if hasattr(self, 'export_button'): self.export_button.setEnabled(False)

    def clear_candidates(self, message):
        self.show_first_choice()
        self.candidate_table.setRowCount(0)
        self.candidate_table.order = []
        self.ui.set_text(self.ranking_title, f'候选排行榜 · Top {self.top_count.currentData()}', 'setText')
        self.ui.set_text(self.ranking_summary, '先过滤完整合约，再排序并选取 Top 数量。', 'setText')
        self.ui.set_text(self.data_state, '等待查询', 'setText')
        self.ui.set_text(self.ranking_message, message, 'setText'); self.ranking_message.show()
        self.ui.set_text(self.selection_hint, '点击选中合约，双击查看评分与筛选依据。', 'setText')
        self.details_button.setEnabled(False)

    def busy(self, value):
        if value: self.symbol_search.dismiss()
        for control in (self.symbol, self.port, self.put_button, self.trend_button, self.refresh_button, self.opend_button, self.watchlist_button, self.view_watchlist_action, self.add_watchlist_action, self.manage_watchlist_action, self.manage_button, self.home_button, self.radar_button, self.scope_list, self.directory_action, self.rules_button, self.top_count, self.candidate_table, self.overview_table, self.radar_table): control.setEnabled(not value)
        self.cancel_button.setVisible(value)

    def start(self, action, reuse=False, refresh=False, update=False, depth=False):
        if self.process is not None: return
        if hasattr(self, 'depth_timer'): self.depth_timer.stop()
        text = self.symbol.text().strip()
        try:
            code = None if action in ('sync-directory', 'overview', 'radar') else self.symbol_search.query_code()
            if action == 'add' and code is None: raise ValueError('请先输入要加入 Watchlist 的股票代码。')
        except ValueError as error:
            self.ui.set_text(self.status, str(error), 'setText'); return
        dataset = self.put_dataset if action == 'put' and reuse else None
        if reuse and dataset is None:
            self.ui.set_text(self.status, '没有可复用的数据，请先抓取。', 'setText'); return
        if action == 'put' and not reuse: self.put_dataset = None
        if action in ('overview','radar','put','trend'): self.main_tabs.setCurrentIndex(0)
        if action == 'overview': self.analysis_stack.setCurrentIndex(0)
        elif action == 'radar': self.analysis_stack.setCurrentIndex(2)
        elif action in ('put','trend'): self.analysis_stack.setCurrentIndex(1)
        if code: self.settings.setValue('symbol', code.removeprefix('US.'))
        self.action = action
        self.cancelled = False
        self.results.pop(action, None)
        if action == 'put':
            self.clear_candidates('正在用已有数据重新过滤和排序…' if reuse else '正在读取已保存的收盘结果…' if not(refresh or update) else '正在按交易时段读取行情并筛选合约…')
        if action in ('put','trend'): self.tabs.setCurrentIndex(0 if action == 'put' else 2)
        if action in ('put', 'trend'): self.ui.set_text(self.price_signal_result, '正在分析价格信号…', 'setPlainText')
        self.export_button.setEnabled(bool(self.results))
        if action in ('put','trend'): self.ui.set_text(self.panel(action), f'<h2>{esc(code or "Watchlist")}</h2><p>正在抓取和分析…</p>', 'setHtml')
        if action == 'overview': self.ui.set_text(self.overview_note, '正在读取 Watchlist 的价格和基本信息…', 'setText')
        if action == 'radar': self.ui.set_text(self.radar_note, '正在读取报价与已保存支撑区…', 'setText')
        if action == 'trend': self.order_book_result.set_message('正在读取买卖盘…' if depth else '点击左侧股票查看盘口。',
                                                                 language=self.ui.language, theme=self.ui.effective_theme)
        self.ui.set_text(self.status, '正在用已采集的数据重新过滤和排序，不重新抓取行情。' if reuse else
                            '正在刷新 OpenD 并保存数据库…' if refresh else '正在读取已保存的收盘结果；首次查询新股票时自动抓取…', 'setText')
        if action == 'add': self.ui.set_text(self.status, '正在核验证券基本资料并加入 Watchlist…', 'setText')
        if update: self.ui.set_text(self.status, '正在逐股检查缓存，只补抓缺失或过期股票，再合并 Top 20…', 'setText')
        if action == 'sync-directory': self.ui.set_text(self.status, '正在更新股票和 ETF 目录；不抓取期权或股票报价…', 'setText')
        if action == 'overview': self.ui.set_text(self.status, '正在读取 Watchlist 股票价格和基本信息…', 'setText')
        if action == 'radar': self.ui.set_text(self.status, '正在比较 Watchlist 报价与已保存支撑区…', 'setText')
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
        if depth: extra.append('--depth')
        if depth and not(refresh or update): extra.append('--update')
        if action in ('put','trend') and not(refresh or update or reuse or depth): extra.append('--saved')
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
        if lines: self.ui.set_text(self.status, lines[-1][-200:], 'setText')

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
                self.ui.set_text(self.status, '已停止操作；以当前保存的 Watchlist / 股票目录为准。', 'setText')
                self.release_process()
                return
            if self.action == 'put': self.clear_candidates('本次分析已取消，没有生成候选。')
            if self.action == 'overview': self.ui.set_text(self.overview_note, '本次价格更新已取消。', 'setText')
            if self.action == 'radar': self.ui.set_text(self.radar_note, '本次雷达更新已取消。', 'setText')
            self.ui.set_text(self.price_signal_result, '本次分析已取消，未生成价格信号。', 'setPlainText')
            if self.action in ('put','trend'):
                self.ui.set_text(self.panel(self.action), '本次分析已取消。可以重新输入股票并开始查询。', 'setPlainText')
            self.ui.set_text(self.status, '已取消；没有生成本次分析结果。', 'setText')
            self.release_process()
            return
        try:
            result = json.loads(self.result_path.read_text(encoding='utf-8')) if self.result_path.exists() else json.loads(self.output.decode('utf-8'))
            if exit_code or result.get('error'):
                raise ValueError(result.get('error', f'分析进程退出：{exit_code}'))
            if result.get('action') == 'directory_sync':
                skipped = len(result.get('skipped', []))
                self.ui.set_text(self.status, f'股票目录已更新：{result["securities"]} 条证券，{result["aliases"]} 个别名。'
                                    + (f'跳过 {skipped} 个格式不支持的代码。' if skipped else '')
                                    + '可输入公司名或代码选择。', 'setText')
            elif result.get('action') == 'watchlist_add':
                self.update_watchlist_label()
                self.ui.set_text(self.status, result['symbol'] + (' 已加入 Watchlist。' if result['added'] else ' 已在 Watchlist 中，没有重复添加。'), 'setText')
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
            self.ui.set_text(self.status, ('股票目录更新失败，保留原目录：' if self.action == 'sync-directory' else '未加入 Watchlist：') + message, 'setText')
            return
        self.results.pop(self.action, None)
        if self.action == 'overview':
            self.overview_table.setRowCount(0)
            self.ui.set_text(self.overview_note, '首页价格暂不可用：' + message, 'setText')
            self.ui.set_text(self.status, '首页价格未完成；请检查 OpenD 和行情权限。', 'setText')
            return
        if self.action == 'radar':
            self.radar_table.setRowCount(0)
            self.ui.set_text(self.radar_note, '买点雷达暂不可用：' + message, 'setText')
            self.ui.set_text(self.status, '买点雷达未完成；请检查 OpenD 和行情权限。', 'setText')
            return
        self.ui.set_text(self.price_signal_result, '本次查询未完成，未生成价格信号。', 'setPlainText')
        if self.action == 'put':
            self.clear_candidates('查询失败：' + message)
            self.ui.set_text(self.data_state, '本次查询失败', 'setText')
        self.export_button.setEnabled(bool(self.results))
        self.ui.set_text(self.panel(self.action), '分析未完成\n\n' + message + '\n\n没有缓存时会自动请求 OpenD。请确认 OpenD 已登录，并检查端口、股票代码和行情权限。', 'setPlainText')
        self.ui.set_text(self.status, '分析未完成；没有生成候选或走势结论。', 'setText')

    def display_overview(self, result):
        self.results['overview'] = result
        self.watchlist_quotes = {row['symbol']: row for row in result.get('rows', [])}
        self.update_watchlist_label()
        self.analysis_stack.setCurrentIndex(0)
        rows = result.get('rows', [])
        self.overview_table.setRowCount(len(rows))
        for index, row in enumerate(rows):
            change = row.get('change_pct')
            values = [row['name'], f'${row["price"]:,.2f}' if row.get('price') is not None else '—',
                      f'{change:+.2f}%' if change is not None else '—']
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column == 0: item.setData(Qt.ItemDataRole.UserRole, row['symbol'])
                item.setToolTip(f'{row["symbol"]} · 报价时间（纽约）：{row.get("update_time") or "未提供"}')
                color = self.change_color(change)
                if column in (1, 2) and color: item.setForeground(color)
                self.overview_table.setItem(index, column, item)
        self.ui.localize_table(self.overview_table)
        self.ui.set_text(self.overview_note,
            f'{len(rows)} 只股票 · 报价采集 {result.get("collected_at") or "时间未提供"}（UTC）。悬停查看各股报价时间；点击股票查看支撑阻力与买卖盘。', 'setText')
        self.ui.set_text(self.status, '首页已显示股价和涨跌；点击一只股票查看详细价位。', 'setText')
        self.export_button.setEnabled(True)

    def display_radar(self, result):
        self.results['radar'] = result
        rows = result.get('rows', [])
        self.watchlist_quotes = {row['symbol']: row for row in rows}
        self.update_watchlist_label()
        self.analysis_stack.setCurrentIndex(2)
        labels = {'watching': '等待进入支撑区', 'inside': '已进入支撑区 · 待确认',
                  'confirmed': '条件已出现 · 请复核', 'invalidated': '条件失效',
                  'paused': '提醒已暂停', 'inside_unarmed': '在支撑区 · 未提醒',
                  'above': '支撑区上方', 'below': '跌破支撑区',
                  'levels_unavailable': '暂无已保存支撑', 'quote_unavailable': '报价不可用'}
        if self.ui.language == 'en':
            labels = {'watching': 'Waiting for support', 'inside': 'Inside support · pending',
                      'confirmed': 'Condition observed · review', 'invalidated': 'Condition invalid',
                      'paused': 'Alert paused', 'inside_unarmed': 'Inside support · no alert',
                      'above': 'Above support', 'below': 'Below support',
                      'levels_unavailable': 'No saved support', 'quote_unavailable': 'Quote unavailable'}
        colors = {'inside': '#d5a031', 'confirmed': '#48d67f', 'invalidated': '#ff7777',
                  'inside_unarmed': '#d5a031', 'below': '#ff7777'} if self.ui.effective_theme == 'dark' else {
                  'inside': '#8e6000', 'confirmed': '#167a3e', 'invalidated': '#bd3030',
                  'inside_unarmed': '#8e6000', 'below': '#bd3030'}
        self.radar_table.setRowCount(len(rows))
        for index, row in enumerate(rows):
            low, high = row.get('support_low'), row.get('support_high')
            state = row['state']
            mode = (' · daily close' if self.ui.language == 'en' else ' · 日收盘') if row.get('alert_mode') == 'daily_close' else ''
            distance = row.get('distance_pct')
            values = [row.get('name') or row['symbol'],
                      f'${row["price"]:,.2f}' if row.get('price') is not None else '—',
                      f'${low:,.2f}–${high:,.2f}' if low is not None and high is not None else '—',
                      labels.get(state, state) + mode,
                      f'{distance:.2f}%' if distance is not None else '—']
            tooltip = (f'{row["symbol"]} · 报价 {row.get("update_time") or "时间未提供"}（纽约）'
                       f' · 支撑日线 {row.get("signal_as_of") or "暂无"}'
                       + (' · 提醒使用历史冻结区间' if row.get('stale_alert') else ''))
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column == 0: item.setData(Qt.ItemDataRole.UserRole, row['symbol'])
                item.setToolTip(tooltip)
                if column == 3 and state in colors: item.setForeground(QColor(colors[state]))
                self.radar_table.setItem(index, column, item)
        self.ui.localize_table(self.radar_table)
        self.ui.set_text(self.radar_note,
            f'{len(rows)} 只股票 · 报价采集 {result.get("collected_at") or "时间未提供"}（UTC）。支撑区来自已保存的日线；悬停看日期，点击股票复核实时详情。', 'setText')
        self.ui.set_text(self.status, '买点雷达已更新；状态仅供筛选，请在个股详情复核。', 'setText')
        self.export_button.setEnabled(True)

    def display(self, result):
        action = result['action']
        if action == 'overview':
            self.display_overview(result)
            return
        if action == 'radar':
            self.display_radar(result)
            return
        signals = dict(result.get('price_signals', {}))
        self.update_watchlist_label()
        self.ui.set_text(self.scope_heading,'分析 · '+result['symbol'].removeprefix('US.'))
        self.results[action] = result
        signal_view = signals_html(signals)
        if result.get('price_signal_saved_at'):
            signal_view += '<p>支撑阻力已保存到 SQLite · 计算时间 ' + esc(result['price_signal_saved_at']) + '（UTC）</p>'
        if result.get('saved_price_signal'):
            saved = result['saved_price_signal']
            signal_view += ('<hr><h3>上次保存的历史价位</h3><p>当前分析不可用；以下结果按当时的参考价与日线计算，可能已经过时。保存时间 '
                            + esc(saved['calculated_at']) + '（UTC）</p>'
                            + signals_html({saved['signal']['symbol']: saved['signal']}))
        if result.get('price_signal_storage_error'):
            signal_view += '<p>支撑阻力未能写入 SQLite：' + esc(result['price_signal_storage_error']) + '</p>'
        self.ui.set_text(self.price_signal_result, signal_view, 'setHtml')
        self.order_book_result.set_book(result.get('order_book'), result.get('quote'),
                                        language=self.ui.language, theme=self.ui.effective_theme,
                                        history=result.get('order_book_history', []))
        if action == 'trend':
            self.show_support_chart(result)
            self.show_detail_data_status(result)
            self.show_buy_plan_context(result)
            if result.get('order_book', {}).get('status') == 'ok':
                self.depth_timer.start()
        heading = f'<h2>{esc(result["symbol"])} · {"卖出 Put" if action == "put" else "走势"}</h2>'
        if action == 'trend':
            content = (''.join('<h2>' + esc(item['symbol']) + '</h2>' + trend_html(item) for item in result['items'])
                       if 'items' in result else trend_html(result) if result.get('trend', {}).get('status') == 'ok'
                       else '<p>日线分析不可用：' + esc(result.get('trend', {}).get('error', '数据不足')) + '</p>')
            quote = result.get('quote')
            if quote:
                content = (f'<p>最新价 ${quote["last_price"]:,.2f} · 报价时间 {esc(quote.get("update_time") or "未提供")}（纽约）</p>'
                           + content)
            if result.get('quote_error'):
                content += '<p>最新报价未取得：' + esc(result['quote_error']) + '</p>'
            content += ''.join('<p>查询失败：' + esc(item['symbol']) + ' · ' + esc(item['error']) + '</p>' for item in result.get('collection_errors', []))
        else:
            report = result['report']; ranked = report['ranked']
            self.show_first_choice(report)
            self.put_dataset = result.get('input_dataset')
            self.configuration = report.get('configuration', self.configuration)
            requested = report.get('top_n_requested', 10)
            if requested in (5, 10, 20):
                self.top_count.blockSignals(True)
                self.top_count.setCurrentIndex(self.top_count.findData(requested))
                self.top_count.blockSignals(False)
            shown = len(report.get('recommendations', []))
            self.ui.set_text(self.ranking_title, ('Watchlist · ' if result.get('query_scope') == 'watchlist' else '候选排行榜 · ') + f'Top {requested}', 'setText')
            self.ui.set_text(self.ranking_summary, f'检查 {report["total_contracts"]} 个合约 · {report["qualified_count"]} 个通过 Filter · 显示 {shown} 个', 'setText')
            self.ui.set_text(self.ranking_summary, 'Sort：'+sort_description(report['sort_order']), 'setToolTip')
            access = result.get('data_access', {})
            source = {'database': 'SQLite', 'OpenD': 'OpenD', 'mixed': '混合来源'}.get(access.get('source'), '已保存数据')
            self.ui.set_text(self.data_state, '● ' + source + ' · ' + report['session_date'], 'setText')
            if result.get('saved_view'):
                self.ui.set_text(self.data_state, '● SQLite · 收盘结果 · '+report['session_date'], 'setText')
            self.ui.set_text(self.data_state, '原始采集时间：' + result['collected_at'] + '\n' + access.get('note', '') + '\n离线重新排序不会刷新行情。', 'setToolTip')
            self.ranking_message.setVisible(not ranked)
            self.ui.set_text(self.ranking_message, '没有符合当前 Filter 的 Put。请查看「合约详情 / 筛选依据」，再自行决定是否调整条件。', 'setText')
            self.candidate_table.show_report(report)
            # The Put dataset already contains validated trend evidence. Populate
            # the tab immediately, rather than leaving a placeholder until a
            # second query fetches the same daily bars.
            trends = []
            rules = load_rules()
            for code, evidence in report.get('underlyings', {}).items():
                trends.append('<h2>'+esc(code)+'</h2>')
                if evidence.get('status') == 'ok':
                    view = dict(evidence, outlook=rules.describe_trend(evidence))
                    trends.append(trend_html(dict(trend=view,collected_at=result['collected_at'])))
                else:
                    series = next((s for s in (self.put_dataset or {}).get('daily_series',[]) if s['symbol']==code),{})
                    count = len(series.get('bars',[]))
                    reason = (f'历史日线不足：现有 {count} 根，完整趋势分析需要至少 205 根已完成日线。'
                              if count < 205 and not series.get('error') else str(evidence.get('error') or series.get('error') or '日线校验未通过'))
                    trends.append('<p>'+esc(reason)+'</p><p>暂不提供完整趋势判断；Put 排名仍遵循当前 Filter。</p>')
            if trends: self.ui.set_text(self.trend_result,''.join(trends),'setHtml')
            if not shown: self.select_candidate()
            self.tabs.setCurrentIndex(0)
        if action == 'trend':
            access = result.get('data_access', {})
            content += '<p>' + esc(access.get('note', '')) + ' · ' + esc(access.get('source', '已保存数据')) + '</p>'
            self.ui.set_text(self.trend_result, heading + content, 'setHtml')
            self.tabs.setCurrentIndex(2)
        failures = result.get('collection_errors', [])
        access = result.get('data_access', {})
        reuse_note = (f' · 复用 {len(access["reused_symbols"])} 只，抓取 {len(access["fetched_symbols"])} 只'
                      if 'reused_symbols' in access else '')
        self.ui.set_text(self.status, ('部分结果：' + '；'.join(item['symbol'] + ' 查询失败' for item in failures) if failures else '分析完成')
                            + reuse_note + ' · 数据采集：' + result['collected_at'] + ' · ' + access.get('note', '可导出数据、Filter、Sort 和规则证据'), 'setText')
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
            self.ui.set_text(self.selection_hint, f'已选 #{choice["overall_rank"]}  ·  {row["code"]}  ·  双击查看依据', 'setText')
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
        self.ui.set_text(self.put_result, content, 'setHtml')

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

    def change_top_count(self, _index):
        self.settings.setValue('put_top_n', self.top_count.currentData())
        self.apply_configuration(self.configuration)

    def apply_configuration(self, configuration):
        self.configuration = configuration
        self.settings.setValue('put_recommendation_configuration_v1', json.dumps(self.configuration))
        if self.put_dataset is not None: self.start('put', reuse=True)
        else:
            self.results.pop('put', None)
            self.clear_candidates('设置已保存。点击「筛选卖出 Put」抓取并分析。')
            self.ui.set_text(self.put_result, f'研究设置已保存：Top {self.top_count.currentData()}。点击“筛选卖出 Put”抓取并分析。', 'setPlainText')
            self.export_button.setEnabled(bool(self.results))
            self.ui.set_text(self.status, '设置已保存；尚未重新抓取行情。', 'setText')

    def cancel(self):
        if self.process:
            self.cancelled = True
            self.process.kill()

    def export(self):
        path, _ = QFileDialog.getSaveFileName(self, self.ui.translate('导出研究结果'), 'moomoo-research.json', 'JSON (*.json)')
        if path:
            try: Path(path).write_text(json.dumps(self.results, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
            except OSError as error: QMessageBox.warning(self, self.ui.translate('导出失败'), str(error))

    def closeEvent(self, event):
        self.alert_timer.stop()
        self.depth_timer.stop()
        if self.alert_process:
            self.alert_process.kill(); self.alert_process.waitForFinished(2000)
        if self.depth_process:
            self.depth_process.kill(); self.depth_process.waitForFinished(2000)
        self.symbol_search.shutdown()
        self.paper_panel.shutdown()
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
