"""Isolate quote permissions by market so one denial cannot blank the overview."""
from collections import defaultdict
from .account_data import records


def query_market_snapshots(sdk, context, codes):
    codes = list(dict.fromkeys(codes))
    if not 1 <= len(codes) <= 200:
        raise ValueError('每次市场快照查询需要 1–200 个标的')
    groups = defaultdict(list)
    for code in codes:
        market, ticker = code.split('.',1)
        # Index entitlements are separate from equity entitlements in OpenD.
        index = market == 'SH' and ticker == '000001' or market == 'SZ' and ticker.startswith('399') or market == 'HK' and ticker.startswith('800')
        groups[(market,index)].append(code)
    rows, errors = [], []
    for (market,_), members in groups.items():
        try:
            returned = records(sdk, context.get_market_snapshot(members))
            rows.extend(row for row in returned if row.get('code') in members)
            received = {row.get('code') for row in returned}
            missing = [code for code in members if code not in received]
            if missing: errors.append(dict(market=market,codes=missing,error='OpenD 未返回这些标的的数据'))
        except Exception as error:
            errors.append(dict(market=market,codes=members,error=str(error)))
    return dict(rows=rows,errors=errors)
