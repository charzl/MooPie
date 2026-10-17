"""Validate a JSON watchlist before researching every requested stock."""
import argparse
from contextlib import redirect_stdout
import json
from pathlib import Path
import sys

from .market_repository import market_data_connection
from .research import load_rules
from .watchlist import load_watchlist, run_watchlist


def main(argv=None):
    parser = argparse.ArgumentParser(description='Precheck a JSON stock list, then research every stock')
    parser.add_argument('list_file', type=Path, nargs='?', help='Optional JSON; omitted means the SQLite Watchlist')
    parser.add_argument('--action', choices=('both', 'put', 'trend'), default='both')
    parser.add_argument('--check-only', action='store_true', help='Verify all symbols without fetching option chains or daily bars')
    parser.add_argument('--top', type=int, choices=(5, 10, 20), default=10, help='Top N candidates per stock')
    parser.add_argument('--rank-by', choices=('return', 'risk', 'duration', 'cost', 'balanced'))
    parser.add_argument('--config', type=Path)
    parser.add_argument('--port', type=int, default=11111)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--refresh', action='store_true', help='Force fetch every requested stock')
    mode.add_argument('--update', action='store_true', help='Fetch only missing or stale data, reusing valid cache')
    parser.add_argument('--max-age-seconds', type=int, default=60)
    parser.add_argument('--output', type=Path, help='Save the complete JSON report; otherwise use stdout')
    args = parser.parse_args(argv)
    def emit(result):
        document = json.dumps(result, ensure_ascii=False, allow_nan=False, indent=2) + '\n'
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(document, encoding='utf-8')
        else:
            print(document, end='')
    try:
        from .watchlist_store import WatchlistStore
        values = load_watchlist(args.list_file) if args.list_file else WatchlistStore().symbols()
        if not values: raise ValueError('Watchlist 为空，请先加入股票。')
        configuration = json.loads(args.config.read_text(encoding='utf-8')) if args.config else None
        if args.rank_by:
            configuration = load_rules().recommendation_configuration(configuration)
            configuration['sort_order'] = [list(item) for item in load_rules().RANKING_SORT_ORDERS[args.rank_by]]
        with redirect_stdout(sys.stderr):
            with market_data_connection(port=args.port, refresh=args.refresh, update=args.update, max_age_seconds=args.max_age_seconds) as service:
                result = run_watchlist(service, values, action=args.action, top_n=args.top,
                                      configuration=configuration, check_only=args.check_only)
        status = 2 if result['status'] == 'precheck_failed' else 1 if result['status'] == 'partial_failure' else 0
    except (ValueError, OSError, RuntimeError) as error:
        result, status = dict(error=str(error)), 1
    try:
        emit(result)
    except OSError as error:
        parser.exit(1, f'Cannot write watchlist report: {error}\n')
    return status


if __name__ == '__main__': raise SystemExit(main())
