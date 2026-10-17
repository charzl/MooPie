"""Independent, descriptive price-location signals over validated daily history.

The research layer supplies the canonical trend validator's evidence. No SDK,
storage, ranking weights or changes to the Put rule engine belong here.
"""
from math import isfinite
from statistics import median

SIGNAL_VERSION = '1.0.0'
PARAMETERS = dict(lookback=120, pivot_radius=2, minimum_touch_spacing=5,
                  zone_atr_fraction=0.5, zone_price_fraction=0.005,
                  nearby_atr=1.0, resistance_support_distance_ratio=0.5, maximum_zones=3)
LIMITATIONS = [
    '潜在支撑 / 阻力来自历史日线转折，不代表当前挂单、真实持仓成本或买卖盘比例。',
    '未验证盘口承接、逐笔方向、成交量按价分布和做市商 Gamma 仓位。',
    '属于日线价格位置参考，不是涨跌概率、估值结论或期权期望收益；支撑可能失效。',
]


def unavailable(symbol, reason):
    return dict(version=SIGNAL_VERSION, symbol=symbol, status='unavailable',
                ranking_effect='none', summary='价格信号数据不足', reason=reason,
                support_zones=[], resistance_zones=[], limitations=list(LIMITATIONS))


def _zones(bars, side, tolerance):
    """Confirmed two-sided pivots; nearby prices cluster without chain drift."""
    radius = PARAMETERS['pivot_radius']
    field, compare = ('low', min) if side == 'support' else ('high', max)
    pivots = []
    for index in range(radius, len(bars)-radius):
        value = bars[index][field]
        before = compare(b[field] for b in bars[index-radius:index])
        after = compare(b[field] for b in bars[index+1:index+radius+1])
        # Strict on the left avoids counting every day of a flat plateau.
        is_pivot = value < before and value <= after if side == 'support' else value > before and value >= after
        if is_pivot:
            pivots.append(dict(price=value, date=bars[index]['date'], index=index,
                               confirmed_at=bars[index+radius]['date']))
    groups = []
    for pivot in sorted(pivots, key=lambda row: row['price']):
        if not groups or pivot['price']-groups[-1][0]['price'] > 2*tolerance:
            groups.append([])
        groups[-1].append(pivot)
    zones = []
    for group in groups:
        touches = []
        for pivot in sorted(group, key=lambda row: row['index']):
            if not touches or pivot['index']-touches[-1]['index'] >= PARAMETERS['minimum_touch_spacing']:
                touches.append(pivot)
        center = median(row['price'] for row in touches)
        zones.append(dict(low=max(0, min(row['price'] for row in touches)-tolerance),
                          high=max(row['price'] for row in touches)+tolerance,
                          center=center, independent_touches=len(touches),
                          evidence_strength='repeated_pivots' if len(touches)>1 else 'single_pivot',
                          evidence=[{k:v for k,v in row.items() if k!='index'} for row in touches]))
    return zones


def price_position(series, trend, *, reference=None):
    """Describe zones, using only bars already accepted by the trend validator."""
    symbol = trend.get('symbol')
    if trend.get('status') != 'ok':
        return unavailable(symbol, trend.get('error', '日线未通过验证'))
    try:
        bars = series['bars']
        if (series['symbol'] != symbol or series['as_of'] != trend['as_of'] or
                len(bars) != trend['bar_count'] or bars[-1]['date'] != trend['as_of']):
            raise ValueError('日线与验证证据不一致')
        metrics = trend['metrics']
        reference = reference or dict(price=metrics['close'], basis='daily_close', time=trend['as_of'])
        price = reference['price']
        atr = metrics['atr14']
        if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not isfinite(v) or v<=0 for v in (price, atr)):
            raise ValueError('参考价格或 ATR 无效')
        bars = bars[-PARAMETERS['lookback']:]
        tolerance = max(atr*PARAMETERS['zone_atr_fraction'], price*PARAMETERS['zone_price_fraction'])
        supports = [z for z in _zones(bars, 'support', tolerance) if z['low'] <= price]
        resistances = [z for z in _zones(bars, 'resistance', tolerance) if z['high'] >= price]
        for side, zones in [('support', supports), ('resistance', resistances)]:
            for zone in zones:
                distance = max(0, price-zone['high']) if side=='support' else max(0, zone['low']-price)
                zone.update(distance_pct=distance/price*100, distance_atr=distance/atr)
            zones.sort(key=lambda z:(z['distance_pct'], -z['independent_touches']))
            del zones[PARAMETERS['maximum_zones']:]
        support = supports[0] if supports else None
        resistance = resistances[0] if resistances else None
        nearby = PARAMETERS['nearby_atr']
        weakening = metrics['macd_histogram'] < 0 and metrics['macd_histogram_change'] < 0 and price < metrics['ma20']
        closer_to_resistance = (support and resistance and support['distance_atr']>nearby and
                                resistance['distance_atr']<support['distance_atr']*PARAMETERS['resistance_support_distance_ratio'])
        if resistance and resistance['distance_atr']<=nearby and (not support or support['distance_atr']>nearby):
            assessment, summary = 'near_resistance', '接近潜在阻力，宜等待更好的价格位置'
            next_check = '观察回落后是否在支撑区企稳；若放量突破阻力，应重新评估价位。'
        elif closer_to_resistance:
            assessment, summary = 'closer_to_resistance', '价格更靠近潜在阻力，可等待回落后的承接依据'
            next_check = '比较支撑与阻力距离，并观察回落是否企稳；这些距离不是期权盈亏比。'
        elif weakening:
            assessment, summary = 'weakening', '短期动能转弱，宜等待企稳证据'
            next_check = '观察支撑能否守住、价格与动能是否改善；跌破后重新评估。'
        elif support and support['distance_atr']<=nearby:
            assessment, summary = 'near_support', '接近潜在支撑，仍需确认承接'
            next_check = '观察是否止跌、回收失地或形成反弹；触及支撑本身不是开仓依据。'
        else:
            assessment, summary = 'unconfirmed', '当前缺少明确的价格位置优势'
            next_check = '等待价格接近有依据的区域，并观察实际价格反应。'
        return dict(version=SIGNAL_VERSION, symbol=symbol, status='ok', ranking_effect='none',
                    assessment=assessment, summary=summary, next_check=next_check,
                    as_of=trend['as_of'], available_at=trend['available_at'], reference=dict(reference),
                    source='completed_regular_qfq_daily_pivots', parameters=dict(PARAMETERS),
                    lookback_start=bars[0]['date'], lookback_bars=len(bars), atr14=atr,
                    zone_tolerance=tolerance, support_zones=supports, resistance_zones=resistances,
                    reasons=[f'日线收盘 {metrics["close"]:.2f}，MA20 {metrics["ma20"]:.2f}。',
                             f'MACD 柱 {metrics["macd_histogram"]:.3f}，较前日变化 {metrics["macd_histogram_change"]:.3f}。'],
                    order_flow=dict(status='not_verified', buy_sell_ratio=None), limitations=list(LIMITATIONS))
    except (KeyError, TypeError, ValueError, IndexError) as error:
        return unavailable(symbol, str(error))


def dataset_signals(dataset, trends):
    """Keep diagnostics outside report; never mutate the input or ranked rows."""
    histories = {s['symbol']:s for s in dataset.get('daily_series', [])}
    references = {}
    for contract in dataset.get('contracts', []):
        symbol = contract.get('symbol')
        value = (contract.get('underlying_price'), contract.get('underlying_update_time'))
        values = references.setdefault(symbol, [])
        if value not in values: values.append(value)
    result = {}
    for symbol, trend in trends.items():
        values = references.get(symbol, [])
        if len(values)>1:
            result[symbol] = unavailable(symbol, '同一股票的参考报价不一致')
        else:
            reference = None
            if values:
                price, when = next(iter(values))
                reference = dict(price=price, time=when, basis='underlying_snapshot')
            result[symbol] = price_position(histories.get(symbol), trend, reference=reference)
    return result
