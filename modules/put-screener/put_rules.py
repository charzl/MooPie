"""Editable, standalone cash-secured PUT research rules. Python standard library only.

Edit TREND_RULES / RULES / SORT_ORDER below, increase RULESET_VERSION, and rerun.
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


ENGINE_VERSION = '0.2.1'
RULESET_VERSION = '1.1.0'
# Initial research thresholds, not calibrated probabilities or backtested signals.
# All must pass BEFORE comparing put premiums. Oversold alone is not a buy signal.
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
]
# Among contracts passing EVERY rule, maximize simple annualized gross premium
# on full strike cash collateral; ties favor tighter spreads / lower delta.
SORT_ORDER = [('annualized_gross_return_pct', 'desc'), ('spread_pct_of_mid', 'asc'), ('abs_delta', 'asc')]
LIVE_MAX_SNAPSHOT_AGE_SECONDS = 900
OPS = {'>': operator.gt, '>=': operator.ge, '<': operator.lt,
       '<=': operator.le, '==': operator.eq}
NY = ZoneInfo('America/New_York')
METRICS = frozenset(('bid', 'ask', 'shares', 'strike', 'underlying_price', 'days_to_expiry',
    'abs_delta', 'iv_pct', 'volume', 'open_interest', 'bid_size', 'spread_pct_of_mid', 'otm_pct',
    'breakeven_before_costs', 'breakeven_buffer_pct', 'premium_per_contract_before_costs',
    'cash_collateral', 'gross_return_pct', 'annualized_gross_return_pct', 'max_profit_before_costs',
    'max_loss_before_costs', 'pnl_at_spot_minus_20_pct', 'standard_contract', 'not_suspended',
    'same_session_snapshot', 'snapshot_age_seconds', 'earnings_known', 'days_expiry_before_earnings',
    'trend_allowed', 'strike_below_20d_low_atr'))
TREND_METRICS = frozenset(('distance_to_ma50_pct', 'ma50_slope_5d_pct', 'breakdown_20d',
                          'rsi14', 'macd_histogram_change'))
EARNINGS_RULES = frozenset(('earnings-checked', 'earnings-buffer'))


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


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


def trend(series, session_date, collected_at):
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
    evidence = [dict(id=rid, metric=key, actual=values[key], op=op, threshold=threshold,
                     passed=OPS[op](values[key], threshold)) for rid, key, op, threshold in TREND_RULES]
    failed = [r['id'] for r in evidence if not r['passed']]
    state = ('downtrend' if last < values['ma50'] and values['ma50_slope_5d_pct'] < 0
             else 'uptrend' if not failed else 'mixed_or_weakening')
    return dict(symbol=series['symbol'], status='ok', as_of=as_of.isoformat(),
                available_at=series['available_at'], bar_count=len(bars), state=state,
                allowed=not failed, metrics=values, rules=evidence, failed_rules=failed)


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
    return dict(heading=heading, horizon='未来 5–20 个交易日的条件判断', reasons=reasons,
        levels=[dict(label='此前 20 日低点（跌破后关注收复）' if m['breakdown_20d'] else '此前 20 日低点', value=m['prior_20d_low']),
                dict(label='此前 60 日低点', value=m['prior_60d_low']),
                dict(label='MA20', value=m['ma20']), dict(label='MA50', value=m['ma50'])],
        change_condition='站上 MA50、均线止跌且 MACD 动能改善时，偏弱判断才有改善依据；跌破前低则下行压力增加。',
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
        if iv <= 0: raise ValueError('Invalid implied volatility')
    return dict(
        bid=bid, ask=ask, shares=int(shares), strike=strike, underlying_price=spot,
        days_to_expiry=dte, abs_delta=abs(delta), iv_pct=iv, **liquidity,
        spread_pct_of_mid=100 * (ask - bid) / mid,
        otm_pct=100 * (spot - strike) / spot,
        breakeven_before_costs=breakeven,
        breakeven_buffer_pct=100 * (spot - breakeven) / spot,
        premium_per_contract_before_costs=credit, cash_collateral=cash,
        gross_return_pct=100 * credit / cash,
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
        finite(threshold, 'Rule threshold')
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
        if metric not in METRICS: raise ValueError('Unknown sort metric: ' + str(metric))
        if direction not in ('asc', 'desc'): raise ValueError('Invalid sort direction')


def scan(dataset, budget=None):
    validate_rules()
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
            trends[symbol] = trend(histories.get(symbol), session, collected)
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
            evidence = []
            for rule_id, metric, op, threshold in RULES:
                if metric not in values: raise ValueError('Unknown rule metric: ' + metric)
                actual = values[metric]
                passed = actual is not None and OPS[op](actual, threshold)
                evidence.append(dict(id=rule_id, metric=metric, actual=actual, op=op,
                                     threshold=threshold, passed=passed))
            if budget is not None:
                evidence.append(dict(id='cash-budget', metric='cash_collateral', actual=values['cash_collateral'],
                                     op='<=', threshold=budget, passed=values['cash_collateral'] <= budget))
            eligible = all(rule['passed'] for rule in evidence)
            results.append(dict(base, status='ok', eligible=eligible, metrics=values,
                                rules=evidence, failed_rules=[r['id'] for r in evidence if not r['passed']],
                                trend_symbol=row['symbol'],
                                market_state=row.get('market_state', 'UNKNOWN'),
                                snapshot_update_time=row['snapshot_update_time'], earnings=row.get('earnings'),
                                live_review_ready=bool(eligible and row.get('market_state') in ('MORNING', 'AFTERNOON')
                                    and values['snapshot_age_seconds'] <= LIVE_MAX_SNAPSHOT_AGE_SECONDS)))
        except (ValueError, TypeError, KeyError, OverflowError) as error:
            results.append(dict(base, status='invalid_data', eligible=False, live_review_ready=False, error=str(error)))
    def sort_key(row):
        return tuple((-1 if direction == 'desc' else 1) * finite(row['metrics'].get(metric), metric)
                     for metric, direction in SORT_ORDER) + (row['code'],)
    ranked = sorted((row for row in results if row['eligible']), key=sort_key)
    for index, row in enumerate(ranked, 1): row['rank'] = index
    # Separate incomplete event checks from full eligibility. A KNOWN earnings
    # conflict is excluded; an UNKNOWN date can appear only on this watchlist.
    watchlist = sorted((row for row in results if row['status'] == 'ok' and not row['eligible']
                        and row['metrics']['earnings_known'] == 0
                        and set(row['failed_rules']) <= EARNINGS_RULES), key=sort_key)
    for index, row in enumerate(watchlist, 1): row['watchlist_rank'] = index
    return dict(
        schema=1, purpose='cash_secured_put_research_ranking', source=dataset.get('source'),
        session_date=session.isoformat(), collected_at=dataset['collected_at'],
        engine_version=ENGINE_VERSION, ruleset_version=RULESET_VERSION,
        engine_file_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        rules_sha256=fingerprint(dict(rules=RULES, trend_rules=TREND_RULES, sort=SORT_ORDER)), dataset_sha256=fingerprint(dataset),
        assumption='One standard US equity/ETF put, fully cash secured, willing to accept shares; user suitability not established',
        cash_budget=budget, budget_checked=budget is not None,
        ranking_objective='Pass every hard rule, then sort lexicographically by sort_order; not an expected-return prediction',
        sort_order=SORT_ORDER, rules=RULES, trend_rules=TREND_RULES, underlyings=trends, total_contracts=len(rows),
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
            'Earnings are provider listings and may change; unknown dates fail the earnings rules.',
            'Snapshot timestamps do not guarantee bid freshness; market-closed / stale snapshots are research only.',
            'No portfolio concentration, issuer valuation, news or user-specific suitability assessment; no order execution.',
        ])


def main(argv=None):
    parser = argparse.ArgumentParser(description='Standalone, editable cash-secured PUT research rules')
    parser.add_argument('input', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--budget', type=float, help='Maximum USD cash for ONE assigned contract; omitted means not checked')
    parser.add_argument('--csv-output', type=Path, help='Export qualified candidates and the separate earnings-unverified watchlist')
    parser.add_argument('--top', type=int, default=10)
    args = parser.parse_args(argv)
    try:
        if args.top < 1: raise ValueError('--top must be positive')
        report = scan(json.loads(args.input.read_text()), args.budget)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, allow_nan=False, indent=2) + '\n')
        if args.csv_output:
            import csv
            columns = ['category', 'rank', 'code', 'symbol', 'expiration', 'bid', 'ask', 'days_to_expiry',
                       'abs_delta', 'otm_pct', 'spread_pct_of_mid', 'volume', 'open_interest',
                       'premium_per_contract_before_costs', 'cash_collateral', 'gross_return_pct',
                       'annualized_gross_return_pct', 'breakeven_before_costs', 'max_loss_before_costs',
                       'pnl_at_spot_minus_20_pct', 'live_review_ready', 'snapshot_update_time', 'blocked_rules']
            args.csv_output.parent.mkdir(parents=True, exist_ok=True)
            with args.csv_output.open('w', encoding='utf-8', newline='') as stream:
                writer = csv.DictWriter(stream, fieldnames=columns, extrasaction='ignore')
                writer.writeheader()
                for category, candidates in [('qualified', report['ranked']), ('earnings_unverified', report['earnings_unverified_watchlist'])]:
                    for row in candidates:
                        writer.writerow(dict(row['metrics'], **{k: row[k] for k in ('code', 'symbol', 'expiration', 'live_review_ready', 'snapshot_update_time')},
                                             category=category, rank=row.get('rank', row.get('watchlist_rank')),
                                             blocked_rules=','.join(row['failed_rules'])))
        print(f'{report["qualified_count"]} / {report["total_contracts"]} contracts pass every rule; session {report["session_date"]}')
        print('Research ranking; gross estimates before costs. Refresh quotes and confirm earnings before any trade.')
        for symbol, underlying in report['underlyings'].items():
            if underlying['status'] == 'ok':
                m = underlying['metrics']
                print(f'{symbol} trend={underlying["state"]} as_of={underlying["as_of"]} '
                      f'close={m["close"]:.2f} MA50={m["ma50"]:.2f} RSI14={m["rsi14"]:.1f} '
                      f'allowed={underlying["allowed"]} failed={",".join(underlying["failed_rules"])}')
            else: print(f'{symbol} trend blocked: {underlying["error"]}')
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
