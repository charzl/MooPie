"""JSON subprocess boundary: SDK runs on its own main thread, away from Qt."""
import argparse
from contextlib import redirect_stdout
import json
import os
from pathlib import Path
import sys

from .market_collection import opend_connection
from .research import analyze_put_dataset, run_research


def main(argv=None):
    parser = argparse.ArgumentParser(description='Single-stock Put or daily trend research')
    parser.add_argument('action', choices=['put', 'trend'])
    parser.add_argument('symbol')
    parser.add_argument('--port', type=int, default=11111)
    parser.add_argument('--output', type=Path, help='JSON file for windowed desktop subprocesses')
    parser.add_argument('--config', type=Path, help='Explicit filters and independent sort configuration')
    parser.add_argument('--top', type=int, choices=(5, 10, 20), default=10, help='Return Top 5, 10 or 20 after ranking the complete dataset')
    parser.add_argument('--input', type=Path, help='Reanalyze a saved Put dataset without connecting to OpenD')
    args = parser.parse_args(argv)
    def emit(value):
        document = json.dumps(value, ensure_ascii=False, allow_nan=False)
        if args.output: args.output.write_text(document, encoding='utf-8')
        elif sys.stdout is not None: print(document)
    if sys.stderr is None: sys.stderr = open(os.devnull, 'w', encoding='utf-8')
    try:
        # Broker logging must never corrupt the JSON protocol on stdout.
        with redirect_stdout(sys.stderr):
            config = json.loads(args.config.read_text(encoding='utf-8')) if args.config else None
            if args.input:
                if args.action != 'put': raise ValueError('--input is only supported for Put filtering')
                result = analyze_put_dataset(json.loads(args.input.read_text(encoding='utf-8')), args.symbol, config, args.top)
            else:
                # Validate options before making any broker request.
                if args.action == 'put':
                    from .research import load_rules
                    load_rules().recommendation_configuration(config)
                with opend_connection(port=args.port) as service:
                    result = run_research(service, args.symbol, args.action, config, args.top)
        emit(result)
        return 0
    except Exception as error:
        emit(dict(error=str(error)))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
