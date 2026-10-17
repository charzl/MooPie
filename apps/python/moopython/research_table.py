"""Native Qt candidate list; values and ordering come from the rule report."""
from PySide6.QtCore import Qt, Signal, QRectF
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPalette
from PySide6.QtWidgets import (QAbstractItemView, QHeaderView, QStyle,
    QStyledItemDelegate, QStyleOptionViewItem, QTableWidget, QTableWidgetItem)


# Header, width, engine sort metric, preferred first-click direction.
COLUMNS = (
    ('#', 60, None, None),
    ('股票', 72, 'symbol', 'asc'),
    ('到期日', 110, 'expiration', 'asc'),
    ('天数', 54, 'days_to_expiry', 'asc'),
    ('行权价 / 担保', 120, 'strike', 'asc'),
    ('Bid / Ask', 100, 'bid', 'desc'),
    ('每张权利金', 100, 'premium_per_contract_before_costs', 'desc'),
    ('盈亏平衡', 100, 'breakeven_before_costs', 'desc'),
    ('日均毛收益', 112, 'daily_gross_return_pct', 'desc'),
    ('简单年化', 100, 'annualized_gross_return_pct', 'desc'),
    ('缓冲', 88, 'breakeven_buffer_pct', 'desc'),
    ('财报', 144, 'earnings_date', 'asc'),
    ('风险分', 94, 'risk_score', 'asc'),
    ('综合分', 130, 'composite_score', 'desc'),
)


class ValueDelegate(QStyledItemDelegate):
    def initStyleOption(self, option, index):
        super().initStyleOption(option, index)
        color = index.data(Qt.ItemDataRole.ForegroundRole)
        if color is not None:
            option.palette.setBrush(QPalette.ColorRole.HighlightedText, color)
        if index.column() == 0:
            option.textElideMode = Qt.TextElideMode.ElideNone


class ScoreDelegate(ValueDelegate):
    def paint(self, painter, option, index):
        value = index.data(Qt.ItemDataRole.UserRole)
        if value is None:
            return super().paint(painter, option, index)
        plain = QStyleOptionViewItem(option)
        self.initStyleOption(plain, index)
        plain.text = ''
        option.widget.style().drawControl(QStyle.ControlElement.CE_ItemViewItem, plain, painter, option.widget)
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(option.rect)
        track = QRectF(rect.left()+12, rect.center().y()-3, max(20, rect.width()-62), 6)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor('#2c313d')); painter.drawRoundedRect(track, 3, 3)
        fill = QRectF(track); fill.setWidth(track.width()*max(0, min(100, value))/100)
        gradient = QLinearGradient(track.topLeft(), track.topRight())
        gradient.setColorAt(0, QColor('#649fff')); gradient.setColorAt(1, QColor('#a28aff'))
        painter.setBrush(gradient); painter.drawRoundedRect(fill, 3, 3)
        painter.setPen(QColor('#e8ebf3'))
        painter.drawText(QRectF(rect.right()-43, rect.top(), 36, rect.height()),
                         Qt.AlignmentFlag.AlignCenter, f'{value:.0f}')
        painter.restore()


class CandidateTable(QTableWidget):
    sort_requested = Signal(str, str)

    def __init__(self, parent=None):
        super().__init__(0, len(COLUMNS), parent)
        self.setObjectName('candidateTable')
        self.setHorizontalHeaderLabels([c[0] for c in COLUMNS])
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setAlternatingRowColors(False)
        self.setShowGrid(False)
        self.setWordWrap(False)
        # Qt must never sort only the displayed Top N; ask the engine to rerank
        # the complete cached dataset instead.
        self.setSortingEnabled(False)
        self.verticalHeader().hide()
        self.verticalHeader().setDefaultSectionSize(58)
        header = self.horizontalHeader()
        header.setMinimumSectionSize(38)
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setStretchLastSection(True)
        header.setSectionsClickable(True)
        header.sectionClicked.connect(self.request_sort)
        self.order = []
        for index, (label, width, metric, _) in enumerate(COLUMNS):
            self.setColumnWidth(index, width)
            if metric:
                self.horizontalHeaderItem(index).setToolTip('点击对完整候选重新排序，再取所选 Top 数量；再次点击切换方向。')
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.horizontalHeaderItem(0).setToolTip('当前完整排序中的名次。')
        self.horizontalHeaderItem(4).setToolTip('按行权价数值排序；标准100股合约的担保成本与行权价同比例。')
        self.horizontalHeaderItem(5).setToolTip('点击按 Bid 数值排序；再次点击切换方向。Ask 作为参考显示。')
        self.horizontalHeaderItem(11).setToolTip('按列示的财报日期排序；日期缺失时始终排在最后，未验证状态继续保留。')
        self.setItemDelegateForColumn(13, ScoreDelegate(self))
        self.setMinimumHeight(160)
        self.setItemDelegate(ValueDelegate(self))

    def request_sort(self, column):
        _, _, metric, direction = COLUMNS[column]
        if metric is None: return
        if self.order and self.order[0][0] == metric:
            direction = 'desc' if self.order[0][1] == 'asc' else 'asc'
        self.sort_requested.emit(metric, direction)

    def show_report(self, report):
        self.blockSignals(True)
        self.clearContents()
        choices = report.get('recommendations', [])
        self.setRowCount(len(choices))
        self.order = report['sort_order']
        for col in range(len(COLUMNS)):
            label, _, metric, _ = COLUMNS[col]
            active = bool(self.order and self.order[0][0] == metric)
            suffix = (' ↑' if self.order[0][1] == 'asc' else ' ↓') if active else ''
            self.horizontalHeaderItem(col).setText(label + suffix)
        ranked = {row['code']: row for row in report['ranked']}
        for index, choice in enumerate(choices):
            row = ranked[choice['code']]; m = row['metrics']
            earnings = row.get('earnings') or {}
            known = bool(m['earnings_known'])
            days = m['days_expiry_before_earnings']
            event_score = next(c['score'] for c in row['scoring']['components'] if c['id'] == 'earnings')
            event = earnings.get('date', '未知')
            if not known: event += '\n未验证'
            elif days <= 0: event += '\n到期前 / 同日'
            else: event += f'\n到期后 {int(days)} 天'
            cells = [str(choice['overall_rank']), row['symbol'].removeprefix('US.'), row['expiration'],
                     str(m['days_to_expiry']), f'${m["strike"]:,.2f}\n${m["cash_collateral"]:,.0f}',
                     f'${m["bid"]:.2f} Bid\n${m["ask"]:.2f} Ask', f'${m["premium_per_contract_before_costs"]:,.0f}',
                     f'${m["breakeven_before_costs"]:,.2f}', f'{m["daily_gross_return_pct"]:.4f}%',
                     f'{m["annualized_gross_return_pct"]:.2f}%', f'{m["breakeven_buffer_pct"]:.2f}%',
                     event, f'{m["risk_score"]:.2f}', f'{m["composite_score"]:.2f}']
            for col, text in enumerate(cells):
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter if col == 0 else
                                      Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
                item.setToolTip(row['code'])
                if col == 1:
                    font = item.font(); font.setBold(True); item.setFont(font)
                if col == 5:
                    item.setToolTip(f'Bid ${m["bid"]:.2f} / Ask ${m["ask"]:.2f}\n合约快照：{row["snapshot_update_time"]}（纽约时间）')
                if col in (8, 9):
                    item.setForeground(QColor('#80adff'))
                    item.setToolTip('完整保留 Bid 权利金时的毛收益比较，未扣费用；不是实际到账或预期净收益。')
                if col == 10:
                    item.setToolTip('现价到费用前盈亏平衡价的距离，由规则引擎计算；不代表不会跌破。')
                if col == 11:
                    item.setForeground(QColor('#e9b45f' if not known or event_score > 0 else '#949bad'))
                    item.setToolTip('券商日历列示日期；未验证不等于没有财报。' + (f'\n日期：{earnings["date"]}' if earnings else ''))
                if col == 12: item.setToolTip('风险分 0–100，越低越好；不是亏损概率。')
                if col == 13:
                    item.setData(Qt.ItemDataRole.UserRole, m['composite_score'])
                    item.setToolTip(f'综合分 {m["composite_score"]:.2f} / 100，越高越好；使用当前收益和风险权重。')
                self.setItem(index, col, item)
        self.blockSignals(False)
        self.scrollToTop()
        if choices: self.selectRow(0)
