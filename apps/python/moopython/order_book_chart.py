"""Compact Qt chart for nearby visible bid and ask price ranges."""
from math import isfinite

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QComboBox, QFrame, QHBoxLayout, QLabel, QProgressBar,
                               QScrollArea, QVBoxLayout, QWidget)

from .order_book import (BOOK_BUCKET_RANGE_FRACTION, BOOK_BUCKETS_PER_SIDE,
                         auto_bucket_width, quote_reference,
                         visible_price_buckets, visible_price_zones, visible_value_ratio)


def price_range(zone):
    low, high = zone['low'], zone['high']
    return f'${low:,.2f}' if low == high else f'${low:,.2f}–${high:,.2f}'


def bucket_label(bucket):
    if bucket['kind'] == 'below': return f'<${bucket["high"]:,.2f}'
    if bucket['kind'] == 'above': return f'≥${bucket["low"]:,.2f}'
    label = f'${bucket["low"]:,.2f}–<${bucket["high"]:,.2f}'
    if 'percent_low' in bucket:
        def percent(value): return f'{value:+g}%' if value else '0%'
        return f'{percent(bucket["percent_low"])}–{percent(bucket["percent_high"])} · {label}'
    return label


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
        self.bucket_width_choice = 0
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

    def _value_ratio(self, book, *, english, theme):
        self._label('Visible bid / ask value ratio' if english else '可见买卖盘金额比例', large=True)
        ratio = visible_value_ratio(book)
        if ratio['status'] != 'ok':
            self._label('Ratio unavailable: one side has no visible value.' if english else
                        '比例不可用：本次返回的一侧没有可见挂单金额。', muted=True)
            return
        self._label((f'Bid ${ratio["bid_value"]:,.0f} ({ratio["bid_share"]:.1%}) · '
                     f'Ask ${ratio["ask_value"]:,.0f} ({ratio["ask_share"]:.1%}) · '
                     f'Bid / Ask {ratio["bid_to_ask"]:.2f}:1') if english else
                    (f'买盘 ${ratio["bid_value"]:,.0f}（{ratio["bid_share"]:.1%}） · '
                     f'卖盘 ${ratio["ask_value"]:,.0f}（{ratio["ask_share"]:.1%}） · '
                     f'买／卖 {ratio["bid_to_ask"]:.2f}:1'))
        bar = QProgressBar()
        bar.setRange(0, 1000)
        bar.setValue(round(ratio['bid_share'] * 1000))
        bar.setTextVisible(False)
        bar.setFixedHeight(19)
        green = '#48d67f' if theme == 'dark' else '#167a3e'
        red = '#ff7777' if theme == 'dark' else '#bd3030'
        bar.setStyleSheet(f'QProgressBar{{border:0;border-radius:5px;background:{red};}}'
                          f'QProgressBar::chunk{{background:{green};border-radius:5px;}}')
        bar.setAccessibleName('Visible bid value share' if english else '可见买盘金额占比')
        self.body.addWidget(bar)
        self._label('Calculated from all returned visible levels, not just nearby ranges. Orders may be cancelled; this is not traded money flow.' if english else
                    '按本次返回的全部可见档位计算，不只看最近区间；挂单可撤销，这不是已成交资金流向。', muted=True)

    def _zone_summary(self, zone, title, reference_name, color, *, english):
        if zone is None:
            self._label(title + (' · unavailable' if english else ' · 暂无可见挂单'))
            return
        label = self._label(f'{title}  {price_range(zone)}', large=True)
        label.setStyleSheet(f'color:{color};font-size:18px;font-weight:bold;')
        distance = (f' · {zone["distance_pct"]:.2f}% from {reference_name}' if english else
                    f' · 距{reference_name} {zone["distance_pct"]:.2f}%') if zone['distance_pct'] is not None else ''
        amount = zone.get('notional')
        amount_note = (f' · estimated limit-order value ≈${amount:,.0f}' if english else
                       f' · 按挂单价估算约 ${amount:,.0f}') if amount is not None else ''
        self._label((f'{zone["volume"]:,.0f} visible shares · {zone["levels"]} merged levels' if english else
                     f'可见 {zone["volume"]:,.0f} 股 · 合并 {zone["levels"]} 档') + amount_note + distance)

    def _bucket_summary(self, bucket, title, color, *, english):
        if bucket is None:
            self._label(title + (' · unavailable' if english else ' · 暂无可见挂单'))
            return
        label = self._label(f'{title}  {bucket_label(bucket)}', large=True)
        label.setStyleSheet(f'color:{color};font-size:18px;font-weight:bold;')
        self._label((f'{bucket["volume"]:,.0f} visible shares · {bucket["levels"]} levels · '
                     f'limit-order value ≈${bucket["notional"]:,.0f}' if english else
                     f'可见 {bucket["volume"]:,.0f} 股 · {bucket["levels"]} 档 · '
                     f'按挂单价估算约 ${bucket["notional"]:,.0f}'))

    def _bucket_width_changed(self, index):
        choice = self.bucket_width.currentData()
        if choice is None or choice == self.bucket_width_choice:
            return
        self.bucket_width_choice = choice
        self.set_book(self.book, self.quote, language=self.language, theme=self.theme)

    def _bucket_section(self, buckets, *, english, theme):
        self._label('Visible shares by price bucket' if english else '各价格桶的可见挂单股数', large=True)
        visible = {side: [item for item in buckets[side] if item['volume'] > 0]
                   for side in ('bids', 'asks')}
        maximum = max((item['volume'] for side in ('bids', 'asks') for item in visible[side]), default=1)
        for side, color in (('bids', '#48d67f' if theme == 'dark' else '#167a3e'),
                            ('asks', '#ff7777' if theme == 'dark' else '#bd3030')):
            if not visible[side]:
                continue
            self._label(('Bids' if side == 'bids' else 'Asks') if english else
                        ('买盘' if side == 'bids' else '卖盘'))
            for bucket in visible[side]:
                line = QHBoxLayout()
                label = QLabel(bucket_label(bucket)); label.setMinimumWidth(150)
                bar = QProgressBar(); bar.setRange(0, max(1, int(maximum)))
                bar.setValue(int(bucket['volume'])); bar.setTextVisible(False); bar.setFixedHeight(16)
                track = '#303542' if theme == 'dark' else '#dce4ed'
                bar.setStyleSheet(f'QProgressBar{{border:0;border-radius:5px;background:{track};}}'
                                  f'QProgressBar::chunk{{background:{color};border-radius:5px;}}')
                amount = QLabel((f'{bucket["volume"]:,.0f} shares' if english else
                                 f'{bucket["volume"]:,.0f} 股') + f'\n≈${bucket["notional"]:,.0f}')
                amount.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                amount.setMinimumWidth(94)
                line.addWidget(label); line.addWidget(bar, 1); line.addWidget(amount)
                self.body.addLayout(line)
        if not visible['bids'] and not visible['asks']:
            self._label('No visible levels' if english else '暂无可见档位')

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
        prices = [row['price'] for side in ('bids', 'asks') for row in book.get(side, [])]
        bucket_reference = price or (max(prices) if prices else None)
        width = self.bucket_width_choice or (auto_bucket_width(bucket_reference) if bucket_reference else 1)
        controls = QHBoxLayout()
        controls.addWidget(QLabel('Bucket width' if english else '价格桶宽'))
        self.bucket_width = QComboBox()
        self.bucket_width.setAccessibleName('Bucket width' if english else '价格桶宽')
        self.bucket_width.addItem('Auto 5%' if english else '自动 5%', 0)
        for option in (1, 2, 5, 10, 20, 50, 100, 200):
            self.bucket_width.addItem(f'${option}', option)
        self.bucket_width.setCurrentIndex(self.bucket_width.findData(self.bucket_width_choice))
        self.bucket_width.currentIndexChanged.connect(self._bucket_width_changed)
        controls.addWidget(self.bucket_width); controls.addStretch()
        self.body.addLayout(controls)
        auto_mode = self.bucket_width_choice == 0 and price is not None
        buckets = visible_price_buckets(book, width, price, anchor_to_reference=auto_mode)
        if price is not None:
            if auto_mode:
                detail = (f'Auto: {BOOK_BUCKETS_PER_SIDE} buckets per side, 5% each '
                          f'(≈${width:g}); detail ${buckets["lower"]:,.2f}–${buckets["upper"]:,.2f}. '
                          'Outer ranges are grouped separately.' if english else
                          f'自动分桶：参考价上下各 {BOOK_BUCKETS_PER_SIDE} 桶，每桶 5%（约 ${width:g}）；'
                          f'详细范围 ${buckets["lower"]:,.2f}–${buckets["upper"]:,.2f}，范围外各合并一桶。')
            else:
                detail = (f'${width:g} per bucket · detail within ±{BOOK_BUCKET_RANGE_FRACTION:.0%} '
                          f'(${buckets["lower"]:,.2f}–${buckets["upper"]:,.2f}); '
                          'each outer range is one bucket.' if english else
                          f'每桶 ${width:g} · 详细范围为参考价上下各 {BOOK_BUCKET_RANGE_FRACTION:.0%} '
                          f'（${buckets["lower"]:,.2f}–${buckets["upper"]:,.2f}）；范围外各合并一桶。')
            self._label(detail, muted=True)
        else:
            self._label((f'${width:g} per bucket · quote unavailable, so no outer range cutoff.' if english else
                         f'每桶 ${width:g} · 参考价不可用，暂不合并范围外价位。'), muted=True)
        for side, color in (('bids', '#48d67f' if theme == 'dark' else '#167a3e'),
                            ('asks', '#ff7777' if theme == 'dark' else '#bd3030')):
            most = max((bucket for bucket in buckets[side]
                        if bucket['kind'] == 'normal' and bucket['volume'] > 0),
                       key=lambda bucket: bucket['volume'], default=None)
            title = ('Largest bid bucket within detail range' if side == 'bids' else
                     'Largest ask bucket within detail range') if english else (
                '范围内买盘挂单最多的价格桶' if side == 'bids' else '范围内卖盘挂单最多的价格桶')
            self._bucket_summary(most, title, color, english=english)
        self._value_ratio(book, english=english, theme=theme)
        self._bucket_section(buckets, english=english, theme=theme)
        zones = visible_price_zones(book, price)
        strongest = {side: sorted(zones[side], key=lambda zone: (-zone['volume'],
                         zone['distance_pct'] if zone['distance_pct'] is not None else 0))[:3]
                     for side in ('bids', 'asks')}
        self._volume_section('Largest ranges by visible shares in returned depth' if english else
                             '已返回档位中挂单股数最多的区间', strongest, english=english, theme=theme)
        for side, color in (('bids', '#48d67f' if theme == 'dark' else '#167a3e'),
                            ('asks', '#ff7777' if theme == 'dark' else '#bd3030')):
            title = ('Nearest visible bid range' if side == 'bids' else 'Nearest visible ask range') if english else (
                '最近买盘区间' if side == 'bids' else '最近卖盘区间')
            self._zone_summary(zones[side][0] if zones[side] else None, title,
                               labels[reference['session']], color, english=english)
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
