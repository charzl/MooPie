"""Editable, standalone cash-secured PUT research rules. Python standard library only.

Edit RECOMMENDATION_BOUNDARIES / RISK_WEIGHTS / SCORING_PARAMETERS /
TREND_RULES / RULES / SORT_ORDER below,
increase RULESET_VERSION, and rerun.
No broker, Qt, other rule-engine package, model, or order API is imported here.
"""
import argparse
from datetime import date, datetime, time, timezone
import hashlib
import json
import math
import operator
from pathlib import Path
import re
from zoneinfo import ZoneInfo


ENGINE_VERSION = '0.6.0'
RULESET_VERSION = '4.2.0'
# Initial research thresholds, not calibrated probabilities or backtested signals.
# These remain available as optional hard filters. Oversold is not a buy signal.
TREND_RULES = [
    ('above-ma50', 'distance_to_ma50_pct', '>=', 0),
    ('ma50-not-falling', 'ma50_slope_5d_pct', '>=', 0),
    ('no-20d-breakdown', 'breakdown_20d', '==', 0),
    ('rsi-floor', 'rsi14', '>=', 40),
    ('momentum-not-deteriorating', 'macd_histogram_change', '>=', 0),
]
RULES = [
    ('standard-contract', 'standard_contract', '==', 1),
    ('not-suspended', 'not_suspended', '==', 1),
    ('same-session-snapshot', 'same_session_snapshot', '==', 1),
    ('min-days', 'days_to_expiry', '>=', 21),
    ('max-days', 'days_to_expiry', '<=', 60),
    ('otm-buffer', 'otm_pct', '>=', 5),
    ('min-delta', 'abs_delta', '>=', .15),
    ('max-delta', 'abs_delta', '<=', .30),
    ('min-bid', 'bid', '>=', .10),
    ('bid-size', 'bid_size', '>=', 1),
    ('open-interest', 'open_interest', '>=', 200),
    ('volume', 'volume', '>=', 10),
    ('spread', 'spread_pct_of_mid', '<=', 15),
    ('earnings-checked', 'earnings_known', '==', 1),
    ('earnings-buffer', 'days_expiry_before_earnings', '>=', 3),
    ('underlying-trend', 'trend_allowed', '==', 1),
    ('min-cost', 'cash_collateral', '>', 0),
    ('max-cost', 'cash_collateral', '<', 100000),
    ('min-daily-return', 'daily_gross_return_pct', '>', .05),
    ('max-risk', 'risk_score', '<', 50),
    ('expiry-before', 'expiration', '<', None),
]
# User-supplied bounds are opt-in in both recommendation and legacy scan modes.
OPTIONAL_SELECTION_FILTERS = frozenset(('min-cost', 'max-cost', 'min-daily-return', 'max-risk', 'expiry-before'))
# Among survivors, maximize daily gross premium on full strike cash collateral;
# ties favor tighter spreads / lower delta.
SORT_ORDER = [('daily_gross_return_pct', 'desc'), ('spread_pct_of_mid', 'asc'), ('abs_delta', 'asc')]
RANKING_SORT_ORDERS = {
    'duration': [('days_to_expiry', 'asc'), ('daily_gross_return_pct', 'desc'), ('risk_score', 'asc')],
    'cost': [('cash_collateral', 'asc'), ('daily_gross_return_pct', 'desc'), ('risk_score', 'asc')],
    'return': [('daily_gross_return_pct', 'desc'), ('risk_score', 'asc'), ('spread_pct_of_mid', 'asc')],
    'risk': [('risk_score', 'asc'), ('daily_gross_return_pct', 'desc'), ('spread_pct_of_mid', 'asc')],
    'balanced': [('composite_score', 'desc'), ('daily_gross_return_pct', 'desc'), ('risk_score', 'asc')],
}
# Provisional research model. Weights and scales have NOT been calibrated.
RISK_WEIGHTS = dict(delta=25, stress_loss=25, trend=20, liquidity=15, earnings=15)
RISK_LABELS = dict(delta='Delta 敏感度', stress_loss='下跌情景亏损', trend='股票趋势',
                   liquidity='流动性', earnings='财报事件')
# Default, lower bound, upper bound, editable parameter label.
SCORING_PARAMETERS = {
    'delta_high': (.5, .000001, 1, 'Delta 达到满风险分的参考值'),
    'stress_drop_pct': (20, .000001, 100, '到期股价下跌情景（%）'),
    'stress_loss_high_pct': (20, .000001, 100, '情景亏损占本金达到满分的参考值（%）'),
    'spread_high_pct': (15, .000001, 200, '价差达到满风险分的参考值（%）'),
    'open_interest_target': (200, .000001, 1e9, '未平仓量参考目标'),
    'bid_size_target': (10, .000001, 1e9, '买盘数量参考目标'),
    'earnings_buffer_days': (3, .000001, 365, '到期与财报的间隔参考天数'),
    'unknown_risk_score': (100, 0, 100, '缺失趋势 / 财报的风险惩罚分'),
    'daily_return_target_pct': (.1, .000001, 100, '收益分达到100分的日均毛收益率（%）'),
    'return_weight': (.5, 0, 1, '综合分中收益的权重（0–1，其余为风险权重）'),
}
LIVE_MAX_SNAPSHOT_AGE_SECONDS = 900
OPS = {'>': operator.gt, '>=': operator.ge, '<': operator.lt,
       '<=': operator.le, '==': operator.eq}
NY = ZoneInfo('America/New_York')
METRICS = frozenset(('bid', 'ask', 'shares', 'strike', 'underlying_price', 'days_to_expiry',
    'risk_score', 'return_score', 'composite_score', 'stress_loss_pct', 'expiration',
    'abs_delta', 'iv_pct', 'volume', 'open_interest', 'bid_size', 'spread_pct_of_mid', 'otm_pct',
    'breakeven_before_costs', 'breakeven_buffer_pct', 'premium_per_contract_before_costs',
    'cash_collateral', 'gross_return_pct', 'daily_gross_return_pct', 'annualized_gross_return_pct', 'max_profit_before_costs',
    'max_loss_before_costs', 'pnl_at_spot_minus_20_pct', 'standard_contract', 'not_suspended',
    'same_session_snapshot', 'snapshot_age_seconds', 'earnings_known', 'days_expiry_before_earnings',
    'trend_allowed', 'strike_below_20d_low_atr'))
TREND_METRICS = frozenset(('distance_to_ma50_pct', 'ma50_slope_5d_pct', 'breakdown_20d',
                          'rsi14', 'macd_histogram_change'))
EARNINGS_RULES = frozenset(('earnings-checked', 'earnings-buffer'))
# Supported-contract boundaries, shown separately from optional strategy filters.
REQUIRED_FILTERS = frozenset(('standard-contract', 'not-suspended'))
SORTABLE_METRICS = (METRICS - {'iv_pct', 'days_expiry_before_earnings', 'strike_below_20d_low_atr'}) | {'symbol', 'earnings_date'}
# Illustrative basic boundaries, not a statement of any user's risk tolerance.
# Preferences such as RSI, momentum, minimum OI and minimum Delta are not vetoes.
RECOMMENDATION_BOUNDARIES = {
    'standard-contract': 1, 'not-suspended': 1, 'same-session-snapshot': 1,
    'min-days': 7, 'max-days': 90, 'otm-buffer': 0, 'max-delta': .30,
    'min-bid': .10, 'bid-size': 1, 'spread': 15,
}


def recommendation_configuration(configuration=None):
    result = default_configuration()
    for rid, option in result['filters'].items():
        option['enabled'] = rid in RECOMMENDATION_BOUNDARIES
        if option['enabled']: option['threshold'] = float(RECOMMENDATION_BOUNDARIES[rid])
    if configuration is not None:
        if not isinstance(configuration, dict): raise ValueError('Configuration must be an object')
        if set(configuration) - result.keys(): raise ValueError('Invalid filter configuration keys')
        for key, value in configuration.items():
            if key in ('filters', 'trend_filters'):
                if not isinstance(value, dict) or set(value) - result[key].keys():
                    raise ValueError('Unknown filter in ' + key)
                for rid, options in value.items():
                    if not isinstance(options, dict) or set(options) - {'enabled', 'threshold'}:
                        raise ValueError('Invalid filter options: ' + rid)
                    result[key][rid].update(options)
            else: result[key] = value
    return resolve_configuration(result)


def default_configuration():
    return dict(schema=1,
        filters={rid: dict(enabled=rid not in OPTIONAL_SELECTION_FILTERS,
                          threshold=threshold if metric == 'expiration' else float(threshold))
                 for rid, metric, _, threshold in RULES},
        trend_filters={rid: dict(enabled=True, threshold=float(threshold)) for rid, _, _, threshold in TREND_RULES},
        sort_order=[list(item) for item in SORT_ORDER],
        scoring=dict(weights=dict(RISK_WEIGHTS), parameters={key: value[0] for key, value in SCORING_PARAMETERS.items()}))


def resolve_configuration(configuration=None):
    """Apply explicit user overrides without ever changing the module defaults."""
    validate_rules()
    result = default_configuration()
    if configuration is None: return result
    if not isinstance(configuration, dict) or set(configuration) - {'schema', 'filters', 'trend_filters', 'sort_order', 'scoring'}:
        raise ValueError('Invalid filter configuration keys')
    if type(configuration.get('schema', 1)) is not int or configuration.get('schema', 1) != 1:
        raise ValueError('Unsupported filter configuration schema')
    scoring = configuration.get('scoring', {})
    if not isinstance(scoring, dict) or set(scoring) - {'weights', 'parameters'}:
        raise ValueError('Invalid scoring configuration keys')
    for group in ('weights', 'parameters'):
        overrides = scoring.get(group, {})
        if not isinstance(overrides, dict) or set(overrides) - result['scoring'][group].keys():
            raise ValueError('Unknown scoring ' + group)
        for key, value in overrides.items():
            number = finite(value, 'Scoring ' + key)
            low, high = (0, 100) if group == 'weights' else SCORING_PARAMETERS[key][1:3]
            if not low <= number <= high: raise ValueError('Scoring parameter out of range: ' + key)
            result['scoring'][group][key] = number
    if sum(result['scoring']['weights'].values()) <= 0:
        raise ValueError('At least one risk weight must be positive')
    for group in ('filters', 'trend_filters'):
        overrides = configuration.get(group, {})
        if not isinstance(overrides, dict) or set(overrides) - result[group].keys():
            raise ValueError('Unknown filter in ' + group)
        for rid, options in overrides.items():
            if not isinstance(options, dict) or set(options) - {'enabled', 'threshold'}:
                raise ValueError('Invalid filter options: ' + rid)
            chosen = dict(result[group][rid], **options)
            if type(chosen['enabled']) is not bool: raise ValueError('Filter enabled must be boolean: ' + rid)
            source = RULES if group == 'filters' else TREND_RULES
            metric = next(metric for key, metric, _, _ in source if key == rid)
            if metric == 'expiration':
                if chosen['threshold'] is not None or chosen['enabled']:
                    iso_date(chosen['threshold'])
            else:
                finite(chosen['threshold'], rid)
                chosen['threshold'] = float(chosen['threshold'])
            if group == 'filters' and rid in REQUIRED_FILTERS and chosen != result[group][rid]:
                raise ValueError('Required supported-contract check cannot be disabled or changed: ' + rid)
            if group == 'filters' and metric != 'expiration' and chosen['threshold'] < 0:
                raise ValueError('Filter threshold cannot be negative: ' + rid)
            if metric == 'abs_delta' and not 0 <= chosen['threshold'] <= 1:
                raise ValueError('Delta threshold must be 0–1')
            if metric in ('standard_contract', 'not_suspended', 'same_session_snapshot', 'earnings_known', 'trend_allowed', 'breakdown_20d') and chosen['threshold'] not in (0, 1):
                raise ValueError('Boolean filter threshold must be 0 or 1: ' + rid)
            if metric == 'rsi14' and not 0 <= chosen['threshold'] <= 100:
                raise ValueError('RSI threshold must be 0–100')
            if metric == 'risk_score' and not 0 <= chosen['threshold'] <= 100:
                raise ValueError('Risk threshold must be 0–100')
            result[group][rid] = chosen
    for minimum, maximum in (('min-days', 'max-days'), ('min-delta', 'max-delta')):
        lower, upper = result['filters'].get(minimum), result['filters'].get(maximum)
        if lower and upper and lower['enabled'] and upper['enabled'] and lower['threshold'] > upper['threshold']:
            raise ValueError('Minimum filter exceeds maximum: ' + minimum)
    lower, upper = result['filters'].get('min-cost'), result['filters'].get('max-cost')
    if lower and upper and lower['enabled'] and upper['enabled'] and lower['threshold'] >= upper['threshold']:
        raise ValueError('Minimum filter exceeds maximum: min-cost (strict cost bounds must differ)')
    if 'sort_order' in configuration:
        order = configuration['sort_order']
        if not isinstance(order, list) or not order: raise ValueError('At least one sort metric is required')
        seen = set()
        for item in order:
            if not isinstance(item, (list, tuple)) or len(item) != 2:
                raise ValueError('Sort entries must contain metric and direction')
            metric, direction = item
            if not isinstance(metric, str) or metric not in SORTABLE_METRICS or metric in seen or direction not in ('asc', 'desc'):
                raise ValueError('Invalid, duplicate or nullable sort metric: ' + str(metric))
            seen.add(metric)
        result['sort_order'] = [list(item) for item in order]
    return result


def configured_rules(source, options):
    return [(rid, metric, op, options[rid]['threshold']) for rid, metric, op, _ in source if options[rid]['enabled']]


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def sorted_candidates(rows, order):
    """Stable numeric, ticker and ISO-date sorting; missing events always last."""
    def value(row, metric):
        if metric in ('symbol', 'expiration'): return row[metric]
        if metric == 'earnings_date': return (row.get('earnings') or {}).get('date')
        return finite(row['metrics'].get(metric), metric)
    result = sorted(rows, key=lambda row: row['code'])
    # Stable passes preserve lower-priority tie-breakers in either direction.
    for metric, direction in reversed(order):
        known = [row for row in result if value(row, metric) is not None]
        missing = [row for row in result if value(row, metric) is None]
        result = sorted(known, key=lambda row: value(row, metric), reverse=direction == 'desc') + missing
    return result


def finite(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(name + ' must be a finite number')
    return float(value)


def iso_date(value):
    if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
        raise ValueError('Date must be YYYY-MM-DD')
    return date.fromisoformat(value)


def timestamp(value, assume_market_timezone=False):
    result = datetime.fromisoformat(value)
    if result.tzinfo is None:
        if not assume_market_timezone:
            raise ValueError('Collection timestamp must include a timezone')
        result = result.replace(tzinfo=NY)
    return result


def ema(values, period):
    """SMA seed; return (original index, EMA) pairs, never read future values."""
    seed = sum(values[:period]) / period
    result = [(period - 1, seed)]
    for index in range(period, len(values)):
        seed += 2 / (period + 1) * (values[index] - seed)
        result.append((index, seed))
    return result


def wilder(values, period=14):
    value = sum(values[:period]) / period
    for item in values[period:]: value = (value * (period - 1) + item) / period
    return value


def trend(series, session_date, collected_at, checks=None):
    """One completed regular-session QFQ series -> auditable trend evidence."""
    if not isinstance(series, dict): raise ValueError('Missing daily history')
    if series.get('error'): raise ValueError('Daily history collection failed: ' + str(series['error']))
    if (series.get('interval'), series.get('adjustment'), series.get('session')) != ('1d', 'qfq', 'regular'):
        raise ValueError('Require regular-session QFQ daily bars')
    as_of = iso_date(series.get('as_of'))
    if not 0 <= (session_date - as_of).days <= 7:
        raise ValueError('Daily history is stale or beyond quote session')
    available = timestamp(series.get('available_at')).astimezone(timezone.utc)
    if available > collected_at or available.astimezone(NY).date() != as_of:
        raise ValueError('Daily bar was not finalized at quote collection time')
    kind = series.get('trade_date_type')
    if kind not in ('WHOLE', 'MORNING', 'AFTERNOON'): raise ValueError('Unknown daily session close')
    close_time = time(13, 5) if kind == 'MORNING' else time(16, 5)
    if available.astimezone(NY).time() < close_time:
        raise ValueError('Daily bar available before session finalization')
    local = collected_at.astimezone(NY)
    if (local.date() > session_date or local.date() == session_date and local.time() >= time(16, 5)) and as_of != session_date:
        raise ValueError('Daily history does not include the completed quote session')
    dates = series.get('calendar_dates')
    bars = series.get('bars')
    if not isinstance(dates, list) or not isinstance(bars, list) or len(bars) < 205:
        raise ValueError('Need at least 205 completed daily bars and trading calendar')
    parsed = [iso_date(day) for day in dates]
    if parsed != sorted(set(parsed)) or parsed[-1] != as_of:
        raise ValueError('Invalid or stale trading calendar')
    bar_dates = [bar.get('date') for bar in bars]
    if bar_dates != dates: raise ValueError('Daily history has gaps, duplicates or unordered / future bars')
    for bar in bars:
        if bar.get('complete') is not True: raise ValueError('Incomplete daily bar')
        o, h, l, c, v = [finite(bar.get(key), key) for key in ('open', 'high', 'low', 'close', 'volume')]
        if min(o, h, l, c) <= 0 or v < 0 or not l <= min(o, c) <= max(o, c) <= h:
            raise ValueError('Invalid daily OHLCV')
    close = [bar['close'] for bar in bars]
    last = close[-1]
    def ma(period, offset=0):
        end = len(close) - offset
        return sum(close[end-period:end]) / period
    changes = [b-a for a, b in zip(close, close[1:])]
    gain = wilder([max(x, 0) for x in changes])
    loss = wilder([max(-x, 0) for x in changes])
    rsi = 50 if gain == loss == 0 else 100 if loss == 0 else 100 - 100 / (1 + gain/loss)
    fast, slow = dict(ema(close, 12)), dict(ema(close, 26))
    macd = [fast[i] - value for i, value in slow.items()]
    signal = ema(macd, 9)
    hist = [macd[i] - value for i, value in signal]
    tr = [max(bar['high']-bar['low'], abs(bar['high']-previous), abs(bar['low']-previous))
          for previous, bar in zip(close, bars[1:])]
    atr = wilder(tr)
    low20 = min(bar['low'] for bar in bars[-21:-1])
    previous_volume = sum(bar['volume'] for bar in bars[-21:-1]) / 20
    values = dict(close=last, ma20=ma(20), ma50=ma(50), ma200=ma(200),
        ma20_slope_5d_pct=100*(ma(20)/ma(20, 5)-1),
        ma50_slope_5d_pct=100*(ma(50)/ma(50, 5)-1),
        distance_to_ma50_pct=100*(last/ma(50)-1), rsi14=rsi,
        macd=macd[-1], macd_signal=signal[-1][1], macd_histogram=hist[-1],
        macd_histogram_change=round(hist[-1]-hist[-2], 12), atr14=atr,
        prior_20d_low=low20, prior_60d_low=min(bar['low'] for bar in bars[-61:-1]),
        breakdown_20d=int(last < low20),
        lower_highs_and_lows_5d=int(max(b['high'] for b in bars[-5:]) < max(b['high'] for b in bars[-10:-5])
                                  and min(b['low'] for b in bars[-5:]) < min(b['low'] for b in bars[-10:-5])),
        volume_ratio_20d=bars[-1]['volume']/previous_volume if previous_volume else None)
    reference = [dict(id=rid, metric=key, actual=values[key], op=op, threshold=threshold,
                     passed=OPS[op](values[key], threshold)) for rid, key, op, threshold in TREND_RULES]
    evidence = reference if checks is None else [dict(id=rid, metric=key, actual=values[key], op=op,
                     threshold=threshold, passed=OPS[op](values[key], threshold)) for rid, key, op, threshold in checks]
    failed = [r['id'] for r in evidence if not r['passed']]
    state = ('downtrend' if last < values['ma50'] and values['ma50_slope_5d_pct'] < 0
             else 'uptrend' if all(r['passed'] for r in reference) else 'mixed_or_weakening')
    return dict(symbol=series['symbol'], status='ok', as_of=as_of.isoformat(),
                available_at=series['available_at'], bar_count=len(bars), state=state,
                allowed=not failed, metrics=values, rules=evidence, failed_rules=failed,
                reference_rules=reference, baseline_failed_rules=[r['id'] for r in reference if not r['passed']])


def describe_trend(evidence):
    """Editable interpretation of validated daily indicators; no price forecast."""
    m = evidence['metrics']
    state = evidence['state']
    heading = {'downtrend': '偏弱，仍有继续下跌的压力',
               'uptrend': '趋势偏强，关注回调后的承接',
               'mixed_or_weakening': '方向分歧，暂未形成一致趋势'}[state]
    reasons = [
        f"收盘 {m['close']:.2f}，MA20 / MA50 / MA200 为 {m['ma20']:.2f} / {m['ma50']:.2f} / {m['ma200']:.2f}",
        f"MA50 五日斜率 {m['ma50_slope_5d_pct']:+.2f}%，RSI14 {m['rsi14']:.1f}",
        f"MACD 柱 {m['macd_histogram']:.3f}，较前日变化 {m['macd_histogram_change']:+.3f}",
        '已跌破此前 20 日低点' if m['breakdown_20d'] else '尚未跌破此前 20 日低点',
    ]
    if m['volume_ratio_20d'] is not None:
        reasons.append(f"成交量为此前 20 日均量的 {m['volume_ratio_20d']:.2f} 倍")
    condition = ('若跌破前低、失守 MA50，且均线和 MACD 同时转弱，当前偏强判断需要下调。'
                 if state == 'uptrend' else
                 '站上 MA50、均线止跌且 MACD 动能改善时，趋势才有转强依据；跌破前低则下行压力增加。')
    return dict(heading=heading, horizon='未来 5–20 个交易日的条件判断', reasons=reasons,
        levels=[dict(label='此前 20 日低点（跌破后关注收复）' if m['breakdown_20d'] else '此前 20 日低点', value=m['prior_20d_low']),
                dict(label='此前 60 日低点', value=m['prior_60d_low']),
                dict(label='MA20', value=m['ma20']), dict(label='MA50', value=m['ma50'])],
        change_condition=condition,
        limitation='基于已完成日线，不覆盖盘中变化、新闻与估值，也不提供经过校准的涨跌概率。')


def metrics(row, session_date, collected_at):
    if not isinstance(row, dict): raise ValueError('Contract must be an object')
    symbol, code = row.get('symbol'), row.get('code')
    if not isinstance(symbol, str) or not re.fullmatch(r'US\.[A-Z0-9][A-Z0-9._-]{0,31}', symbol):
        raise ValueError('Only US stock / ETF puts supported')
    if not isinstance(code, str) or not code.startswith('US.'):
        raise ValueError('Missing contract code')
    expiry = iso_date(row.get('expiration'))
    strike, shares, spot, bid, ask, delta = [finite(row.get(key), key)
        for key in ('strike', 'shares', 'underlying_price', 'bid', 'ask', 'delta')]
    if min(strike, spot, shares) <= 0 or not shares.is_integer():
        raise ValueError('Invalid strike, spot or contract shares')
    if not 0 < bid <= ask or bid >= strike:
        raise ValueError('Need a positive, uncrossed two-sided quote with bid below strike')
    if not -1 <= delta <= 0:
        raise ValueError('Invalid PUT delta')
    if row.get('currency') != 'USD' or row.get('option_type') != 'PUT' or row.get('option_valid') is not True:
        raise ValueError('Require a valid USD PUT snapshot')
    if (row.get('snapshot_symbol') != symbol or row.get('snapshot_option_type') != 'PUT'
            or row.get('snapshot_expiration') != row['expiration']
            or finite(row.get('snapshot_strike'), 'snapshot_strike') != strike
            or finite(row.get('snapshot_shares'), 'snapshot_shares') != shares):
        raise ValueError('Chain and snapshot identities / contract sizes do not match')
    dte = (expiry - session_date).days
    if dte <= 0: raise ValueError('Expired or same-day contract is excluded')
    updated = timestamp(row.get('snapshot_update_time'), assume_market_timezone=True)
    age = (collected_at - updated.astimezone(timezone.utc)).total_seconds()
    if age < -60: raise ValueError('Snapshot timestamp is in the future')
    liquidity = {key: finite(row.get(key), key) for key in ('volume', 'open_interest', 'bid_size')}
    if any(value < 0 for value in liquidity.values()): raise ValueError('Negative liquidity data')
    earnings = row.get('earnings')
    days_before_earnings = None
    if earnings is not None:
        event_day = iso_date(earnings.get('date'))
        if event_day < session_date: raise ValueError('Earnings date is stale')
        days_before_earnings = (event_day - expiry).days
    mid = (bid + ask) / 2
    credit = bid * shares
    cash = strike * shares
    breakeven = strike - bid
    iv = row.get('iv_pct')
    if iv is not None:
        iv = finite(iv, 'iv_pct')
        if iv == 0: iv = None  # Broker's unavailable-IV sentinel; IV is optional.
        elif iv < 0: raise ValueError('Invalid implied volatility')
    return dict(
        bid=bid, ask=ask, shares=int(shares), strike=strike, underlying_price=spot, expiration=expiry.isoformat(),
        days_to_expiry=dte, abs_delta=abs(delta), iv_pct=iv, **liquidity,
        spread_pct_of_mid=100 * (ask - bid) / mid,
        otm_pct=100 * (spot - strike) / spot,
        breakeven_before_costs=breakeven,
        breakeven_buffer_pct=100 * (spot - breakeven) / spot,
        premium_per_contract_before_costs=credit, cash_collateral=cash,
        gross_return_pct=100 * credit / cash,
        daily_gross_return_pct=100 * credit / cash / dte,
        annualized_gross_return_pct=100 * credit / cash * 365 / dte,
        max_profit_before_costs=credit, max_loss_before_costs=cash - credit,
        pnl_at_spot_minus_20_pct=credit - max(strike - spot * .8, 0) * shares,
        standard_contract=int(row.get('standard_type') == 'STANDARD' and shares == 100),
        not_suspended=int(row.get('suspension') is False),
        same_session_snapshot=int(updated.astimezone(NY).date() == session_date),
        snapshot_age_seconds=max(0, age),
        earnings_known=int(earnings is not None and row.get('earnings_calendar_complete') is True),
        days_expiry_before_earnings=days_before_earnings,
    )


def validate_rules():
    seen = set()
    for rule_id, metric, op, threshold in RULES:
        if rule_id in seen or op not in OPS: raise ValueError('Duplicate rule ID or invalid operator')
        seen.add(rule_id)
        if metric == 'expiration':
            if threshold is not None: iso_date(threshold)
        else: finite(threshold, 'Rule threshold')
        if metric not in METRICS: raise ValueError('Unknown rule metric: ' + str(metric))
    if not RULES: raise ValueError('At least one rule is required')
    trend_ids = set()
    if not TREND_RULES: raise ValueError('At least one trend rule is required')
    for rid, metric, op, threshold in TREND_RULES:
        if rid in trend_ids or op not in OPS or metric not in TREND_METRICS:
            raise ValueError('Invalid or duplicate trend rule')
        trend_ids.add(rid)
        finite(threshold, 'Trend threshold')
    for metric, direction in SORT_ORDER:
        if metric not in SORTABLE_METRICS: raise ValueError('Unknown sort metric: ' + str(metric))
        if direction not in ('asc', 'desc'): raise ValueError('Invalid sort direction')


def score_contract(values, underlying, configuration):
    """Transparent heuristic scores, independent of filter switches and peers.

    Stress loss is an expiry scenario, NOT expected loss or early-close value.
    Missing evidence is penalized and reported separately from observed risk.
    """
    p, weights = configuration['parameters'], configuration['weights']
    def bounded(number): return max(0., min(100., number))
    stress_price = values['underlying_price'] * (1-p['stress_drop_pct']/100)
    stress_pnl = values['premium_per_contract_before_costs'] - max(values['strike']-stress_price, 0)*values['shares']
    stress_loss_pct = 100*max(0, -stress_pnl)/values['cash_collateral']
    reference = underlying.get('reference_rules', [])
    trend_known = underlying['status'] == 'ok' and bool(reference)
    trend_score = (100*sum(not r['passed'] for r in reference)/len(reference)
                   if trend_known else p['unknown_risk_score'])
    spread_score = bounded(100*values['spread_pct_of_mid']/p['spread_high_pct'])
    oi_score = bounded(100*(1-values['open_interest']/p['open_interest_target']))
    depth_score = bounded(100*(1-values['bid_size']/p['bid_size_target']))
    earnings_known = bool(values['earnings_known'])
    earnings_score = (bounded(100*(1-values['days_expiry_before_earnings']/p['earnings_buffer_days']))
                      if earnings_known else p['unknown_risk_score'])
    raw = [
        ('delta', bounded(100*values['abs_delta']/p['delta_high']), True,
         f"|Delta|={values['abs_delta']:.4f}，满分参考 {p['delta_high']:g}；衡量敏感度，不是指派概率。"),
        ('stress_loss', bounded(100*stress_loss_pct/p['stress_loss_high_pct']), True,
         f"到期股价下跌 {p['stress_drop_pct']:g}% 时，费用前损益 ${stress_pnl:,.2f}，亏损占担保本金 {stress_loss_pct:.2f}%；满分参考 {p['stress_loss_high_pct']:g}%。"),
        ('trend', trend_score, trend_known,
         f"默认趋势参考 {sum(not r['passed'] for r in reference)} / {len(reference)} 项未通过；不随 Filter 开关变化。" if trend_known else '缺少可验证日线，使用未知风险惩罚分。'),
        ('liquidity', .5*spread_score+.25*oi_score+.25*depth_score, True,
         f"价差分 {spread_score:.2f} ×50% + 未平仓量不足分 {oi_score:.2f} ×25% + 买盘数量不足分 {depth_score:.2f} ×25%；报价数量不保证成交。"),
        ('earnings', earnings_score, earnings_known,
         f"财报在到期后 {values['days_expiry_before_earnings']} 天；跨财报为100分，间隔达到 {p['earnings_buffer_days']:g} 天为0分。" if earnings_known else '下次财报或日历完整性未知，使用未知风险惩罚分。'),
    ]
    total_weight = sum(weights.values())
    components = [dict(id=key, label=RISK_LABELS[key], score=score, known=known,
                       weight_pct=100*weights[key]/total_weight,
                       contribution=score*weights[key]/total_weight, explanation=detail)
                  for key, score, known, detail in raw]
    risk = bounded(sum(c['contribution'] for c in components))
    returns = bounded(100*values['daily_gross_return_pct']/p['daily_return_target_pct'])
    composite = p['return_weight']*returns + (1-p['return_weight'])*(100-risk)
    values.update(risk_score=risk, return_score=returns, composite_score=composite, stress_loss_pct=stress_loss_pct)
    return dict(model='heuristic_v1_unvalidated', components=components,
                evidence_coverage_pct=sum(c['weight_pct'] for c in components if c['known']),
                missing_components=[c['id'] for c in components if not c['known'] and weights[c['id']] > 0],
                stress_drop_pct=p['stress_drop_pct'], stress_pnl_before_costs=stress_pnl,
                return_contribution=p['return_weight']*returns,
                safety_contribution=(1-p['return_weight'])*(100-risk))


def scan(dataset, budget=None, configuration=None):
    config = resolve_configuration(configuration)
    filters = configured_rules(RULES, config['filters'])
    trend_filters = configured_rules(TREND_RULES, config['trend_filters'])
    order = config['sort_order']
    reference_earnings_buffer = next((value for rid, _, _, value in RULES if rid == 'earnings-buffer'), 3)
    if not isinstance(dataset, dict) or type(dataset.get('schema')) is not int or dataset['schema'] != 1:
        raise ValueError('Unsupported input schema')
    session = iso_date(dataset.get('session_date'))
    collected = timestamp(dataset.get('collected_at')).astimezone(timezone.utc)
    if not 0 <= (collected.astimezone(NY).date() - session).days <= 7:
        raise ValueError('Session date is future or more than seven days old')
    if budget is not None and finite(budget, 'Budget') <= 0:
        raise ValueError('Budget must be positive')
    rows = dataset.get('contracts')
    if not isinstance(rows, list): raise ValueError('contracts must be a list')
    codes = [row.get('code') if isinstance(row, dict) else None for row in rows]
    if any(not isinstance(code, str) for code in codes) or len(set(codes)) != len(codes):
        raise ValueError('Missing or duplicate contract codes')
    daily = dataset.get('daily_series', [])
    if not isinstance(daily, list): raise ValueError('daily_series must be a list')
    histories = {}
    for series in daily:
        if not isinstance(series, dict) or not isinstance(series.get('symbol'), str):
            raise ValueError('Daily series must identify its underlying symbol')
        if series['symbol'] in histories: raise ValueError('Duplicate daily series')
        histories[series['symbol']] = series
    trends = {}
    for symbol in sorted({r.get('symbol') for r in rows if isinstance(r, dict) and isinstance(r.get('symbol'), str)}):
        try:
            trends[symbol] = trend(histories.get(symbol), session, collected, trend_filters)
        except (ValueError, TypeError, KeyError, OverflowError, IndexError) as error:
            trends[symbol] = dict(symbol=symbol, status='invalid_data', allowed=False, error=str(error))
    results = []
    for row in rows:
        base = dict(code=row['code'], symbol=row.get('symbol'), expiration=row.get('expiration'))
        try:
            values = metrics(row, session, collected)
            underlying = trends[row['symbol']]
            values['trend_allowed'] = int(underlying['allowed'])
            tm = underlying.get('metrics', {})
            values['strike_below_20d_low_atr'] = ((tm['prior_20d_low'] - values['strike']) / tm['atr14']
                                                if tm.get('atr14', 0) > 0 else None)
            scoring = score_contract(values, underlying, config['scoring'])
            evidence = []
            for rule_id, metric, op, threshold in filters:
                if metric not in values: raise ValueError('Unknown rule metric: ' + metric)
                actual = values[metric]
                passed = actual is not None and OPS[op](actual, threshold)
                evidence.append(dict(id=rule_id, metric=metric, actual=actual, op=op,
                                     threshold=threshold, passed=passed))
            if budget is not None:
                evidence.append(dict(id='cash-budget', metric='cash_collateral', actual=values['cash_collateral'],
                                     op='<=', threshold=budget, passed=values['cash_collateral'] <= budget))
            eligible = all(rule['passed'] for rule in evidence)
            warnings = []
            if not values['earnings_known']: warnings.append('财报日期或日历完整性未验证')
            elif values['days_expiry_before_earnings'] < reference_earnings_buffer: warnings.append('合约跨越或临近已知财报日')
            if underlying['status'] != 'ok': warnings.append('历史日线无法验证')
            elif underlying.get('baseline_failed_rules'): warnings.append('标的未通过默认趋势检查')
            if not values['same_session_snapshot']: warnings.append('报价不属于当前交易日')
            results.append(dict(base, status='ok', eligible=eligible, metrics=values, scoring=scoring,
                                rules=evidence, failed_rules=[r['id'] for r in evidence if not r['passed']],
                                warnings=warnings,
                                trend_symbol=row['symbol'],
                                market_state=row.get('market_state', 'UNKNOWN'),
                                snapshot_update_time=row['snapshot_update_time'], earnings=row.get('earnings'),
                                live_review_ready=bool(eligible and not warnings and row.get('market_state') in ('MORNING', 'AFTERNOON')
                                    and values['snapshot_age_seconds'] <= LIVE_MAX_SNAPSHOT_AGE_SECONDS)))
        except (ValueError, TypeError, KeyError, OverflowError) as error:
            results.append(dict(base, status='invalid_data', eligible=False, live_review_ready=False, error=str(error)))
    ranked = sorted_candidates((row for row in results if row['eligible']), order)
    for index, row in enumerate(ranked, 1): row['rank'] = index
    # Separate incomplete event checks from full eligibility. A KNOWN earnings
    # conflict is excluded; an UNKNOWN date can appear only on this watchlist.
    watchlist = sorted_candidates((row for row in results if row['status'] == 'ok' and not row['eligible']
                        and row['metrics']['earnings_known'] == 0
                        and set(row['failed_rules']) <= EARNINGS_RULES), order)
    for index, row in enumerate(watchlist, 1): row['watchlist_rank'] = index
    valid = [row for row in results if row['status'] == 'ok']
    impacts = [dict(id=rid, excluded_count=sum(rid in row['failed_rules'] for row in valid),
                    qualified_without_filter=sum(set(row['failed_rules']) <= {rid} for row in valid)) for rid, _, _, _ in filters]
    previews = [dict(disabled_filters=sorted(group), qualified_count=sum(set(row['failed_rules']) <= group for row in valid))
                for group in ({'underlying-trend'}, set(EARNINGS_RULES), set(EARNINGS_RULES) | {'underlying-trend'})]
    return dict(
        schema=1, purpose='cash_secured_put_research_ranking', source=dataset.get('source'),
        session_date=session.isoformat(), collected_at=dataset['collected_at'],
        engine_version=ENGINE_VERSION, ruleset_version=RULESET_VERSION,
        engine_file_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        rules_sha256=fingerprint(config), dataset_sha256=fingerprint(dataset),
        assumption='One standard US equity/ETF put, fully cash secured, willing to accept shares; user suitability not established',
        cash_budget=budget, budget_checked=budget is not None,
        ranking_objective='Pass required data checks and enabled filters, then sort independently by sort_order',
        scoring_model=dict(version='heuristic_v1_unvalidated', configuration=config['scoring'],
            risk_direction='0 to 100; higher is riskier; not a probability or expected loss',
            risk_formula='sum(component_score * weight) / sum(weights)',
            return_formula='min(100, 100 * daily_gross_return_pct / daily_return_target_pct)',
            composite_formula='return_weight * return_score + (1 - return_weight) * (100 - risk_score)',
            limitations='Provisional correlated factors and subjective scales; no calibration, news, portfolio exposure or expected-return model. Zero stress loss is not zero overall risk.'),
        configuration=config, default_configuration=default_configuration(),
        disabled_filters=[rid for rid, option in config['filters'].items() if not option['enabled']],
        filter_impact=impacts, relaxation_preview=previews,
        sort_order=order, rules=filters, trend_rules=trend_filters, all_rules=RULES,
        all_trend_rules=TREND_RULES, underlyings=trends, total_contracts=len(rows),
        missing_quote_codes=dataset.get('missing_quote_codes', []),
        calendar_errors=dataset.get('calendar_errors', []),
        qualified_count=len(ranked), best_research_code=ranked[0]['code'] if ranked else None,
        ranked_codes=[row['code'] for row in ranked], results=results,
        ranked=ranked, earnings_unverified_watchlist=watchlist,
        best_watchlist_code=watchlist[0]['code'] if watchlist else None,
        limitations=[
            'Rule-selected research candidates; thresholds have not been backtested or validated.',
            'Daily trend indicators describe completed history; they do not estimate the probability of a future decline.',
            'Bid-based estimates are not fill guarantees. All returns and P/L exclude fees, slippage, taxes and cash interest.',
            'Simple annualization is a comparison scale, not a forecast or compounded return.',
            'Delta is price sensitivity, not an exact assignment or profit probability.',
            'Earnings are provider listings and may change; unknown dates fail enabled earnings filters and remain flagged when disabled.',
            'Snapshot timestamps do not guarantee bid freshness; market-closed / stale snapshots are research only.',
            'No portfolio concentration, issuer valuation, news or user-specific suitability assessment; no order execution.',
        ])


def recommend(dataset, budget=None, configuration=None, top_n=10):
    """Hard risk boundaries -> selected return/risk ranking -> strict Top N.

    This is a constrained research ranking, not expected profit or an investment
    suitability judgement. Every eligible contract is ranked; no soft score cutoff.
    """
    if type(top_n) is not int or top_n < 1: raise ValueError('top_n must be a positive integer')
    config = recommendation_configuration(configuration)
    report = scan(dataset, budget, config)
    ranked = report['ranked']
    views = {}
    for mode, order in RANKING_SORT_ORDERS.items():
        ordered = sorted_candidates(ranked, order)
        views[mode] = [row['code'] for row in ordered[:top_n]]
        for index, row in enumerate(ordered, 1): row[mode + '_rank'] = index
    by_expiry = {}
    for row in ranked: by_expiry.setdefault(row['expiration'], row)
    chosen = ranked[:top_n]
    recommendations = []
    for number, row in enumerate(chosen, 1):
        m = row['metrics']
        reasons = [
            f"通过当前全部风险边界，在 {len(ranked)} 个候选中排序第 {row['rank']}。",
            f"每张权利金 ${m['premium_per_contract_before_costs']:,.2f} ÷ 担保现金 ${m['cash_collateral']:,.2f} ÷ {m['days_to_expiry']} 天，日均毛收益率 {m['daily_gross_return_pct']:.4f}%。",
            f"行权价 ${m['strike']:,.2f}，较现价低 {m['otm_pct']:.2f}%；费用前盈亏平衡价 ${m['breakeven_before_costs']:,.2f}。",
            f"收益分 {m['return_score']:.2f}，风险分 {m['risk_score']:.2f}（越高越危险），综合分 {m['composite_score']:.2f}。评分为未校准的研究模型。",
        ]
        notes = list(row['warnings'])
        if not report['budget_checked']: notes.append('尚未提供单张现金预算，未判断担保资金是否适合个人账户')
        if not row['live_review_ready']: notes.append('仅按采集时点研究比较；交易前需复核风险并刷新报价')
        comparisons = [f"|Delta|={m['abs_delta']:.3f}，买卖价差为中间价的 {m['spread_pct_of_mid']:.2f}%。",
                       f"最大权利金收益 ${m['max_profit_before_costs']:,.2f}，股票归零时最大亏损 ${m['max_loss_before_costs']:,.2f}；不含费用。"]
        if row['rank'] != 1:
            comparisons.append(f"属于当前排序的 Top {len(chosen)}；其排序低于总体第一名 {ranked[0]['code']}。")
        scenarios = [dict(stock_change_pct=change,
                          stock_price=m['underlying_price']*(1+change/100),
                          pnl_before_costs=m['premium_per_contract_before_costs'] -
                          max(m['strike']-m['underlying_price']*(1+change/100), 0)*m['shares'])
                     for change in (0, -10, -20, -30, -100)]
        recommendations.append(dict(
            recommendation_rank=number, overall_rank=row['rank'], code=row['code'], symbol=row['symbol'],
            expiration=row['expiration'], strike=m['strike'], days_to_expiry=m['days_to_expiry'],
            bid=m['bid'], ask=m['ask'], premium_per_contract_before_costs=m['premium_per_contract_before_costs'],
            cash_collateral=m['cash_collateral'], daily_gross_return_pct=m['daily_gross_return_pct'],
            gross_return_pct=m['gross_return_pct'], annualized_gross_return_pct=m['annualized_gross_return_pct'],
            return_score=m['return_score'], risk_score=m['risk_score'], composite_score=m['composite_score'],
            return_rank=row['return_rank'], risk_rank=row['risk_rank'], balanced_rank=row['balanced_rank'],
            duration_rank=row['duration_rank'], cost_rank=row['cost_rank'],
            scoring=row['scoring'],
            breakeven_before_costs=m['breakeven_before_costs'], max_loss_before_costs=m['max_loss_before_costs'],
            reasons=reasons, tradeoffs=comparisons, risk_notes=notes, scenarios=scenarios,
            data_collected_at=report['collected_at'], snapshot_update_time=row['snapshot_update_time']))
    report.update(
        decision='candidates_found' if recommendations else 'no_candidates_within_boundaries',
        decision_summary=(f"风险边界内有 {len(ranked)} 个有效合约，返回 {len(recommendations)} 份到期日/行权价比较。"
                          if recommendations else '当前风险边界内没有有效合约；未放宽边界或补造候选。'),
        comparison_basis=dict(default_metric='daily_gross_return_pct', actual_sort_order=report['sort_order'],
            formula='100 * premium_per_contract_before_costs / cash_collateral / days_to_expiry',
            meaning='Average gross premium per calendar day on full strike cash collateral; assumes entire premium retained, not realized daily profit',
            selection_policy='First top_n contracts in the actual sort order, without expiration diversification'),
        top_n_requested=top_n, ranking_views=views,
        recommendations=recommendations, best_recommendation=recommendations[0] if recommendations else None,
        default_configuration=recommendation_configuration(),
        expiration_comparisons=[dict(expiration=expiry, best_code=row['code'], strike=row['metrics']['strike'],
                                     overall_rank=row['rank'], daily_gross_return_pct=row['metrics']['daily_gross_return_pct'])
                                for expiry, row in by_expiry.items()],
        boundary_origin='illustrative_basic_defaults' if configuration is None else 'explicit_configuration_over_basic_defaults',
        personal_suitability_assessed=False,
        ranking_objective='Pass explicit hard boundaries, rank every survivor by selected return/risk/composite metrics, and return strict Top N')
    return report


def main(argv=None):
    import sys
    if sys.stdout is not None and hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description='Standalone, editable cash-secured PUT research rules')
    parser.add_argument('input', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--budget', type=float, help='Maximum USD cash for ONE assigned contract; omitted means not checked')
    parser.add_argument('--config', type=Path, help='JSON with explicit filter toggles/thresholds and independent sort_order')
    parser.add_argument('--csv-output', type=Path, help='Export qualified candidates and the separate earnings-unverified watchlist')
    parser.add_argument('--top', type=int, default=10)
    parser.add_argument('--rank-by', choices=RANKING_SORT_ORDERS, help='Override sorting: duration, cost, return, risk or balanced; filters remain unchanged')
    parser.add_argument('--scan-only', action='store_true', help='Use the legacy full-filter scan without date/strike recommendations')
    args = parser.parse_args(argv)
    try:
        if args.top < 1: raise ValueError('--top must be positive')
        config = json.loads(args.config.read_text(encoding='utf-8')) if args.config else None
        if args.rank_by:
            config = resolve_configuration(config) if args.scan_only else recommendation_configuration(config)
            config['sort_order'] = [list(item) for item in RANKING_SORT_ORDERS[args.rank_by]]
        dataset = json.loads(args.input.read_text(encoding='utf-8'))
        report = scan(dataset, args.budget, config) if args.scan_only else recommend(dataset, args.budget, config, args.top)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, allow_nan=False, indent=2) + '\n', encoding='utf-8')
        if args.csv_output:
            import csv
            columns = ['category', 'rank', 'code', 'symbol', 'expiration', 'strike', 'bid', 'ask', 'days_to_expiry',
                       'abs_delta', 'otm_pct', 'spread_pct_of_mid', 'volume', 'open_interest',
                       'premium_per_contract_before_costs', 'cash_collateral', 'gross_return_pct',
                       'daily_gross_return_pct', 'annualized_gross_return_pct', 'breakeven_before_costs', 'max_loss_before_costs',
                       'return_score', 'risk_score', 'composite_score', 'stress_loss_pct', 'evidence_coverage_pct',
                       *[key + '_risk_score' for key in RISK_WEIGHTS],
                       'pnl_at_spot_minus_20_pct', 'live_review_ready', 'snapshot_update_time', 'blocked_rules',
                       'earnings_known', 'trend_allowed', 'warnings']
            args.csv_output.parent.mkdir(parents=True, exist_ok=True)
            with args.csv_output.open('w', encoding='utf-8', newline='') as stream:
                writer = csv.DictWriter(stream, fieldnames=columns, extrasaction='ignore')
                writer.writeheader()
                for category, candidates in [('qualified', report['ranked']), ('earnings_unverified', report['earnings_unverified_watchlist'])]:
                    for row in candidates:
                        writer.writerow(dict(row['metrics'], **{k: row[k] for k in ('code', 'symbol', 'expiration', 'live_review_ready', 'snapshot_update_time')},
                                             category=category, rank=row.get('rank', row.get('watchlist_rank')),
                                             evidence_coverage_pct=row['scoring']['evidence_coverage_pct'],
                                             **{c['id'] + '_risk_score': c['score'] for c in row['scoring']['components']},
                                             blocked_rules=','.join(row['failed_rules']), warnings='; '.join(row.get('warnings', []))))
        print(f'{report["qualified_count"]} / {report["total_contracts"]} contracts pass every rule; session {report["session_date"]}')
        print('Research ranking; gross estimates before costs. Refresh quotes and confirm earnings before any trade.')
        if not args.scan_only:
            print(report['decision_summary'])
            for choice in report['recommendations']:
                print(f"Choice {choice['recommendation_rank']}: {choice['expiration']} strike={choice['strike']:.2f} daily_gross={choice['daily_gross_return_pct']:.4f}% risk={choice['risk_score']:.2f} composite={choice['composite_score']:.2f}")
                for reason in choice['reasons'] + choice['tradeoffs'] + choice['risk_notes']: print('  ' + reason)
        for symbol, underlying in report['underlyings'].items():
            if underlying['status'] == 'ok':
                m = underlying['metrics']
                print(f'{symbol} trend={underlying["state"]} as_of={underlying["as_of"]} '
                      f'close={m["close"]:.2f} MA50={m["ma50"]:.2f} RSI14={m["rsi14"]:.1f} '
                      f'allowed={underlying["allowed"]} failed={",".join(underlying["failed_rules"])}')
            else: print(f'{symbol} trend unavailable: {underlying["error"]}')
        for row in report['ranked'][:args.top]:
            m = row['metrics']
            print(f'{row["rank"]:2} {row["code"]:27} bid={m["bid"]:.2f} DTE={m["days_to_expiry"]:2} '
                  f'abs_delta={m["abs_delta"]:.3f} premium=${m["premium_per_contract_before_costs"]:.0f} '
                  f'cash=${m["cash_collateral"]:.0f} annualized_gross={m["annualized_gross_return_pct"]:.2f}% '
                  f'live_review_ready={row["live_review_ready"]}')
        if report['earnings_unverified_watchlist']:
            print('\nWATCHLIST ONLY — all quote/risk rules pass; earnings are NOT verified:')
            for row in report['earnings_unverified_watchlist'][:args.top]:
                m = row['metrics']
                print(f'{row["watchlist_rank"]:2} {row["code"]:27} bid={m["bid"]:.2f} DTE={m["days_to_expiry"]:2} '
                      f'abs_delta={m["abs_delta"]:.3f} premium=${m["premium_per_contract_before_costs"]:.0f} '
                      f'cash=${m["cash_collateral"]:.0f} annualized_gross={m["annualized_gross_return_pct"]:.2f}% '
                      f'BLOCKED={",".join(row["failed_rules"])}')
    except (ValueError, TypeError, KeyError, OSError) as error:
        parser.exit(2, f'Scan failed: {error}\n')
    return 0


if __name__ == '__main__': raise SystemExit(main())
