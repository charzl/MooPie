"""Read and describe visible order-book depth for one stock on demand."""
from datetime import datetime, timezone
from math import isfinite

from .market_collection import opend_connection, us_symbols


def unavailable(symbol, reason):
    return dict(symbol=symbol, status='unavailable', reason=str(reason))


def read_order_book(symbol, port=11111, depth=10):
    code = us_symbols([symbol])[0]
    if type(depth) is not int or not 1 <= depth <= 10:
        raise ValueError('Order-book depth must be 1–10')
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
                    depth=depth, bids=sides['bids'], asks=sides['asks'],
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
                              levels=len(group), distance_pct=distance_pct))
        if reference_price:
            items.sort(key=lambda zone: (zone['distance_pct'],
                                         -zone['high'] if side == 'bids' else zone['low']))
        zones[side] = items
    return zones
