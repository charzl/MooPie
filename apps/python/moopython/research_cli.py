"""JSON subprocess boundary: SDK runs on its own main thread, away from Qt."""
import argparse
from contextlib import redirect_stdout
import json
import os
from pathlib import Path
import sys

from .market_repository import market_data_connection
from .research import analyze_put_dataset, run_research


def main(argv=None):
    parser = argparse.ArgumentParser(description='Single-stock or Watchlist research')
    parser.add_argument('action', choices=['overview', 'radar', 'put', 'trend', 'add', 'sync-directory', 'alerts'])
    parser.add_argument('symbol', nargs='?')
    parser.add_argument('--watchlist', type=Path, help='Research this JSON instead of the database Watchlist; read-only input')
    parser.add_argument('--port', type=int, default=11111)
    parser.add_argument('--output', type=Path, help='JSON file for windowed desktop subprocesses')
    parser.add_argument('--config', type=Path, help='Explicit filters and independent sort configuration')
    parser.add_argument('--top', type=int, choices=(5, 10, 20), default=10, help='Return Top 5, 10 or 20 after ranking the complete dataset')
    parser.add_argument('--input', type=Path, help='Reanalyze a saved Put dataset without connecting to OpenD')
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--refresh', action='store_true', help='Force fetch all requested data, even after hours')
    mode.add_argument('--update', action='store_true', help='Reuse valid snapshots; fetch only missing or stale stocks')
    mode.add_argument('--saved', action='store_true', help='Show saved closing results, even intraday; auto-fetch only a never-collected single stock')
    parser.add_argument('--max-age-seconds', type=int, default=60, help='Intraday quote cache validity for --update (1–3600 seconds)')
    parser.add_argument('--depth', action='store_true', help='Read visible order-book depth for a single-stock detail view')
    args = parser.parse_args(argv)
    output_stream = sys.stdout
    def emit(value):
        document = json.dumps(value, ensure_ascii=False, allow_nan=False)
        if args.output: args.output.write_text(document, encoding='utf-8')
        elif output_stream is not None: print(document,file=output_stream)
    if sys.stderr is None: sys.stderr = open(os.devnull, 'w', encoding='utf-8')
    try:
        if args.action == 'alerts':
            if args.symbol or args.input or args.watchlist or args.config or args.depth:
                raise ValueError('alerts polls armed stocks from SQLite only')
            from .buy_alert_store import BuyAlertStore
            alerts = BuyAlertStore()
            symbols = alerts.active_symbols()
            rows = []
            daily_error = None
            if symbols:
                with redirect_stdout(sys.stderr):
                    with market_data_connection(port=args.port, refresh=True) as service:
                        quote_rows = service.snapshots(symbols)['rows']
                for quote in quote_rows:
                    record, event = alerts.observe(quote['code'], quote, with_event=True)
                    if record: rows.append(dict(symbol=quote['code'], quote=quote, alert=record, event=event))
                close_symbols = [row['symbol'] for row in rows if row['alert']['status'] == 'inside'
                                 and row['alert']['confirmation_mode'] == 'daily_close']
                if close_symbols:
                    try:
                        with redirect_stdout(sys.stderr):
                            with market_data_connection(port=args.port, update=True) as service:
                                daily = service.daily_bars(close_symbols)
                        series_by_symbol = {item['symbol']: item for item in daily.get('daily_series', [])}
                        for row in rows:
                            if row['symbol'] not in close_symbols: continue
                            series = series_by_symbol.get(row['symbol'])
                            if series and series.get('bars'):
                                bar = series['bars'][-1]
                                if bar.get('complete') is True and series.get('as_of') == bar.get('date'):
                                    record, event = alerts.observe_close(row['symbol'], bar.get('close'),
                                                                         bar.get('date'), with_event=True)
                                    row['alert'], row['event'] = record, row['event'] or event
                                else:
                                    daily_error = '日线尚未标记为已完成；收盘确认未执行'
                            else:
                                daily_error = str(series.get('error') if series else '未返回已完成日线')
                    except (OSError, RuntimeError, ValueError, KeyError, TypeError) as error:
                        daily_error = str(error)
            emit(dict(action='alerts', rows=rows, daily_error=daily_error))
            return 0
        if args.depth and (args.action != 'trend' or not args.symbol):
            raise ValueError('--depth requires a single-stock trend query')
        def attach_depth(result):
            if args.depth:
                from .order_book import read_order_book
                from .price_signals import price_position, unavailable
                from .timeframe_levels import timeframe_levels
                from .price_signal_store import PriceSignalStore
                from .market_collection import us_symbols
                code = us_symbols([args.symbol])[0]
                try:
                    with market_data_connection(port=args.port, update=True,
                                                max_age_seconds=args.max_age_seconds) as service:
                        quote = next(row for row in service.snapshots([code])['rows'] if row['code'] == code)
                        result['quote'] = quote
                        if result.get('trend', {}).get('status') == 'ok':
                            daily = service.daily_bars([code])
                            series = next(row for row in daily['daily_series'] if row['symbol'] == code)
                            signal = price_position(series, result['trend'], reference=dict(
                                price=quote['last_price'], time=quote.get('update_time'), basis='underlying_snapshot'))
                            if signal['status'] == 'ok':
                                signal['multi_timeframe'] = timeframe_levels(
                                    series, signal, daily.get('decision_cutoff') or daily.get('fetched_at'))
                            result['price_signals'] = {code: signal}
                except Exception as error:
                    result['quote_error'] = str(error)
                    if result.get('trend', {}).get('status') != 'ok':
                        result['price_signals'] = {code: unavailable(code, result['trend'].get('error', str(error)))}
                result['order_book'] = read_order_book(args.symbol, args.port)
                try:
                    signal = result.get('price_signals', {}).get(code)
                    store = PriceSignalStore()
                    if signal and signal.get('status') == 'ok':
                        result['price_signal_saved_at'] = store.save(signal)
                    else:
                        previous = store.latest(code)
                        if previous: result['saved_price_signal'] = previous
                except (OSError, RuntimeError, ValueError, KeyError) as error:
                    result['price_signal_storage_error'] = str(error)
            return result
        if args.action in ('overview', 'radar'):
            if args.symbol or args.input or args.watchlist or args.config or args.saved or args.depth:
                raise ValueError('overview/radar reads the database Watchlist and does not accept stock/input/watchlist/config/saved/depth')
            from .security_directory import SecurityDirectory
            from .stock_overview import build_overview
            from .watchlist_store import WatchlistStore
            symbols = WatchlistStore().symbols()
            if not symbols: raise ValueError('Watchlist 为空，请先加入股票。')
            with redirect_stdout(sys.stderr):
                with market_data_connection(port=args.port, refresh=args.refresh,
                                            update=args.update, max_age_seconds=args.max_age_seconds) as service:
                    snapshot = service.snapshots(symbols)
                identities = SecurityDirectory().lookup(symbols)
                result = build_overview(symbols, snapshot, identities)
            if args.action == 'radar':
                from .buy_radar import build_radar
                from .price_signal_store import PriceSignalStore
                from .buy_alert_store import BuyAlertStore
                signal_store, alert_store = PriceSignalStore(), BuyAlertStore()
                result = build_radar(result, {code: signal_store.latest(code) for code in symbols},
                                     {code: alert_store.get(code) for code in symbols})
            emit(result)
            return 0
        if args.action == 'sync-directory':
            if args.symbol or args.input or args.watchlist: raise ValueError('sync-directory does not accept stock/input/watchlist')
            from .market_collection import opend_connection
            from .security_directory import SecurityDirectory
            with redirect_stdout(sys.stderr):
                with opend_connection(port=args.port) as service:
                    payload = service.security_directory()
                result = SecurityDirectory().ingest(payload)
            emit(result)
            return 0
        if args.action == 'add':
            if not args.symbol or args.input: raise ValueError('add requires a stock symbol and cannot use --input')
            if args.watchlist: raise ValueError('add writes SQLite; use db import-watchlist to import JSON')
            from .watchlist_store import add_to_watchlist
            with redirect_stdout(sys.stderr):
                with market_data_connection(port=args.port, refresh=args.refresh, update=args.update, max_age_seconds=args.max_age_seconds) as service:
                    result = add_to_watchlist(service, args.symbol)
            emit(result)
            return 0
        # Broker logging must never corrupt the JSON protocol on stdout.
        with redirect_stdout(sys.stderr):
            config = json.loads(args.config.read_text(encoding='utf-8')) if args.config else None
            if args.symbol and args.watchlist: raise ValueError('Choose a single stock or --watchlist, not both')
            use_watchlist = not args.symbol
            if args.input:
                if args.refresh or args.update or args.saved: raise ValueError('--input cannot be combined with --refresh, --update or --saved')
                if args.action != 'put': raise ValueError('--input is only supported for Put filtering')
                dataset = json.loads(args.input.read_text(encoding='utf-8'))
                if use_watchlist:
                    from .watchlist_research import analyze_watchlist_dataset
                    result = analyze_watchlist_dataset(dataset, config, args.top)
                else:
                    result = analyze_put_dataset(dataset, args.symbol, config, args.top)
            else:
                # Validate options before making any broker request.
                if args.action == 'put':
                    from .research import load_rules
                    load_rules().recommendation_configuration(config)
                if args.saved:
                    from .saved_research import saved_research, SavedMarketData
                    from .market_repository import CacheMissError
                    from .watchlist_store import WatchlistStore
                    from .watchlist import load_watchlist
                    from .market_collection import us_symbols
                    values = (us_symbols([args.symbol]) if args.symbol else
                              load_watchlist(args.watchlist) if args.watchlist else WatchlistStore().symbols())
                    if not values: raise ValueError('Watchlist 为空，请先加入股票。')
                    try:
                        result = saved_research(values,args.action,config,args.top,port=args.port,watchlist=use_watchlist)
                        emit(attach_depth(result))
                        return 0
                    except CacheMissError:
                        if use_watchlist or not SavedMarketData(values,args.port).never_collected(values[0],args.action):
                            raise
                        # Preserve first-query collection for a new single stock;
                        # existing intraday-only/stale data requires Update Quotes.
                with market_data_connection(port=args.port, refresh=args.refresh, update=args.update, max_age_seconds=args.max_age_seconds) as service:
                    if use_watchlist:
                        from .watchlist_store import WatchlistStore
                        from .watchlist import load_watchlist
                        from .watchlist_research import run_watchlist_research
                        values = load_watchlist(args.watchlist) if args.watchlist else WatchlistStore().symbols()
                        if not values: raise ValueError('Watchlist 为空，请先加入股票。')
                        result = run_watchlist_research(service, values, args.action, config, args.top)
                    else:
                        try:
                            result = run_research(service, args.symbol, args.action, config, args.top)
                        except Exception as error:
                            if not args.depth: raise
                            from .market_collection import us_symbols
                            from .price_signals import unavailable
                            from datetime import datetime, timezone
                            code = us_symbols([args.symbol])[0]
                            result = dict(action='trend', symbol=code,
                                          collected_at=datetime.now(timezone.utc).isoformat(),
                                          trend=dict(status='unavailable', error=str(error)),
                                          price_signals={code: unavailable(code, str(error))})
            if args.action=='put':
                from .saved_research import remember_closing_result
                remember_closing_result(result,args.port)
        emit(attach_depth(result))
        return 0
    except Exception as error:
        emit(dict(error=str(error)))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
