"""Collect normalized market data as JSON without importing the desktop UI."""
import argparse
from contextlib import redirect_stdout
import json
from pathlib import Path
import sys

from .market_collection import MarketDataService, opend_connection


def main(argv=None):
    parser = argparse.ArgumentParser(description='Collect US put chains, bid/ask, Greeks and earnings as JSON')
    parser.add_argument('symbols', nargs='*')
    parser.add_argument('--enrich', type=Path, help='Add completed daily bars to an existing snapshot JSON; preserve quote collection time')
    parser.add_argument('--months', type=int, default=3)
    parser.add_argument('--port', type=int, default=11111)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        with redirect_stdout(sys.stderr):
            with opend_connection(port=args.port) as service:
                if args.enrich:
                    dataset = json.loads(args.enrich.read_text())
                    dataset.update(service.daily_bars(dataset['symbols'], dataset['session_date'],
                                                      cutoff=dataset['collected_at']))
                else:
                    dataset = service.collect_put_dataset(args.symbols, args.months)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(dataset, ensure_ascii=False, allow_nan=False, indent=2) + '\n')
        print(f'Saved {len(dataset["contracts"])} contract snapshots to {args.output}')
    except (ValueError, RuntimeError, OSError) as error:
        parser.exit(1, f'Collection failed: {error}\n')


if __name__ == '__main__': main()
