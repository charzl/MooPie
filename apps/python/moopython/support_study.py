"""Prefix-only support event study and frozen-zone daily lifecycle replay."""
from copy import deepcopy
from datetime import date
import hashlib
import json
from math import isfinite
from statistics import mean, median

from .price_signals import PARAMETERS as ZONE_PARAMETERS, SIGNAL_VERSION, confirmed_zones

VERSION = '1.0.0'
PARAMETERS = dict(warmup_bars=205, horizons=[5, 10, 20], separation_bars=20,
                  minimum_summary_samples=20, break_basis='daily_close_below_lower_edge',
                  reference_basis='touch_day_close', selection='previous_close_nearest_support')
BLOCKED = {'basis_changed', 'history_gap'}


def _hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     allow_nan=False).encode()).hexdigest()


def _bar_key(bar):
    return [bar[key] for key in ('date', 'open', 'high', 'low', 'close', 'volume')]


def unavailable(symbol, reason):
    return dict(version=VERSION, symbol=symbol, status='unavailable', reason=str(reason))


def _validate(series, trend):
    if not series or trend.get('status') != 'ok':
        raise ValueError('需要已通过趋势校验的日线')
    bars = series['bars']
    if ((series.get('interval'), series.get('adjustment'), series.get('session')) != ('1d', 'qfq', 'regular')
            or series['symbol'] != trend['symbol'] or series['as_of'] != trend['as_of']
            or len(bars) != trend['bar_count'] or len(bars) < PARAMETERS['warmup_bars']):
        raise ValueError('日线与已验证趋势证据不一致')
    days = [row['date'] for row in bars]
    if days != sorted(set(days)) or days != series.get('calendar_dates') or days[-1] != series['as_of']:
        raise ValueError('日线日期存在缺失、重复或顺序错误')
    for bar in bars:
        date.fromisoformat(bar['date'])
        values = [bar[key] for key in ('open', 'high', 'low', 'close', 'volume')]
        if (bar.get('complete') is not True or any(type(value) not in (int, float) or not isfinite(value)
                                                  for value in values)):
            raise ValueError('日线包含未完成或无效数据')
        o, h, l, c, v = values
        if min(o, h, l, c) <= 0 or v < 0 or not l <= min(o, c) <= max(o, c) <= h:
            raise ValueError('日线 OHLCV 无效')
    return bars


def _outcome(bars, index, zone, horizon):
    observed = bars[index:min(index+horizon+1, len(bars))]
    broken = next((bar['date'] for bar in observed if bar['close'] < zone['low']), None)
    result = dict(horizon=horizon, status='pending', observed_bars=len(observed)-1,
                  first_break_date=broken, close_return_pct=None,
                  max_rise_pct=None, max_drop_pct=None, end_date=None)
    if index+horizon >= len(bars):
        return result
    reference = bars[index]['close']
    forward = bars[index+1:index+horizon+1]
    result.update(status='complete', end_date=forward[-1]['date'],
                  close_return_pct=100*(forward[-1]['close']/reference-1),
                  max_rise_pct=max(0, 100*(max(bar['high'] for bar in forward)/reference-1)),
                  max_drop_pct=min(0, 100*(min(bar['low'] for bar in forward)/reference-1)))
    return result


def _backtest(bars, candidates):
    samples, next_eligible = [], PARAMETERS['warmup_bars']
    for index in range(PARAMETERS['warmup_bars'], len(bars)):
        if index < next_eligible or not candidates[index-1]:
            continue
        zone = candidates[index-1][0]
        # Include gap-through failures; no limit-order fill is assumed.
        if bars[index-1]['close'] <= zone['high'] or bars[index]['low'] > zone['high']:
            continue
        samples.append(dict(signal_date=bars[index-1]['date'], touch_date=bars[index]['date'],
                            reference_price=bars[index]['close'], zone=deepcopy(zone),
                            gap_through=bars[index]['high'] < zone['low'],
                            outcomes=[_outcome(bars, index, zone, horizon)
                                      for horizon in PARAMETERS['horizons']]))
        next_eligible = index+PARAMETERS['separation_bars']+1
    summaries = []
    for horizon in PARAMETERS['horizons']:
        outcomes = [outcome for sample in samples for outcome in sample['outcomes']
                    if outcome['horizon'] == horizon and outcome['status'] == 'complete']
        returns = [outcome['close_return_pct'] for outcome in outcomes]
        summaries.append(dict(horizon=horizon, complete=len(outcomes), pending=len(samples)-len(outcomes),
                              positive=sum(value > 0 for value in returns),
                              negative=sum(value < 0 for value in returns),
                              flat=sum(value == 0 for value in returns),
                              mean_return_pct=mean(returns) if returns else None,
                              median_return_pct=median(returns) if returns else None,
                              median_max_rise_pct=median(o['max_rise_pct'] for o in outcomes) if outcomes else None,
                              median_max_drop_pct=median(o['max_drop_pct'] for o in outcomes) if outcomes else None,
                              worst_drop_pct=min(o['max_drop_pct'] for o in outcomes) if outcomes else None,
                              broken=sum(o['first_break_date'] is not None for o in outcomes),
                              small_sample=len(outcomes) < PARAMETERS['minimum_summary_samples']))
    return dict(status='ok', sample_count=len(samples), summaries=summaries, samples=samples,
                first_test_date=bars[PARAMETERS['warmup_bars']]['date']
                                if len(bars) > PARAMETERS['warmup_bars'] else None)


def _event(record, kind, bar, **extra):
    record['events'].append(dict(kind=kind, date=bar['date'], close=bar['close'], **extra))


def advance_zone(record, bar):
    """Advance a frozen region with one later completed daily bar, idempotently."""
    if record['state'] in BLOCKED or bar['date'] <= record['last_evaluated']:
        return
    low, high = record['low'], record['high']
    contact = bar['low'] <= high and bar['high'] >= low
    new_contact = contact and not record['in_contact']
    close, old_state, old_phase = bar['close'], record['state'], record['phase']
    if record['phase'] == 'support':
        if new_contact:
            record['tests'] += 1
            _event(record, 'test', bar)
        if close < low:
            record['state'], record['phase'] = 'broken', 'broken'
            record['breaks'] += 1
            _event(record, 'break', bar, gap_through=bar['high'] < low)
        elif contact:
            record['state'] = 'held' if close > high else 'testing'
            if close > high and (new_contact or old_state == 'testing'):
                _event(record, 'held', bar)
        elif old_state == 'testing' and close > high:
            record['state'] = 'held'
            _event(record, 'held', bar)
    else:
        if close > high:
            record['state'], record['phase'] = 'reclaimed', 'support'
            _event(record, 'reclaim', bar)
        elif contact:
            if new_contact:
                record['resistance_tests'] += 1
                _event(record, 'resistance_test', bar)
            record['state'] = 'resistance' if close < low else 'broken_retest'
            if close < low and (new_contact or old_state == 'broken_retest'):
                _event(record, 'resistance', bar)
        elif old_state == 'broken_retest' and close < low:
            record['state'] = 'resistance'
            _event(record, 'resistance', bar)
    record['in_contact'] = contact if old_phase == record['phase'] else False
    record['last_evaluated'] = bar['date']
    record['last_close'] = close


def _lifecycles(bars, candidates, symbol, previous):
    records = []
    notices = deepcopy(previous['lifecycle']['notices']) if previous else []
    start = PARAMETERS['warmup_bars']-1
    basis_id = _hash([_bar_key(bar) for bar in bars[:PARAMETERS['warmup_bars']]])
    if previous:
        records = deepcopy(previous['lifecycle']['records'])
        old_bars = {bar['date']: _bar_key(bar) for bar in previous['input_series']['bars']}
        changed = [bar['date'] for bar in bars if bar['date'] in old_bars
                   and old_bars[bar['date']] != _bar_key(bar)]
        positions = {bar['date']: i for i, bar in enumerate(bars)}
        problem = 'basis_changed' if changed else 'history_gap' if previous['as_of'] not in positions else None
        if problem:
            notices.append(dict(kind=problem, dates=changed, detected_at=bars[-1]['date']))
            basis_id = _hash([basis_id, previous['basis_id'], problem,
                              [_bar_key(bar) for bar in bars if bar['date'] <= previous['as_of']]])
            for record in records:
                if record['state'] not in BLOCKED:
                    record['state'] = problem
                    record['stopped_at'] = bars[-1]['date']
                    record['events'].append(dict(kind=problem, date=bars[-1]['date'],
                                                 close=bars[-1]['close']))
        else:
            start = positions[previous['as_of']]+1
            basis_id = previous['basis_id']
    for index in range(start, len(bars)):
        bar = bars[index]
        for record in records:
            advance_zone(record, bar)
        for zone in candidates[index]:
            dates = {item['date'] for item in zone['evidence']}
            matches = [record for record in records if record['state'] not in BLOCKED
                       and record['detected_at'] <= bar['date']
                       and (dates.intersection(item['date'] for item in record['evidence'])
                            or (record['phase'] == 'support' and record['low'] <= zone['center'] <= record['high']))]
            if matches:
                record = max(matches, key=lambda item: item['detected_at'])
                known = {item['date'] for item in record['evidence']}
                record['evidence'].extend(deepcopy(item) for item in zone['evidence']
                                          if item['date'] not in known and record['low'] <= item['price'] <= record['high'])
                continue
            seed = zone['evidence'][0]
            record = dict(zone_id=_hash([symbol, basis_id, bar['date'], seed['date'], zone['low'], zone['high']])[:20],
                          low=zone['low'], high=zone['high'], center=zone['center'],
                          detected_at=bar['date'], formed_at=min(item['confirmed_at'] for item in zone['evidence']),
                          evidence=deepcopy(zone['evidence']), state='active', phase='support',
                          tests=0, breaks=0, resistance_tests=0, in_contact=False,
                          last_evaluated=bar['date'], last_close=bar['close'], events=[])
            _event(record, 'created', bar)
            records.append(record)
    return dict(status='ok', records=records, notices=notices,
                tracking_start=previous['lifecycle']['tracking_start'] if previous else bars[PARAMETERS['warmup_bars']-1]['date']), basis_id


def support_study(series, trend, *, previous=None, rules=None):
    """Reuse validated input, reconstruct past definitions, retain frozen history."""
    symbol = trend.get('symbol')
    try:
        bars = _validate(series, trend)
        if rules is None:
            from .research import load_rules
            rules = load_rules()
        definition = dict(version=VERSION, signal_version=SIGNAL_VERSION,
                          zone_parameters=dict(ZONE_PARAMETERS), parameters=deepcopy(PARAMETERS),
                          engine_version=rules.ENGINE_VERSION)
        definition_key = _hash(definition)
        if (not previous or previous.get('status') != 'ok' or previous.get('symbol') != symbol
                or previous.get('definition_key') != definition_key or previous['as_of'] > series['as_of']):
            previous = None
        candidates = [[] for _ in bars]
        true_ranges = [max(bar['high']-bar['low'], abs(bar['high']-prior['close']),
                           abs(bar['low']-prior['close'])) for prior, bar in zip(bars, bars[1:])]
        for index in range(PARAMETERS['warmup_bars']-1, len(bars)):
            atr = rules.wilder(true_ranges[:index])
            if atr > 0:
                candidates[index] = confirmed_zones(bars[:index+1], bars[index]['close'], atr)['support_zones']
        lifecycle, basis_id = _lifecycles(bars, candidates, symbol, previous)
        input_hash = _hash(dict(symbol=symbol, bars=[_bar_key(bar) for bar in bars],
                                adjustment=series['adjustment'], definition_key=definition_key))
        continued_from = None
        if previous:
            continued_from = (previous.get('continued_from') if previous['input_hash'] == input_hash else
                              dict(as_of=previous['as_of'], input_hash=previous['input_hash'],
                                   definition_key=previous['definition_key']))
        return dict(status='ok', symbol=symbol, as_of=series['as_of'], version=VERSION,
                    definition_key=definition_key, definition=definition, input_hash=input_hash,
                    input_series=deepcopy(series), basis_id=basis_id,
                    continued_from=continued_from,
                    source='historical_reconstruction_current_qfq_daily',
                    ranking_effect='none', backtest=_backtest(bars, candidates), lifecycle=lifecycle)
    except (ValueError, KeyError, TypeError, IndexError) as error:
        return unavailable(symbol, error)
