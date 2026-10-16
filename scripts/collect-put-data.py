"""Collect broker snapshots as JSON; ranking rules live in put_rules.py."""
import argparse
from contextlib import redirect_stdout
from datetime import date, datetime, timedelta, timezone
import json
import math
from pathlib import Path
import signal
import socket
import sys
import time
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'apps/python'))
from moopython.options import OptionChainService, OptionQuery, option_symbol
from moopython.account_data import records


def clean(value):
    if isinstance(value, dict): return {k: clean(v) for k, v in value.items()}
    if isinstance(value, list): return [clean(v) for v in value]
    if isinstance(value, float) and not math.isfinite(value): return None
    return value


def collect(sdk, context, symbols, months=3):
    symbols = list(dict.fromkeys(option_symbol(value) for value in symbols))
    if not symbols or any(not code.startswith('US.') for code in symbols):
        raise ValueError('This first screener collects US stock / ETF puts only')
    now = datetime.now(timezone.utc)
    today = now.astimezone(ZoneInfo('America/New_York')).date()
    ret, days = context.request_trading_days(
        sdk.Market.US, start=(today - timedelta(days=14)).isoformat(), end=today.isoformat())
    if ret != sdk.RET_OK: raise RuntimeError(str(days))
    session_date = max(row['time'] for row in days)
    underlying = {row['code']: row for row in records(sdk, context.get_market_snapshot(symbols))}
    missing = set(symbols) - underlying.keys()
    if missing: raise RuntimeError(f'Missing underlying snapshots: {sorted(missing)}')
    states = {row['code']: row['market_state'] for row in records(sdk, context.get_market_state(symbols))}
    service = OptionChainService(sdk, context)
    contracts = []
    coverage = []
    for code in symbols:
        print(f'Collecting {code} PUT chains…', file=sys.stderr)
        query = OptionQuery.upcoming(code, months=months, option_type='PUT')
        chain = service.query(query)
        coverage.append({k: chain[k] for k in ('symbol', 'start', 'end', 'expirations', 'queried_at')})
        contracts.extend(chain['contracts'])

    quotes = {}
    codes = list(dict.fromkeys(row['code'] for row in contracts))
    for index in range(0, len(codes), 200):
        if index: time.sleep(.6)
        batch = codes[index:index + 200]
        print(f'Collecting option snapshots {index + 1}–{index + len(batch)} / {len(codes)}', file=sys.stderr)
        quotes.update({row['code']: row for row in records(sdk, context.get_market_snapshot(batch))})

    # A missing calendar listing is unknown, rather than proof of no earnings.
    horizon = max(date.fromisoformat(row['end']) for row in coverage)
    earnings = {code: [] for code in symbols}
    calendar_errors = []
    first = today
    while first <= horizon:
        last = min(horizon, first + timedelta(days=6))
        try:
            rows = records(sdk, context.get_earnings_calendar(
                sdk.Market.US, begin_date=first.isoformat(), end_date=last.isoformat()))
            for row in rows:
                if row.get('security') in earnings and row.get('earnings_date'):
                    earnings[row['security']].append(dict(
                        date=row['earnings_date'], publication_time=row.get('pub_type'),
                        source='moomoo OpenD earnings calendar; provider date, not issuer-confirmed'))
        except Exception as error:
            calendar_errors.append(dict(start=first.isoformat(), end=last.isoformat(), error=str(error)))
        first = last + timedelta(days=1)
        if first <= horizon: time.sleep(.6)

    normalized = []
    missing_quotes = []
    for contract in contracts:
        code = contract['code']
        quote = quotes.get(code)
        if quote is None:
            missing_quotes.append(code)
            continue
        owner = contract['stock_owner']
        next_earnings = sorted(earnings[owner], key=lambda row: row['date'])
        normalized.append(dict(
            code=code, symbol=owner, currency='USD', option_type=contract['option_type'],
            expiration=contract['strike_time'], strike=contract['strike_price'],
            standard_type=contract['option_standard_type'], shares=contract['lot_size'],
            snapshot_symbol=quote.get('stock_owner'), snapshot_expiration=quote.get('strike_time'),
            snapshot_strike=quote.get('option_strike_price'), snapshot_option_type=quote.get('option_type'),
            option_valid=quote.get('option_valid'), snapshot_shares=quote.get('option_contract_size'),
            underlying_price=underlying[owner]['last_price'],
            underlying_price_basis='OpenD regular-session last_price; after_price is not substituted',
            underlying_update_time=underlying[owner]['update_time'],
            market_state=states.get(owner, 'UNKNOWN'),
            bid=quote.get('bid_price'), ask=quote.get('ask_price'), bid_size=quote.get('bid_vol'),
            volume=quote.get('volume'), open_interest=quote.get('option_open_interest'),
            delta=quote.get('option_delta'), iv_pct=quote.get('option_implied_volatility'),
            snapshot_update_time=quote.get('update_time'),
            suspension=bool(contract.get('suspension') or quote.get('suspension')),
            earnings=next_earnings[0] if next_earnings else None,
            earnings_calendar_complete=not calendar_errors,
        ))
    return clean(dict(
        schema=1, source='moomoo OpenD', collected_at=datetime.now(timezone.utc).isoformat(),
        session_date=session_date, timezone='America/New_York', symbols=symbols, coverage=coverage,
        contracts=normalized, missing_quote_codes=missing_quotes, calendar_errors=calendar_errors,
        collection_notes=[
            'All listed PUT contracts in the requested range; no yield or delta preselection.',
            'snapshot_update_time is the broker snapshot timestamp, not a guaranteed bid timestamp.',
            'Earnings dates are provider listings and may be estimated or change.',
        ]))


def main():
    parser = argparse.ArgumentParser(description='Collect US put chains, bid/ask, Greeks and earnings as JSON')
    parser.add_argument('symbols', nargs='+')
    parser.add_argument('--months', type=int, default=3)
    parser.add_argument('--port', type=int, default=11111)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        with redirect_stdout(sys.stderr):
            with socket.create_connection(('127.0.0.1', args.port), timeout=2): pass
            import moomoo as sdk
            signal.signal(signal.SIGINT, signal.default_int_handler)
            context = sdk.OpenQuoteContext(host='127.0.0.1', port=args.port)
            try: dataset = collect(sdk, context, args.symbols, args.months)
            finally: context.close()
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(dataset, ensure_ascii=False, allow_nan=False, indent=2) + '\n')
        print(f'Saved {len(dataset["contracts"])} contract snapshots to {args.output}')
    except (ValueError, RuntimeError, OSError) as error:
        parser.exit(1, f'Collection failed: {error}\n')


if __name__ == '__main__': main()
