"""JSON subprocess boundary: SDK runs on its own main thread, away from Qt."""
import argparse
from contextlib import redirect_stdout
import json
import os
from pathlib import Path
import sys

from .market_collection import opend_connection
from .research import run_research


def main(argv=None):
    parser = argparse.ArgumentParser(description='Single-stock Put or daily trend research')
    parser.add_argument('action', choices=['put', 'trend'])
    parser.add_argument('symbol')
    parser.add_argument('--port', type=int, default=11111)
    parser.add_argument('--output', type=Path, help='JSON file for windowed desktop subprocesses')
    args = parser.parse_args(argv)
    def emit(value):
        document = json.dumps(value, ensure_ascii=False, allow_nan=False)
        if args.output: args.output.write_text(document, encoding='utf-8')
        elif sys.stdout is not None: print(document)
    if sys.stderr is None: sys.stderr = open(os.devnull, 'w', encoding='utf-8')
    try:
        # Broker logging must never corrupt the JSON protocol on stdout.
        with redirect_stdout(sys.stderr):
            with opend_connection(port=args.port) as service:
                result = run_research(service, args.symbol, args.action)
        emit(result)
        return 0
    except Exception as error:
        emit(dict(error=str(error)))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
