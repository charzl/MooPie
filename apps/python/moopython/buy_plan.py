"""Hypothetical stock tranches and quote-sequenced support alerts."""
from math import floor, isfinite


def nearest_levels(signal):
    if not signal or signal.get('status') != 'ok' or not signal.get('support_zones'):
        return None
    support = signal['support_zones'][0]
    resistance = next((zone for zone in signal.get('resistance_zones', [])
                       if zone['low'] > support['high']), None)
    return dict(low=float(support['low']), high=float(support['high']),
                resistance=float(resistance['low']) if resistance else None,
                as_of=signal['as_of'])


def calculate_plan(signal, budget):
    if isinstance(budget, bool) or not isinstance(budget, (int, float)) or not isfinite(budget) or budget <= 0:
        raise ValueError('投入金额必须大于 0')
    levels = nearest_levels(signal)
    if levels is None:
        raise ValueError('暂无已确认的下方支撑区，不能自动生成买入计划')
    low, high = levels['low'], levels['high']
    if low <= 0 or high < low:
        raise ValueError('支撑区价格无效')
    # Subsequent tranches are conditional retests, never assumed filled.
    prices = [high, low + (high-low)*.5, low + (high-low)*.25]
    weights = [.4, .3, .3]
    tranches = [dict(price=round(price, 2), shares=floor(budget*weight / round(price, 2)),
                     allocation=budget*weight) for price, weight in zip(prices, weights)]
    cost = sum(item['shares']*item['price'] for item in tranches)
    shares = sum(item['shares'] for item in tranches)
    if shares == 0:
        raise ValueError('按当前分批比例，金额不足以购买一股；请增加投入金额')
    stop = round(low, 2)
    risk = sum(max(0, item['price']-stop)*item['shares'] for item in tranches)
    target = levels['resistance']
    return dict(**levels, budget=budget, stop=stop, tranches=tranches,
                shares=shares, cost=round(cost, 2), unused=round(budget-cost, 2),
                average=round(cost/shares, 2) if shares else None,
                max_loss_to_stop=round(risk, 2),
                target_gain=round(target*shares-cost, 2) if target is not None else None)


def advance_alert(record, price, quote_time):
    """One provider timestamp advances at most one phase; old quotes never alert."""
    if not quote_time or not isinstance(quote_time, str):
        return record
    if isinstance(price, bool) or not isinstance(price, (int, float)) or not isfinite(price) or price <= 0:
        return record
    if record['status'] in ('paused', 'confirmed', 'invalidated') or quote_time <= record['last_quote_time']:
        return record
    status = record['status']
    if price < record['support_low']:
        status = 'invalidated'
    elif status == 'watching' and record['support_low'] <= price <= record['support_high']:
        status = 'inside'
    elif status == 'inside' and price > record['support_high']:
        status = 'confirmed'
    return dict(record, status=status, last_quote_time=quote_time, last_price=price,
                triggered_at=quote_time if status in ('confirmed', 'invalidated') else record['triggered_at'])
