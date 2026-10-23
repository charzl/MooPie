"""SQLite maintenance and explicit security-directory synchronization."""
import argparse
from contextlib import redirect_stdout
import json
from pathlib import Path
import sys

from .market_store import SnapshotStore
from .database import schema_sql


def main(argv=None):
    parser = argparse.ArgumentParser(description='Local market database status, retention and cleanup')
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('status', help='Show database location, schema, history and retention policy')
    commands.add_parser('schema', help='Print SQL generated from migrations without opening the user database')
    commands.add_parser('watchlist', help='Read the persistent SQLite Watchlist')
    signal_history = commands.add_parser('price-signals', help='Read saved support/resistance history for one stock')
    signal_history.add_argument('symbol')
    signal_history.add_argument('--limit', type=int, default=20)
    importing = commands.add_parser('import-watchlist', help='Validate a JSON and merge it into the SQLite Watchlist')
    importing.add_argument('path', type=Path)
    importing.add_argument('--replace', action='store_true', help='Replace existing membership after the full list validates')
    importing.add_argument('--refresh', action='store_true', help='Explicitly refresh security verification, including after hours')
    importing.add_argument('--port', type=int, default=11111)
    exporting = commands.add_parser('export-watchlist', help='Export the SQLite Watchlist as JSON')
    exporting.add_argument('path', type=Path)
    sync = commands.add_parser('sync-symbols', help='Explicitly connect OpenD to update the US stock/ETF directory, without quotes')
    sync.add_argument('--port', type=int, default=11111)
    search = commands.add_parser('search', help='Local code/name/alias prefix search; supports quoted * and ? wildcards')
    search.add_argument('query')
    search.add_argument('--limit', type=int, default=20)
    retention = commands.add_parser('retention', help='Persist automatic retention; 0 disables deletion')
    retention.add_argument('--days', type=int, required=True)
    cleanup = commands.add_parser('cleanup', help='Delete snapshots older than N calendar days by collection time')
    cleanup.add_argument('--older-than-days', type=int, help='Use this age once; otherwise use saved retention policy')
    cleanup.add_argument('--dry-run', action='store_true', help='Only count eligible snapshots; do not delete')
    commands.add_parser('vacuum', help='Explicitly compact the file after cleanup; may block other database users')
    args = parser.parse_args(argv)
    store = SnapshotStore()
    try:
        if args.command == 'schema':
            print(schema_sql(), end='')
            return 0
        if args.command in ('watchlist', 'import-watchlist', 'export-watchlist'):
            from .watchlist_store import WatchlistStore
            watchlist = WatchlistStore(store)
            if args.command == 'watchlist': result = watchlist.status()
            elif args.command == 'export-watchlist': result = watchlist.export_json(args.path)
            else:
                from .market_repository import market_data_connection
                with redirect_stdout(sys.stderr):
                    with market_data_connection(port=args.port, refresh=args.refresh) as service:
                        result = watchlist.import_json(service, args.path, replace=args.replace)
        elif args.command == 'sync-symbols':
            from .market_collection import opend_connection
            from .security_directory import SecurityDirectory
            with redirect_stdout(sys.stderr):
                with opend_connection(port=args.port) as service: payload = service.security_directory()
                result = SecurityDirectory(store).ingest(payload)
        elif args.command == 'search':
            from .security_directory import SecurityDirectory
            result = dict(query=args.query, candidates=SecurityDirectory(store).search(args.query, args.limit))
        elif args.command == 'price-signals':
            from .market_collection import us_symbols
            from .price_signal_store import PriceSignalStore
            code = us_symbols([args.symbol])[0]
            result = dict(symbol=code, history=PriceSignalStore(store).history(code, args.limit))
        elif args.command == 'status': result = store.status()
        elif args.command == 'retention': result = store.set_retention(args.days)
        elif args.command == 'cleanup': result = store.cleanup(args.older_than_days, dry_run=args.dry_run)
        else: result = store.vacuum()
        print(json.dumps(result, ensure_ascii=False, allow_nan=False))
        return 0
    except (ValueError, RuntimeError, OSError) as error:
        parser.exit(1, f'Database maintenance failed: {error}\n')


if __name__ == '__main__': raise SystemExit(main())
