"""Compact Qt chart for nearby visible bid and ask price ranges."""
from math import isfinite

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QProgressBar,
                               QScrollArea, QVBoxLayout, QWidget)

from .order_book import quote_reference, visible_price_zones


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

    def _volume_section(self, title, selected, *, english, theme):
        self._label(title, large=True)
        visible = [zone['volume'] for side in ('bids', 'asks') for zone in selected[side]]
        maximum = max(visible, default=1)
        for side, color in (('bids', '#48d67f' if theme == 'dark' else '#167a3e'),
                            ('asks', '#ff7777' if theme == 'dark' else '#bd3030')):
            self._label(('Bids' if side == 'bids' else 'Asks') if english else ('买盘' if side == 'bids' else '卖盘'))
            for zone in selected[side]:
                line = QHBoxLayout()
                label = price_range(zone)
                if zone['distance_pct'] is not None:
                    label += f'  ({zone["distance_pct"]:.2f}%)'
                range_label = QLabel(label); range_label.setMinimumWidth(135)
                bar = QProgressBar(); bar.setRange(0, max(1, int(maximum)))
                bar.setValue(int(zone['volume'])); bar.setTextVisible(False)
                bar.setFixedHeight(16)
                track = '#303542' if theme == 'dark' else '#dce4ed'
                bar.setStyleSheet(f'QProgressBar{{border:0;border-radius:5px;background:{track};}}'
                                  f'QProgressBar::chunk{{background:{color};border-radius:5px;}}')
                amount = zone.get('notional')
                volume_text = f'{zone["volume"]:,.0f} shares' if english else f'{zone["volume"]:,.0f} 股'
                if amount is not None:
                    volume_text += f'\n≈${amount:,.0f}'
                volume = QLabel(volume_text)
                volume.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                volume.setMinimumWidth(94)
                line.addWidget(range_label); line.addWidget(bar, 1); line.addWidget(volume)
                self.body.addLayout(line)
        if not visible: self._label('No visible levels' if english else '暂无可见档位')

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
        reference = quote_reference(quote)
        price = reference['price']
        labels = ({'regular': 'regular-session last price', 'after': 'after-hours price',
                   'pre': 'pre-market price', 'overnight': 'overnight price'} if english else
                  {'regular': '常规时段最新成交价', 'after': '盘后参考价',
                   'pre': '盘前参考价', 'overnight': '夜盘参考价'})
        last = (quote or {}).get('last_price')
        if price is not None:
            comparison = f'{labels[reference["session"]]} ${price:,.2f}'
            if reference['session'] != 'regular' and type(last) in (int, float) and isfinite(last) and last > 0:
                comparison = (f'Regular-session last price ${last:,.2f} · ' if english else
                              f'常规时段 last_price ${last:,.2f} · ') + comparison
            self._label(comparison)
        zones = visible_price_zones(book, price)
        for side, color in (('bids', '#48d67f' if theme == 'dark' else '#167a3e'),
                            ('asks', '#ff7777' if theme == 'dark' else '#bd3030')):
            nearest = zones[side][0] if zones[side] else None
            title = ('Nearest visible bid range' if side == 'bids' else 'Nearest visible ask range') if english else (
                '最近买盘区间' if side == 'bids' else '最近卖盘区间')
            if nearest:
                reference_name = labels[reference['session']]
                distance = (f' · {nearest["distance_pct"]:.2f}% from {reference_name}' if english else
                            f' · 距{reference_name} {nearest["distance_pct"]:.2f}%') if nearest['distance_pct'] is not None else ''
                value = f'{title}  {price_range(nearest)}'
                label = self._label(value, large=True)
                label.setStyleSheet(f'color:{color};font-size:18px;font-weight:bold;')
                amount = nearest.get('notional')
                amount_note = (f' · estimated limit-order value ≈${amount:,.0f}' if english else
                               f' · 按挂单价估算约 ${amount:,.0f}') if amount is not None else ''
                self._label((f'{nearest["volume"]:,.0f} visible shares · {nearest["levels"]} merged levels' if english else
                             f'可见 {nearest["volume"]:,.0f} 股 · 合并 {nearest["levels"]} 档') + amount_note + distance)
            else:
                self._label(title + (' · unavailable' if english else ' · 暂无可见挂单'))
        strongest = {side: sorted(zones[side], key=lambda zone: (-zone['volume'],
                         zone['distance_pct'] if zone['distance_pct'] is not None else 0))[:3]
                     for side in ('bids', 'asks')}
        self._volume_section('Largest ranges by visible shares in returned depth' if english else
                             '已返回档位中挂单股数最多的区间', strongest, english=english, theme=theme)
        self._volume_section('Nearby visible shares by merged price range' if english else
                             '邻近价位合并后的挂单股数',
                             {side: zones[side][:4] for side in ('bids', 'asks')}, english=english, theme=theme)
        self._label('Bars show shares, not order count or traded value. Dollar figures sum each visible limit price × shares; no execution is implied.' if english else
                    '柱长表示挂单股数，不是订单笔数或成交金额。美元数为各档挂单价 × 股数的合计，仅作名义金额参考。', muted=True)
        collected = book.get('collected_at') or ('Unavailable' if english else '未提供')
        self._label(('Collected (UTC): ' if english else '盘口采集（UTC）：') + collected, muted=True)
        if (quote or {}).get('update_time'):
            self._label(('Snapshot update (New York): ' if english else '快照更新时间（纽约）：')
                        + str(quote['update_time']), muted=True)
        if price and ((zones['bids'] and zones['bids'][0]['low'] > price) or
                      (zones['asks'] and zones['asks'][0]['high'] < price)):
            self._label('The selected trade price is outside the nearest book ranges; quote and depth may differ in time or session.' if english else
                        '所选时段参考价落在最近盘口区间外；报价与盘口可能来自不同时间或时段。', muted=True)
        if not book.get('bid_server_time') or not book.get('ask_server_time'):
            self._label('Exchange update time unavailable; freshness cannot be verified.' if english else
                        '交易所更新时间未提供，无法核对盘口时效。', muted=True)
        bid_count = book.get('returned_bids', len(book.get('bids', [])))
        ask_count = book.get('returned_asks', len(book.get('asks', [])))
        self._label((f'Requested up to {book["depth"]} levels per side; received {bid_count} bid / {ask_count} ask levels. Only this feed; orders can be cancelled.' if english else
                     f'每侧请求最多 {book["depth"]} 档，实际返回买 {bid_count} / 卖 {ask_count} 档。只统计当前行情源可见挂单；挂单可撤销，并非全市场买卖总量。'), muted=True)
        self.body.addStretch()
