"""Project and assemble raw batches without calculating strategy indicators."""
import json
import re


def underlying(code):
    return re.sub(r'\d{6}[CP]\d+$', '', code)


def partition(operation, parameters):
    field = {'collect_put_dataset': 'symbols', 'daily_bars': 'symbols',
             'snapshots': 'codes', 'basic_info': 'codes', 'paper_inputs':'symbols'}.get(operation)
    return (field, parameters[field]) if field else (None, [])


def project(payload, operation, subject):
    result = dict(payload)
    for field in ('symbols', 'codes'):
        if field in result: result[field] = [subject]
    for field, owner in [('contracts', 'symbol'), ('coverage', 'symbol'), ('daily_series', 'symbol'), ('actions','symbol'), ('rows', 'code')]:
        if field in result:
            result[field] = [row for row in result[field] if row.get(owner) == subject]
    if 'missing_codes' in result:
        result['missing_codes'] = [code for code in result['missing_codes'] if code == subject]
    if 'missing_quote_codes' in result:
        result['missing_quote_codes'] = [code for code in result['missing_quote_codes'] if underlying(code) == subject]
        known = set(payload.get('symbols', []))
        unassigned = [code for code in payload['missing_quote_codes'] if underlying(code) not in known]
        if unassigned:
            # Adjusted contract roots need not equal their stock owner. The raw
            # dataset has no owner record for these missing quotes: retain them
            # explicitly instead of guessing ownership or silently dropping them.
            result['unassigned_missing_quote_codes'] = unassigned
            result['collection_notes'] = [*result.get('collection_notes', []),
                'Some missing quote codes cannot be assigned to one stock; preserved as unassigned_missing_quote_codes.']
    return result


def assemble(payloads, operation, parameters):
    result = dict(payloads[0])
    field, subjects = partition(operation, parameters)
    if field in result: result[field] = subjects
    for key in ('contracts', 'coverage', 'daily_series', 'actions', 'rows', 'missing_codes', 'missing_quote_codes'):
        if any(key in value for value in payloads):
            result[key] = [item for value in payloads for item in value.get(key, [])]
    for key in ('calendar_errors', 'collection_notes', 'unassigned_missing_quote_codes'):
        if any(key in value for value in payloads):
            seen, rows = set(), []
            for value in payloads:
                for item in value.get(key, []):
                    identity = json.dumps(item, sort_keys=True)
                    if identity not in seen: rows.append(item); seen.add(identity)
            result[key] = rows
    # These aggregate timestamps mean "latest member", not simultaneous quotes.
    # Each member retains its actual time and original snapshot ID in data_access.
    from datetime import datetime
    for key in ('collected_at', 'fetched_at', 'decision_cutoff', 'trend_collected_at', 'trend_decision_cutoff'):
        values = [value[key] for value in payloads if value.get(key)]
        if values: result[key] = max(values, key=datetime.fromisoformat)
    dates = {value['session_date'] for value in payloads if value.get('session_date')}
    if len(dates) > 1:
        raise RuntimeError('不能将不同交易日的股票快照合并，请刷新对应股票。')
    as_of = [value['trend_as_of'] for value in payloads if value.get('trend_as_of')]
    if as_of: result['trend_as_of'] = min(as_of)
    return result
