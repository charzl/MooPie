"""Read and describe visible order-book depth for one stock on demand."""
from datetime import datetime, time, timezone
from decimal import Decimal, ROUND_FLOOR
from math import isfinite
from zoneinfo import ZoneInfo

from .market_collection import opend_connection, us_symbols


# Temporary display range around the session-matched quote; adjust as the UI evolves.
BOOK_BUCKET_RANGE_FRACTION = 0.30
BOOK_BUCKETS_PER_SIDE = 6


def auto_bucket_width(reference_price):
    """Divide either side of the 30% reference range into six exact 5% bands."""
    if type(reference_price) not in (int, float) or not isfinite(reference_price) or reference_price <= 0:
        raise ValueError('A positive reference price is required')
    return float(Decimal(str(reference_price)) * Decimal(str(BOOK_BUCKET_RANGE_FRACTION)) /
                 BOOK_BUCKETS_PER_SIDE)


def visible_price_buckets(book, width, reference_price=None, *, anchor_to_reference=False):
    """Group visible shares in reference-anchored or fixed-dollar bins plus tails."""
    if type(width) not in (int, float) or not isfinite(width) or width <= 0:
        raise ValueError('Bucket width must be positive')
    if not book or book.get('status') != 'ok':
        return dict(bids=[], asks=[], width=width, lower=None, upper=None)
    valid_reference = (type(reference_price) in (int, float) and isfinite(reference_price)
                       and reference_price > 0)
    if anchor_to_reference and not valid_reference:
        raise ValueError('Reference-anchored buckets require a positive reference price')
    decimal_reference = Decimal(str(reference_price)) if valid_reference else None
    fraction = Decimal(str(BOOK_BUCKET_RANGE_FRACTION))
    decimal_lower = decimal_reference * (1 - fraction) if valid_reference else None
    decimal_upper = decimal_reference * (1 + fraction) if valid_reference else None
    lower = float(decimal_lower) if decimal_lower is not None else None
    upper = float(decimal_upper) if decimal_upper is not None else None
    decimal_width = Decimal(str(width))

    def normal_bucket(index):
        raw_low = ((decimal_reference if anchor_to_reference else Decimal(0))
                   + index * decimal_width)
        raw_high = raw_low + decimal_width
        low = max(raw_low, decimal_lower) if decimal_lower is not None else raw_low
        high = min(raw_high, decimal_upper) if decimal_upper is not None else raw_high
        item = dict(kind='normal', low=float(low), high=float(high),
                    volume=0, notional=0, levels=0)
        if anchor_to_reference:
            step = BOOK_BUCKET_RANGE_FRACTION * 100 / BOOK_BUCKETS_PER_SIDE
            item.update(percent_low=index * step, percent_high=(index + 1) * step)
        return item

    sides = {}
    for side in ('bids', 'asks'):
        grouped = {}
        if anchor_to_reference:
            indices = (range(-BOOK_BUCKETS_PER_SIDE, 0) if side == 'bids' else
                       range(0, BOOK_BUCKETS_PER_SIDE))
            grouped.update({('normal', index): normal_bucket(index) for index in indices})
        for row in book.get(side, []):
            price, volume = row['price'], row['volume']
            if volume <= 0:
                continue
            decimal_price = Decimal(str(price))
            if decimal_lower is not None and decimal_price < decimal_lower:
                key, kind, low, high = ('below',), 'below', None, lower
            elif decimal_upper is not None and decimal_price >= decimal_upper:
                key, kind, low, high = ('above',), 'above', upper, None
            else:
                anchor = decimal_reference if anchor_to_reference else Decimal(0)
                index = int(((decimal_price - anchor) / decimal_width).to_integral_value(rounding=ROUND_FLOOR))
                key, kind = ('normal', index), 'normal'
                low = high = None
            if kind == 'normal':
                bucket = grouped.setdefault(key, normal_bucket(index))
            else:
                bucket = grouped.setdefault(key, dict(kind=kind, low=low, high=high,
                                                       volume=0, notional=0, levels=0))
            bucket['volume'] += volume
            bucket['notional'] += price * volume
            bucket['levels'] += 1
        items = list(grouped.values())
        for item in items:
            item['notional'] = round(item['notional'], 2)
        items.sort(key=lambda item: item['high'] if item['high'] is not None else float('inf'),
                   reverse=side == 'bids')
        sides[side] = items
    return dict(**sides, width=width, lower=lower, upper=upper,
                anchor_to_reference=anchor_to_reference)


def unavailable(symbol, reason):
    return dict(symbol=symbol, status='unavailable', reason=str(reason))


def quote_reference(quote):
    """Choose a session-matched trade price for comparing with visible depth."""
    quote = quote or {}
    stamp = quote.get('update_time')
    session = 'regular'
    if isinstance(stamp, str):
        try:
            observed = datetime.fromisoformat(stamp)
            if observed.tzinfo is not None:
                observed = observed.astimezone(ZoneInfo('America/New_York'))
            clock = observed.time()
            if time(16) <= clock < time(20): session = 'after'
            elif clock >= time(20) or clock < time(4): session = 'overnight'
            elif clock < time(9, 30): session = 'pre'
        except ValueError:
            pass
    fields = {'regular': 'last_price', 'after': 'after_price',
              'overnight': 'overnight_price', 'pre': 'pre_price'}
    field = fields[session]
    price = quote.get(field)
    if type(price) not in (int, float) or not isfinite(price) or price <= 0:
        field, session, price = 'last_price', 'regular', quote.get('last_price')
    if type(price) not in (int, float) or not isfinite(price) or price <= 0:
        price = None
    return dict(price=price, field=field, session=session, update_time=stamp)


def read_order_book(symbol, port=11111, depth=60):
    code = us_symbols([symbol])[0]
    if type(depth) is not int or not 1 <= depth <= 60:
        raise ValueError('Order-book depth must be 1–60')
    try:
        with opend_connection(port=port) as service:
            sdk, context = service.sdk, service.context
            ret, response = context.subscribe([code], [sdk.SubType.ORDER_BOOK], subscribe_push=False)
            if ret != sdk.RET_OK: raise RuntimeError('盘口订阅失败：' + str(response))
            ret, response = context.get_order_book(code, num=depth)
            if ret != sdk.RET_OK: raise RuntimeError('盘口读取失败：' + str(response))
        if response.get('code') != code: raise ValueError('盘口返回的股票代码不匹配')
        sides = {}
        for source, target in (('Bid', 'bids'), ('Ask', 'asks')):
            levels = []
            for row in response.get(source, [])[:depth]:
                price, volume = row[:2]
                if (type(price) not in (int, float) or type(volume) not in (int, float) or
                        not isfinite(price) or not isfinite(volume) or price <= 0 or volume < 0):
                    raise ValueError('盘口价位或数量无效')
                levels.append(dict(price=price, volume=volume))
            sides[target] = levels
        if not sides['bids'] and not sides['asks']: return unavailable(code, '盘口没有可用价位')
        return dict(symbol=code, status='ok', collected_at=datetime.now(timezone.utc).isoformat(),
                    bid_server_time=response.get('svr_recv_time_bid') or None,
                    ask_server_time=response.get('svr_recv_time_ask') or None,
                    depth=depth, returned_bids=len(sides['bids']), returned_asks=len(sides['asks']),
                    bids=sides['bids'], asks=sides['asks'],
                    scope='visible_top_levels', source='moomoo OpenD get_order_book')
    except (OSError, RuntimeError, ValueError, KeyError, TypeError, AttributeError) as error:
        return unavailable(code, error)


def visible_price_zones(book, reference_price=None):
    """Merge neighboring visible levels without treating them as marketwide orders."""
    if not book or book.get('status') != 'ok':
        return dict(bids=[], asks=[])
    if (type(reference_price) not in (int, float) or not isfinite(reference_price)
            or reference_price <= 0):
        reference_price = None
    prices = [row['price'] for side in ('bids', 'asks') for row in book.get(side, [])]
    scale = reference_price or (max(prices) if prices else 1.0)
    maximum_gap = max(0.02, scale * 0.001)
    maximum_span = max(0.05, scale * 0.003)
    zones = {}
    for side, descending in (('bids', True), ('asks', False)):
        levels = sorted((row for row in book.get(side, []) if row['volume'] > 0),
                        key=lambda row: row['price'], reverse=descending)
        groups = []
        for level in levels:
            if (not groups or abs(level['price'] - groups[-1][-1]['price']) > maximum_gap
                    or abs(level['price'] - groups[-1][0]['price']) > maximum_span):
                groups.append([])
            groups[-1].append(level)
        items = []
        for group in groups:
            low = min(row['price'] for row in group)
            high = max(row['price'] for row in group)
            distance = max(low-reference_price, reference_price-high, 0) if reference_price else None
            distance_pct = distance / reference_price * 100 if reference_price else None
            items.append(dict(low=low, high=high, volume=sum(row['volume'] for row in group),
                              notional=round(sum(row['price'] * row['volume'] for row in group), 2),
                              levels=len(group), distance_pct=distance_pct))
        if reference_price:
            items.sort(key=lambda zone: (zone['distance_pct'],
                                         -zone['high'] if side == 'bids' else zone['low']))
        zones[side] = items
    return zones


def visible_value_ratio(book):
    """Compare the notional value of all returned visible bid and ask levels."""
    if not book or book.get('status') != 'ok':
        return dict(status='unavailable')
    values = {}
    for side in ('bids', 'asks'):
        values[side] = sum(row['price'] * row['volume'] for row in book.get(side, [])
                           if row['volume'] > 0)
    bid_value, ask_value = values['bids'], values['asks']
    if bid_value <= 0 or ask_value <= 0:
        return dict(status='insufficient', bid_value=round(bid_value, 2),
                    ask_value=round(ask_value, 2))
    total = bid_value + ask_value
    return dict(status='ok', bid_value=round(bid_value, 2), ask_value=round(ask_value, 2),
                bid_share=bid_value / total, ask_share=ask_value / total,
                bid_to_ask=bid_value / ask_value)
