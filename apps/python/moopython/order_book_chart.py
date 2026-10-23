"""Compact Qt chart for nearby visible bid and ask price ranges."""
from math import isfinite

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QProgressBar,
                               QScrollArea, QVBoxLayout, QWidget)

from .order_book import visible_price_zones


def price_range(zone):
    low, high = zone['low'], zone['high']
    return f'${low:,.2f}' if low == high else f'${low:,.2f}–${high:,.2f}'


class OrderBookChart(QScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.content = QWidget()
        self.body = QVBoxLayout(self.content)
        self.body.setContentsMargins(16, 14, 16, 14)
        self.body.setSpacing(8)
        self.setWidget(self.content)
        self.book = None
        self.quote = None
        self.language = 'zh'
        self.theme = 'dark'
        self.set_book(None)

    def _clear(self):
        def remove(layout):
            while layout.count():
                item = layout.takeAt(0)
                if item.widget():
                    item.widget().hide()
                    item.widget().deleteLater()
                elif item.layout():
                    remove(item.layout())
                    item.layout().deleteLater()
        remove(self.body)

    def _label(self, text, *, large=False, muted=False):
        label = QLabel(text)
        label.setWordWrap(True)
        label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        if large: label.setStyleSheet('font-size:18px;font-weight:bold;')
        elif muted: label.setStyleSheet('color:#949bad;font-size:11px;' if self.theme == 'dark'
                                         else 'color:#58677b;font-size:11px;')
        self.body.addWidget(label)
        return label

    def set_message(self, message, *, language='zh', theme='dark'):
        self.book = None
        self.quote = None
        self.language = language
        self.theme = theme
        self._clear()
        self._label('Visible Order Book' if language == 'en' else '当前可见买卖盘', large=True)
        self._label(message)
        self.body.addStretch()

    def set_book(self, book, quote=None, *, language='zh', theme='dark'):
        self.book, self.quote, self.language, self.theme = book, quote, language, theme
        self._clear()
        english = language == 'en'
        self._label('Visible Order Book' if english else '当前可见买卖盘', large=True)
        if not book or book.get('status') != 'ok':
            reason = (book or {}).get('reason', 'Not loaded' if english else '尚未查询')
            self._label(('Unavailable: ' if english else '盘口不可用：') + str(reason))
            self.body.addStretch()
            return
        price = (quote or {}).get('last_price')
        if type(price) not in (int, float) or not isfinite(price) or price <= 0:
            price = None
        zones = visible_price_zones(book, price)
        for side, color in (('bids', '#48d67f' if theme == 'dark' else '#167a3e'),
                            ('asks', '#ff7777' if theme == 'dark' else '#bd3030')):
            nearest = zones[side][0] if zones[side] else None
            title = ('Nearest visible bid range' if side == 'bids' else 'Nearest visible ask range') if english else (
                '最近买盘区间' if side == 'bids' else '最近卖盘区间')
            if nearest:
                distance = (f' · {nearest["distance_pct"]:.2f}% from price' if english else
                            f' · 距现价 {nearest["distance_pct"]:.2f}%') if nearest['distance_pct'] is not None else ''
                value = f'{title}  {price_range(nearest)}'
                label = self._label(value, large=True)
                label.setStyleSheet(f'color:{color};font-size:18px;font-weight:bold;')
                self._label((f'{nearest["volume"]:,.0f} visible shares · {nearest["levels"]} merged levels' if english else
                             f'可见 {nearest["volume"]:,.0f} 股 · 合并 {nearest["levels"]} 档') + distance)
            else:
                self._label(title + (' · unavailable' if english else ' · 暂无可见挂单'))
        self._label('Nearby volume by merged price range' if english else '邻近价位合并后的挂单量', large=True)
        visible = [zone['volume'] for side in ('bids', 'asks') for zone in zones[side][:4]]
        maximum = max(visible, default=1)
        for side, color in (('bids', '#48d67f' if theme == 'dark' else '#167a3e'),
                            ('asks', '#ff7777' if theme == 'dark' else '#bd3030')):
            title = ('Bids' if side == 'bids' else 'Asks') if english else ('买盘' if side == 'bids' else '卖盘')
            self._label(title)
            for zone in zones[side][:4]:
                line = QHBoxLayout()
                range_label = QLabel(price_range(zone)); range_label.setMinimumWidth(135)
                bar = QProgressBar(); bar.setRange(0, max(1, int(maximum)))
                bar.setValue(int(zone['volume'])); bar.setTextVisible(False)
                bar.setFixedHeight(16)
                track = '#303542' if theme == 'dark' else '#dce4ed'
                bar.setStyleSheet(f'QProgressBar{{border:0;border-radius:5px;background:{track};}}'
                                  f'QProgressBar::chunk{{background:{color};border-radius:5px;}}')
                volume = QLabel(f'{zone["volume"]:,.0f}')
                volume.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                volume.setMinimumWidth(65)
                line.addWidget(range_label); line.addWidget(bar, 1); line.addWidget(volume)
                self.body.addLayout(line)
        if not visible: self._label('No visible levels' if english else '暂无可见档位')
        collected = book.get('collected_at') or ('Unavailable' if english else '未提供')
        self._label(('Collected (UTC): ' if english else '盘口采集（UTC）：') + collected, muted=True)
        if (quote or {}).get('update_time'):
            self._label(('Quote time (New York): ' if english else '最新价时间（纽约）：')
                        + str(quote['update_time']), muted=True)
        if price and ((zones['bids'] and zones['bids'][0]['low'] > price) or
                      (zones['asks'] and zones['asks'][0]['high'] < price)):
            self._label('Quote and order book may be out of sync.' if english else
                        '报价与盘口价位可能不同步，请核对更新时间。', muted=True)
        if not book.get('bid_server_time') or not book.get('ask_server_time'):
            self._label('Exchange update time unavailable; freshness cannot be verified.' if english else
                        '交易所更新时间未提供，无法核对盘口时效。', muted=True)
        self._label((f'Only the top {book["depth"]} visible levels from this feed; orders can be cancelled.' if english else
                     f'仅统计当前行情源可见的前 {book["depth"]} 档挂单；挂单可撤销，并非全市场买卖总量。'), muted=True)
        self.body.addStretch()
