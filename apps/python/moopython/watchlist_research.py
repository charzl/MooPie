"""Watchlist research rendered in the same desktop report as a single stock."""
from datetime import datetime, timezone

from .market_payloads import assemble
from .research import load_rules
from .watchlist import run_watchlist


def _access(items):
    sources = {item.get('data_access', {}).get('source', 'saved') for item in items}
    members = [dict(symbol=item['symbol'], collected_at=item['collected_at'],
                    **{k: v for k, v in item.get('data_access', {}).items() if k != 'symbol'}) for item in items]
    return dict(source=next(iter(sources)) if len(sources) == 1 else 'mixed', members=members,
                reused_symbols=[item['symbol'] for item in items if item.get('data_access', {}).get('source')=='database'],
                fetched_symbols=[item['symbol'] for item in items if item.get('data_access', {}).get('source')=='OpenD'],
                note='Watchlist 合并研究；各股票保留自己的采集时间，不代表同时报价。')


def analyze_watchlist_dataset(dataset, configuration=None, top_n=10):
    report = load_rules().recommend(dataset, configuration=configuration, top_n=top_n, per_symbol_limit=20)
    return dict(action='put', symbol='Watchlist', query_scope='watchlist',
                symbols=dataset['symbols'], collected_at=dataset['collected_at'], report=report,
                input_dataset=dataset, data_access=dataset.get('data_access', {}),
                collection_errors=dataset.get('collection_errors', []))


def run_watchlist_research(service, values, action, configuration=None, top_n=10):
    batch = run_watchlist(service, values, action=action, top_n=top_n, configuration=configuration, raw_put=action=='put')
    if not batch['precheck']['passed']:
        issues = batch['precheck']['invalid'] + batch['precheck']['unverified']
        raise ValueError('Watchlist 预检查未通过：\n' + '\n'.join(
            f'{row.get("symbol", row["input"])}：{row["reason"]}' for row in issues))
    successes, errors = [], []
    for item in batch['results']:
        result = item[action]
        if 'error' in result:
            errors.append(dict(symbol=item['symbol'], error=result['error']))
        else:
            successes.append(result)
    if not successes:
        raise RuntimeError('Watchlist 全部查询失败：\n' + '\n'.join(f'{e["symbol"]}：{e["error"]}' for e in errors))
    access = _access(successes)
    if action == 'trend':
        return dict(action='trend', symbol='Watchlist', query_scope='watchlist',
                    symbols=batch['precheck']['valid_symbols'], items=successes, collection_errors=errors,
                    collected_at=max((item['collected_at'] for item in successes), key=datetime.fromisoformat), data_access=access)
    datasets = [item['input_dataset'] for item in successes]
    symbols = [item['symbol'] for item in successes]
    dataset = assemble(datasets, 'collect_put_dataset', dict(symbols=symbols))
    dataset.update(symbols=symbols, query_scope='watchlist', data_access=access, collection_errors=errors,
                   requested_symbols=batch['precheck']['valid_symbols'])
    result = analyze_watchlist_dataset(dataset, configuration, top_n)
    result['precheck'] = batch['precheck']
    return result
