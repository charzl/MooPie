"""Watchlist quote overview, separate from Put rankings and trend evidence."""
from math import isfinite


def _number(value):
    return value if type(value) in (int, float) and isfinite(value) and value > 0 else None


def build_overview(symbols, snapshot, identities):
    quotes = {row['code']: row for row in snapshot.get('rows', [])}
    rows = []
    for symbol in symbols:
        quote = quotes.get(symbol, {})
        identity = identities.get(symbol, {})
        price = _number(quote.get('last_price'))
        previous = _number(quote.get('prev_close_price'))
        rows.append(dict(symbol=symbol, name=identity.get('name') or quote.get('name') or symbol,
                         security_type=identity.get('security_type'), price=price,
                         previous_close=previous,
                         change_pct=(price / previous - 1) * 100 if price and previous else None,
                         update_time=quote.get('update_time') or None))
    return dict(action='overview', symbol='Watchlist', query_scope='watchlist', symbols=list(symbols),
                rows=rows, collected_at=snapshot.get('collected_at'),
                data_access=snapshot.get('data_access', {}))
