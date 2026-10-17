"""JSON watchlists, whole-list prechecks and per-stock research orchestration."""
from datetime import datetime, timezone
from collections import deque
import json
from pathlib import Path
import re
import sys

from .options import option_symbol
from .market_repository import CacheMissError
from .research import load_rules, run_research, trend_report


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result: raise ValueError(f'JSON 出现重复字段：{key}')
        result[key] = value
    return result


def _constant(value):
    raise ValueError(f'JSON 不支持 {value}')


def load_watchlist(path, *, allow_empty=False):
    value = json.loads(Path(path).read_text(encoding='utf-8-sig'),
                       object_pairs_hook=_object, parse_constant=_constant)
    if isinstance(value, dict):
        if set(value) != {'symbols'}:
            raise ValueError('股票列表对象只接受 symbols 字段，例如 {"symbols":["AVGO","NVDA"]}')
        value = value['symbols']
    if not isinstance(value, list) or not value and not allow_empty:
        raise ValueError('symbols 必须是非空 JSON 数组')
    return value


def normalize_stock(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError('股票代码必须是非空字符串')
    code = option_symbol(value)
    if not re.fullmatch(r'US\.[A-Z][A-Z0-9]*(?:[._-][A-Z0-9]+)*', code):
        raise ValueError('当前仅支持 US 股票 / ETF 代码，例如 AVGO、US.NVDA、BRK.B')
    if re.search(r'\d{6}[CP]\d+$', code):
        raise ValueError('请填写股票 / ETF 代码，不要填写期权合约代码')
    return code


def _finish_precheck(entries):
    unique = [row for row in entries if row['status'] != 'duplicate']
    valid = [row['symbol'] for row in unique if row['status'] == 'valid']
    invalid = [row for row in unique if row['status'] in ('invalid', 'invalid_format')]
    unverified = [row for row in unique if row['status'] in ('unverified', 'not_checked')]
    return dict(passed=bool(valid) and not invalid and not unverified, entries=entries,
                valid_symbols=valid, invalid=invalid, unverified=unverified,
                duplicates=[row for row in entries if row['status'] == 'duplicate'])


def precheck(service, values):
    if not isinstance(values, list) or not values:
        raise ValueError('股票列表不能为空')
    entries, seen = [], {}
    for index, value in enumerate(values, 1):
        row = dict(index=index, input=value)
        try:
            row['symbol'] = code = normalize_stock(value)
            if code in seen:
                row.update(status='duplicate', duplicate_of=seen[code], reason='重复代码，只分析一次')
            else:
                seen[code] = index
                row.update(status='not_checked', reason='尚未查询证券基本资料')
        except ValueError as error:
            row.update(status='invalid_format', reason=str(error))
        entries.append(row)
    # No database/SDK activity until the entire file passes local validation.
    if any(row['status'] == 'invalid_format' for row in entries):
        return _finish_precheck(entries)
    pending = [row for row in entries if row['status'] == 'not_checked']
    batches = deque(pending[start:start+200] for start in range(0, len(pending), 200))
    while batches:
        batch = batches.popleft()
        codes = [row['symbol'] for row in batch]
        try:
            payload = service.basic_info(codes)
            rows = payload.get('rows')
            if not isinstance(rows, list): raise RuntimeError('证券基本资料返回格式错误')
            by_code = {}
            for item in rows:
                if not isinstance(item, dict): raise RuntimeError('证券基本资料包含无效记录')
                code = item.get('code')
                if code not in codes or code in by_code:
                    raise RuntimeError('证券基本资料包含非请求代码或重复代码')
                by_code[code] = item
        except CacheMissError as error:
            if len(batch) > 1:
                # One uncached code must not hide verification evidence already
                # available for other stocks. These reads stay in the same router.
                batches.extendleft(reversed([[row] for row in batch]))
            else:
                batch[0].update(status='unverified', reason=str(error))
            continue
        except (ValueError, RuntimeError, OSError) as error:
            for row in batch: row.update(status='unverified', reason=str(error))
            continue
        for row in batch:
            info = by_code.get(row['symbol'])
            row['data_access'] = payload.get('data_access')
            if info is None:
                # A missing result could be a provider/data failure, not a typo.
                row.update(status='unverified', reason='券商未返回该代码的基本资料，不能确认是否有效')
                continue
            row['name'], row['stock_type'] = info.get('name'), info.get('stock_type')
            kind, delisted = info.get('stock_type'), info.get('delisting')
            if kind in ('NONE', 'N/A'):
                row.update(status='invalid', reason='券商不识别该股票代码')
            elif kind not in ('STOCK', 'ETF'):
                if kind:
                    row.update(status='invalid', reason=f'该代码为 {kind}，当前列表仅支持股票 / ETF')
                else:
                    row.update(status='unverified', reason='券商未返回证券类型')
            elif delisted is True:
                row.update(status='invalid', reason='券商标记为已退市')
            elif delisted is not False or not isinstance(row['name'], str) or not row['name'].strip():
                row.update(status='unverified', reason='证券名称或退市状态不完整，不能确认有效')
            else:
                row.update(status='valid', reason='券商确认该代码为未退市股票 / ETF')
    return _finish_precheck(entries)


def run_watchlist(service, values, *, action='both', top_n=10, configuration=None,
                  check_only=False, progress=None, raw_put=False):
    if action not in ('both', 'put', 'trend'): raise ValueError('action must be both, put or trend')
    if type(top_n) is not int or top_n not in (5, 10, 20): raise ValueError('top_n must be 5, 10 or 20')
    # Reject invalid strategy settings before any provider call.
    if action in ('both', 'put'): configuration = load_rules().recommendation_configuration(configuration)
    progress = progress or (lambda message: print(message, file=sys.stderr))
    started = datetime.now(timezone.utc).isoformat()
    progress('预检查股票列表：格式、重复项及券商基本资料…')
    check = precheck(service, values)
    result = dict(schema=1, action='watchlist', requested_action=action, top_n=top_n,
                  ranking_scope='per_symbol', started_at=started, precheck=check, results=[])
    if not check['passed']:
        result['status'] = 'precheck_failed'
        progress('预检查未通过；尚未开始期权 / 走势分析。')
    elif check_only:
        result['status'] = 'precheck_passed'
    else:
        for index, code in enumerate(check['valid_symbols'], 1):
            progress(f'[{index}/{len(check["valid_symbols"])}] 分析 {code}…')
            item = dict(symbol=code)
            if action in ('both', 'put'):
                try:
                    if raw_put:
                        dataset = service.collect_put_dataset([code], months=3)
                        item['put'] = dict(action='put', symbol=code, collected_at=dataset['collected_at'],
                                           input_dataset=dataset, data_access=dataset.get('data_access', {}))
                    else:
                        item['put'] = run_research(service, code, 'put', configuration, top_n)
                except (ValueError, RuntimeError, OSError) as error:
                    item['put'] = dict(error=str(error))
            if action in ('both', 'trend'):
                try:
                    dataset = item.get('put', {}).get('input_dataset')
                    if dataset is not None:
                        # Reuse the completed bars already fetched by Put collection.
                        trend = dict(action='trend', symbol=code,
                                     collected_at=dataset.get('fetched_at', dataset['collected_at']),
                                     trend=trend_report(dataset, code))
                        from .price_signals import dataset_signals
                        trend['price_signals'] = item['put'].get('price_signals') or dataset_signals(dataset, {code:trend['trend']})
                        if 'data_access' in dataset: trend['data_access'] = dataset['data_access']
                        item['trend'] = trend
                    else:
                        item['trend'] = run_research(service, code, 'trend')
                except (ValueError, RuntimeError, OSError) as error:
                    item['trend'] = dict(error=str(error))
            failed = sum('error' in item[key] for key in ('put', 'trend') if key in item)
            actions = sum(key in item for key in ('put', 'trend'))
            item['status'] = 'ok' if not failed else 'error' if failed == actions else 'partial'
            result['results'].append(item)
        result['status'] = 'completed' if all(item['status'] == 'ok' for item in result['results']) else 'partial_failure'
    result['summary'] = dict(input_count=len(values), unique_count=len(check['entries'])-len(check['duplicates']),
                            valid_count=len(check['valid_symbols']), invalid_count=len(check['invalid']),
                            unverified_count=len(check['unverified']), duplicate_count=len(check['duplicates']),
                            analyzed_count=len(result['results']),
                            failed_count=sum(item['status'] != 'ok' for item in result['results']))
    result['completed_at'] = datetime.now(timezone.utc).isoformat()
    return result
