"""Read and describe visible order-book depth for one stock on demand."""
from datetime import datetime, timezone
from html import escape
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


def order_book_html(book):
    content = '<h2>买卖盘价位</h2>'
    if not book or book.get('status') != 'ok':
        return content + '<p>盘口不可用：' + escape((book or {}).get('reason', '尚未查询')) + '</p>'
    content += '<p>仅比较当前可见的前 '+str(book['depth'])+' 档挂单量；挂单可以撤销，不代表实际成交或有效支撑。</p>'
    for field, label in (('bids', '买盘'), ('asks', '卖盘')):
        largest = sorted((level for level in book[field] if level['volume'] > 0),
                         key=lambda level: (-level['volume'], level['price']))[:3]
        content += '<p><b>'+label+'主要价位：</b>' + (' · '.join(
            f'${level["price"]:,.2f}（{level["volume"]:,.0f} 股）' for level in largest) if largest else '没有可见档位') + '</p>'
    content += ('<p>采集时间（UTC）：'+escape(book['collected_at'])+'<br>买盘服务器时间：'
                +escape(book.get('bid_server_time') or '未提供，无法核对交易所更新时间')
                +' · 卖盘服务器时间：'+escape(book.get('ask_server_time') or '未提供，无法核对交易所更新时间')+'</p>')
    for field, label in (('bids', '买盘'), ('asks', '卖盘')):
        levels = book[field]
        content += '<h3>'+label+'挂单量较集中的价位</h3>'
        if not levels:
            content += '<p>没有可见档位。</p>'
            continue
        content += '<table cellspacing="0" cellpadding="6"><tr><th>档位</th><th>价格</th><th>可见挂单量</th></tr>'
        for index, level in enumerate(levels, 1):
            content += f'<tr><td>{index}</td><td>${level["price"]:,.2f}</td><td>{level["volume"]:,.0f} 股</td></tr>'
        content += '</table>'
    return content
