"""Hypothetical stock tranches and quote-sequenced support alerts."""
from datetime import date
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


def calculate_plan(signal, budget, risk_budget=None):
    if isinstance(budget, bool) or not isinstance(budget, (int, float)) or not isfinite(budget) or budget <= 0:
        raise ValueError('投入金额必须大于 0')
    if risk_budget is not None and (isinstance(risk_budget, bool) or
            not isinstance(risk_budget, (int, float)) or not isfinite(risk_budget) or risk_budget <= 0):
        raise ValueError('风险预算必须大于 0；留空或设为 0 表示不限制')
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
    stop = round(low, 2)
    loss_per_share = [max(0, item['price']-stop) for item in tranches]
    full_risk = sum(loss*item['shares'] for loss, item in zip(loss_per_share, tranches))
    risk_limited = risk_budget is not None and full_risk > risk_budget
    if risk_limited:
        factor = risk_budget/full_risk
        for item in tranches:
            item['shares'] = floor(item['shares']*factor)
    cost = sum(item['shares']*item['price'] for item in tranches)
    shares = sum(item['shares'] for item in tranches)
    if shares == 0:
        raise ValueError('风险预算或投入金额不足以按当前分批比例购买一股')
    risk = sum(loss*item['shares'] for loss, item in zip(loss_per_share, tranches))
    target = levels['resistance']
    return dict(**levels, budget=budget, risk_budget=risk_budget, risk_limited=risk_limited,
                uncapped_loss_to_stop=round(full_risk, 2), stop=stop, tranches=tranches,
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
    elif status == 'inside' and record.get('confirmation_mode', 'quote') == 'quote' and price > record['support_high']:
        status = 'confirmed'
    return dict(record, status=status, last_quote_time=quote_time, last_price=price,
                entered_at=quote_time if status == 'inside' and record['status'] == 'watching' else record.get('entered_at', ''),
                triggered_at=quote_time if status in ('confirmed', 'invalidated') else record['triggered_at'])


def advance_close_alert(record, close, as_of):
    """A completed later trading day can confirm the quote-observed support touch."""
    if record.get('confirmation_mode') != 'daily_close' or record['status'] != 'inside':
        return record
    if not isinstance(as_of, str) or len(as_of) != 10 or as_of <= record.get('last_bar_date', ''):
        return record
    try: date.fromisoformat(as_of)
    except ValueError: return record
    entered_at = record.get('entered_at', '')
    if not entered_at or as_of <= entered_at[:10]:
        return record
    if isinstance(close, bool) or not isinstance(close, (int, float)) or not isfinite(close) or close <= 0:
        return record
    status = ('confirmed' if close > record['support_high'] else
              'invalidated' if close < record['support_low'] else 'inside')
    return dict(record, status=status, last_bar_date=as_of,
                triggered_at=as_of if status in ('confirmed', 'invalidated') else record['triggered_at'])
