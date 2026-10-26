"""Rank saved support observations for the Watchlist without inventing live levels."""
from math import isfinite


def build_radar(overview, signals, alerts):
    rows = []
    for quote in overview['rows']:
        symbol = quote['symbol']
        saved = signals.get(symbol)
        signal = saved['signal'] if saved else None
        zones = signal.get('support_zones', []) if signal and signal.get('status') == 'ok' else []
        alert = alerts.get(symbol)
        zone = (dict(low=alert['support_low'], high=alert['support_high']) if alert else
                zones[0] if zones else None)
        price = quote.get('price')
        if type(price) not in (int, float) or not isfinite(price) or price <= 0:
            state, distance = 'quote_unavailable', None
        elif zone is None:
            state, distance = 'levels_unavailable', None
        elif alert:
            state = alert['status']
            distance = max(0.0, (price-zone['high'])/price*100) if price > zone['high'] else 0.0
        elif price < zone['low']:
            state, distance = 'below', (zone['low']-price)/price*100
        elif price <= zone['high']:
            state, distance = 'inside_unarmed', 0.0
        else:
            state, distance = 'above', (price-zone['high'])/price*100
        rows.append(dict(**quote, support_low=zone['low'] if zone else None,
                         support_high=zone['high'] if zone else None,
                         signal_as_of=alert['signal_as_of'] if alert else signal.get('as_of') if signal else None,
                         alert_mode=alert['confirmation_mode'] if alert else None,
                         state=state, distance_pct=distance,
                         stale_alert=bool(alert and signal and alert['signal_as_of'] != signal.get('as_of'))))
    priority = {'confirmed': 0, 'inside': 1, 'inside_unarmed': 2, 'above': 3,
                'watching': 3, 'below': 4, 'invalidated': 4, 'paused': 5,
                'levels_unavailable': 6, 'quote_unavailable': 7}
    rows.sort(key=lambda row: (priority[row['state']], row['distance_pct'] if row['distance_pct'] is not None else float('inf'), row['symbol']))
    return dict(action='radar', rows=rows, symbols=overview['symbols'],
                collected_at=overview.get('collected_at'), data_access=overview.get('data_access', {}))
