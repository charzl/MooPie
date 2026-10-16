"""Editable, standalone cash-secured PUT research rules. Python standard library only.

Edit RULES / SORT_ORDER below, increase RULESET_VERSION, and rerun the same input.
No broker, Qt, other rule-engine package, model, or order API is imported here.
"""
import argparse
from datetime import date, datetime, timezone
import hashlib
import json
import math
import operator
from pathlib import Path
import re
from zoneinfo import ZoneInfo


ENGINE_VERSION = '0.1.0'
RULESET_VERSION = '1.0.0'
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
    'same_session_snapshot', 'snapshot_age_seconds', 'earnings_known', 'days_expiry_before_earnings'))
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
    results = []
    for row in rows:
        base = dict(code=row['code'], symbol=row.get('symbol'), expiration=row.get('expiration'))
        try:
            values = metrics(row, session, collected)
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
        rules_sha256=fingerprint(dict(rules=RULES, sort=SORT_ORDER)), dataset_sha256=fingerprint(dataset),
        assumption='One standard US equity/ETF put, fully cash secured, willing to accept shares; user suitability not established',
        cash_budget=budget, budget_checked=budget is not None,
        ranking_objective='Pass every hard rule, then sort lexicographically by sort_order; not an expected-return prediction',
        sort_order=SORT_ORDER, rules=RULES, total_contracts=len(rows),
        missing_quote_codes=dataset.get('missing_quote_codes', []),
        calendar_errors=dataset.get('calendar_errors', []),
        qualified_count=len(ranked), best_research_code=ranked[0]['code'] if ranked else None,
        ranked_codes=[row['code'] for row in ranked], results=results,
        ranked=ranked, earnings_unverified_watchlist=watchlist,
        best_watchlist_code=watchlist[0]['code'] if watchlist else None,
        limitations=[
            'Rule-selected research candidates; thresholds have not been backtested or validated.',
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
