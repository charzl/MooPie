"""Strict daily-bar inputs and an allowlisted declarative rule language."""
import hashlib
import json
import math
import operator
import re
from datetime import date
from importlib.resources import files

ENGINE_VERSION = '0.1.0'
OPS = {'>': operator.gt, '>=': operator.ge, '<': operator.lt,
       '<=': operator.le, '==': operator.eq}
METRICS = frozenset(('close', 'ma20', 'ma50', 'ma200', 'distance_ma50_pct',
                    'distance_ma200_pct', 'ma20_vs_ma50_pct', 'ma50_slope_5_pct',
                    'volume_ratio_20', 'rsi14', 'atr14', 'atr14_pct'))


def number(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(name + ' must be a finite number')
    return float(value)


def iso_date(value):
    if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
        raise ValueError('Date must be YYYY-MM-DD')
    return date.fromisoformat(value)


def validate_rules(config):
    if not isinstance(config, dict) or set(config) != {'schema', 'id', 'version', 'engine_major', 'description', 'rules'}:
        raise ValueError('Invalid ruleset fields')
    if type(config['schema']) is not int or config['schema'] != 1:
        raise ValueError('Unsupported rule schema')
    if type(config['engine_major']) is not int or config['engine_major'] != int(ENGINE_VERSION.split('.')[0]):
        raise ValueError('Incompatible engine major version')
    if not isinstance(config['version'], str) or not re.fullmatch(r'\d+\.\d+\.\d+', config['version']):
        raise ValueError('Invalid ruleset version')
    if not isinstance(config['id'], str) or not re.fullmatch(r'[a-z][a-z0-9-]{0,63}', config['id']):
        raise ValueError('Invalid ruleset ID')
    if not isinstance(config['description'], str):
        raise ValueError('Invalid description')
    rules = config['rules']
    if not isinstance(rules, list) or not 1 <= len(rules) <= 100:
        raise ValueError('Ruleset must contain 1 to 100 rules')
    seen = set()
    for rule in rules:
        if not isinstance(rule, dict) or set(rule) != {'id', 'metric', 'op', 'value', 'weight', 'required'}:
            raise ValueError('Invalid rule fields')
        if not isinstance(rule['id'], str) or not re.fullmatch(r'[a-z][a-z0-9-]{0,63}', rule['id']) or rule['id'] in seen:
            raise ValueError('Invalid or duplicate rule ID')
        seen.add(rule['id'])
        if not isinstance(rule['metric'], str) or rule['metric'] not in METRICS:
            raise ValueError('Unknown metric')
        if not isinstance(rule['op'], str) or rule['op'] not in OPS:
            raise ValueError('Unsupported operator')
        number(rule['value'], 'threshold')
        if number(rule['weight'], 'weight') <= 0 or type(rule['required']) is not bool:
            raise ValueError('Invalid weight or required flag')
    if not math.isfinite(sum(float(rule['weight']) for rule in rules)):
        raise ValueError('Invalid total weight')
    return config


def load_rules(path=None):
    if path is None:
        text = files('moomoo_rules').joinpath('rules/trend.json').read_text(encoding='utf-8')
    else:
        from pathlib import Path
        text = Path(path).read_text(encoding='utf-8')
    return validate_rules(json.loads(text))


def canonical_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def indicators(series, as_of):
    """Exactly one completed regular-session, adjusted OHLCV bar per date."""
    if not isinstance(series, dict):
        raise ValueError('Series must be an object')
    if series.get('interval') != '1d' or series.get('adjustment') != 'qfq' or series.get('session') != 'regular':
        raise ValueError('Require 1d/qfq/regular bars')
    symbol = series.get('symbol')
    if not isinstance(symbol, str) or not re.fullmatch(r'(US|HK|SH|SZ)\.[A-Z0-9][A-Z0-9._-]{0,31}', symbol):
        raise ValueError('Invalid symbol')
    bars = series.get('bars')
    if not isinstance(bars, list) or len(bars) < 200:
        raise ValueError('Need at least 200 completed trading-day bars')
    closes, volumes, ranges, gains, losses = [], [], [], [], []
    previous_date = None
    for bar in bars:
        if not isinstance(bar, dict) or bar.get('complete') is not True:
            raise ValueError('Incomplete daily bar')
        day = iso_date(bar.get('date'))
        if day > as_of or (previous_date is not None and day <= previous_date):
            raise ValueError('Future, duplicate or unordered bar')
        previous_date = day
        op, high, low, close, volume = [number(bar.get(k), k) for k in ('open', 'high', 'low', 'close', 'volume')]
        if min(op, high, low, close) <= 0 or volume < 0 or not low <= min(op, close) <= max(op, close) <= high:
            raise ValueError('Invalid OHLCV range')
        if closes:
            delta = close - closes[-1]
            gains.append(max(delta, 0)); losses.append(max(-delta, 0))
            ranges.append(max(high - low, abs(high - closes[-1]), abs(low - closes[-1])))
        closes.append(close); volumes.append(volume)
    if previous_date != as_of:
        raise ValueError('Stale series: final bar must match as_of trading date')
    # Baseline excludes the current bar; a zero-volume baseline cannot support a ratio.
    volume_mean = sum(volumes[-21:-1]) / 20
    if volume_mean <= 0:
        raise ValueError('Insufficient nonzero volume history')
    ma20, ma50, ma200 = (sum(closes[-n:]) / n for n in (20, 50, 200))
    previous_ma50 = sum(closes[-55:-5]) / 50
    # Wilder smoothing seeded with the first 14 deltas / true ranges.
    def wilder(values):
        average = sum(values[:14]) / 14
        for value in values[14:]:
            average = (13 * average + value) / 14
        return average
    gain, loss, atr = wilder(gains), wilder(losses), wilder(ranges)
    rsi = 50.0 if gain == loss == 0 else (100.0 if loss == 0 else 100 - 100 / (1 + gain / loss))
    result = dict(close=closes[-1], ma20=ma20, ma50=ma50, ma200=ma200,
                  distance_ma50_pct=100 * (closes[-1] / ma50 - 1),
                  distance_ma200_pct=100 * (closes[-1] / ma200 - 1),
                  ma20_vs_ma50_pct=100 * (ma20 / ma50 - 1),
                  ma50_slope_5_pct=100 * (ma50 / previous_ma50 - 1),
                  volume_ratio_20=volumes[-1] / volume_mean, rsi14=rsi,
                  atr14=atr, atr14_pct=100 * atr / closes[-1])
    for key, value in result.items():
        number(value, key)
    return result


def evaluate(series, config, as_of):
    config = validate_rules(config)
    day = iso_date(as_of)
    values = indicators(series, day)
    evidence = []
    for rule in config['rules']:
        actual = values[rule['metric']]
        passed = OPS[rule['op']](actual, rule['value'])
        evidence.append(dict(rule_id=rule['id'], metric=rule['metric'], actual=actual,
                             operator=rule['op'], threshold=rule['value'], passed=passed,
                             required=rule['required'], points=rule['weight'] if passed else 0,
                             max_points=rule['weight']))
    eligible = all(row['passed'] for row in evidence if row['required'])
    return dict(symbol=series['symbol'], as_of=as_of, status='ok', eligible=eligible,
                score=100 * (sum(row['points'] for row in evidence) / sum(row['max_points'] for row in evidence)),
                score_meaning='rule_match_percent_not_return_or_probability', metrics=values,
                rules=evidence, engine_version=ENGINE_VERSION, ruleset_id=config['id'],
                ruleset_version=config['version'], ruleset_sha256=canonical_hash(config),
                data_sha256=canonical_hash(series), data_source=series.get('source', 'unspecified'),
                adjustment='qfq', interval='1d', session='regular', bar_count=len(series['bars']))


def scan(dataset, config):
    validate_rules(config)
    if not isinstance(dataset, dict) or type(dataset.get('schema')) is not int or dataset.get('schema') != 1:
        raise ValueError('Unsupported dataset schema')
    day = dataset.get('as_of'); iso_date(day)
    series = dataset.get('series')
    if not isinstance(series, list) or not series:
        raise ValueError('Dataset must contain series')
    symbols = [item.get('symbol') if isinstance(item, dict) else None for item in series]
    if any(not isinstance(s, str) for s in symbols) or len(set(symbols)) != len(symbols):
        raise ValueError('Invalid or duplicate series symbols')
    results = []
    for item in series:
        try:
            results.append(evaluate(item, config, day))
        except (ValueError, TypeError, KeyError, OverflowError) as error:
            results.append(dict(symbol=item['symbol'], as_of=day, status='invalid_data',
                                eligible=False, score=None, error=str(error)))
    candidates = sorted((r for r in results if r['status'] == 'ok' and r['eligible']),
                        key=lambda row: (-row['score'], row['symbol']))
    return dict(schema=1, as_of=day, engine_version=ENGINE_VERSION, ruleset_id=config['id'],
                ruleset_version=config['version'], ruleset_sha256=canonical_hash(config),
                dataset_sha256=canonical_hash(dataset), results=results,
                ranked_symbols=[r['symbol'] for r in candidates],
                limitations=['Experimental rules; not a validated investment strategy.',
                             'No news, fundamentals, benchmark-relative strength, or order execution.',
                             'Input adapter must verify trading calendar, session completion and corporate-action adjustment.'])
