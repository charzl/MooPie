"""Research orchestration shared by the desktop and CLI; no Qt or MCP imports."""
from datetime import date, datetime
import importlib.util
from pathlib import Path
import sys

from .market_collection import us_symbols
from .price_signals import dataset_signals


def load_rules():
    # Source installations always use the independently editable canonical file.
    source = Path(__file__).resolve().parents[3] / 'modules/put-screener/put_rules.py'
    bundled = Path(__file__).with_name('_bundled_put_rules.py')
    frozen = Path(getattr(sys, '_MEIPASS', '.')) / 'put_rules.py'
    path = next((p for p in (source, bundled, frozen) if p.is_file()), None)
    if path is None:
        raise RuntimeError('Put rule file is missing; reinstall moomoo-clients.')
    spec = importlib.util.spec_from_file_location('moomoo_research_rules', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def trend_report(payload, code, rules=None):
    rules = rules or load_rules()
    series = next((s for s in payload['daily_series'] if s['symbol'] == code), None)
    if not series or series.get('error'):
        raise ValueError('日线不可用：' + str((series or {}).get('error', '缺少日线')))
    evidence = rules.trend(series, date.fromisoformat(series['as_of']),
                           datetime.fromisoformat(payload['decision_cutoff']))
    evidence['outlook'] = rules.describe_trend(evidence)
    return evidence


def analyze_put_dataset(dataset, symbol, configuration=None, top_n=10):
    code = us_symbols([symbol])[0]
    owners = set(dataset.get('symbols', [])) | {r.get('symbol') for r in dataset.get('contracts', [])}
    if owners and owners != {code}: raise ValueError('Cached dataset does not match the requested stock')
    report = load_rules().recommend(dataset, configuration=configuration, top_n=top_n, per_symbol_limit=20)
    result = dict(action='put', symbol=code, collected_at=dataset['collected_at'],
                  report=report, input_dataset=dataset,
                  price_signals=dataset_signals(dataset, report['underlyings']))
    if 'data_access' in dataset:
        result['data_access'] = dataset['data_access']
    return result


def run_research(service, symbol, action, configuration=None, top_n=10):
    code = us_symbols([symbol])[0]
    rules = load_rules()
    if action == 'trend':
        payload = service.daily_bars([code])
        evidence = trend_report(payload, code, rules)
        result = dict(action=action, symbol=code, collected_at=payload['fetched_at'],
                      trend=evidence, price_signals=dataset_signals(payload, {code:evidence}))
        if 'data_access' in payload:
            result['data_access'] = payload['data_access']
        return result
    if action != 'put':
        raise ValueError('Unknown research action: ' + action)
    dataset = service.collect_put_dataset([code], months=3)
    return analyze_put_dataset(dataset, code, configuration, top_n)
