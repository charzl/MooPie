"""Local paper-trading CLI and windowed desktop subprocess protocol."""
import argparse
from contextlib import redirect_stdout
import copy
from datetime import datetime,timezone,date,time
import json
from pathlib import Path
import sys
import time as clock
from .paper_strategies import STRATEGIES
from .paper_engine import configuration,NY
from .paper_store import PaperStore
from .market_repository import market_data_connection
from .market_payloads import assemble
from .watchlist import precheck
from .watchlist_store import WatchlistStore


def fetch(symbols,port,refresh=False):
    with market_data_connection(port=port,update=not refresh,refresh=refresh) as service:
        check=precheck(service,symbols)
        if not check['passed']: raise ValueError('Paper universe precheck failed: '+json.dumps(check['invalid']+check['unverified'],ensure_ascii=False))
        parts=[service.paper_inputs(symbols[i:i+20]) for i in range(0,len(symbols),20)]
    return parts[0] if len(parts)==1 else assemble(parts,'paper_inputs',dict(symbols=symbols))


def through(payload,end):
    from .market_sessions import EARLY
    result=copy.deepcopy(payload)
    for row in result['daily_series']:
        row['bars']=[b for b in row['bars'] if b['date']<=end]
        if not row['bars']: raise ValueError('No data before backtest end')
        row['calendar_dates']=[b['date'] for b in row['bars']]
        row['as_of']=row['bars'][-1]['date']
        early=row['as_of'] in EARLY
        row['trade_date_type']='MORNING' if early else 'WHOLE'
        row['available_at']=datetime.combine(date.fromisoformat(row['as_of']),time(13,5) if early else time(16,5),NY).isoformat()
    return result


def main(argv=None):
    parser=argparse.ArgumentParser(description='Research-only virtual stock accounts; never sends broker orders')
    sub=parser.add_subparsers(dest='action',required=True)
    for action in ('strategies','list','create','backtest','update','report','watch'):
        command=sub.add_parser(action)
        command.add_argument('--output',type=Path)
        if action in ('update','report','watch'): command.add_argument('id',type=int)
        if action in ('create','backtest'):
            command.add_argument('--name',default='Strategy comparison')
            command.add_argument('--symbols',nargs='+',help='Defaults to the SQLite Watchlist; frozen at creation')
            command.add_argument('--clients',type=int,default=6)
            command.add_argument('--notional',type=float,default=10000)
            command.add_argument('--slippage-bps',type=float,default=5)
            command.add_argument('--fee-bps',type=float,default=1)
        if action in ('create','backtest','update','watch'):
            command.add_argument('--port',type=int,default=11111)
            command.add_argument('--refresh',action='store_true')
            command.add_argument('--input',type=Path,help='Raw paper_inputs JSON, for offline reproducibility')
        if action=='backtest':
            command.add_argument('--start',required=True)
            command.add_argument('--end')
        if action=='watch': command.add_argument('--interval',type=int,default=300)
    args=parser.parse_args(argv)
    if getattr(args,'input',None) and getattr(args,'refresh',False): parser.error('--input and --refresh are mutually exclusive')
    def emit(value):
        raw=json.dumps(value,ensure_ascii=False,allow_nan=False)
        if args.output: args.output.write_text(raw,encoding='utf-8')
        elif sys.stdout is not None: print(raw,flush=True)
    def inputs(symbols):
        return json.loads(args.input.read_text(encoding='utf-8')) if args.input else fetch(symbols,args.port,args.refresh)
    if sys.stderr is None:
        import os
        sys.stderr=open(os.devnull,'w',encoding='utf-8')
    try:
        if args.action=='strategies': emit(STRATEGIES); return 0
        store=PaperStore()
        if args.action=='list': emit(store.list()); return 0
        if args.action=='report': emit(store.report(args.id)); return 0
        if args.action in ('create','backtest'):
            from .watchlist import normalize_stock
            symbols=list(dict.fromkeys(normalize_stock(s) for s in args.symbols)) if args.symbols else WatchlistStore().symbols()
            config=configuration(symbols,args.clients,args.notional,args.slippage_bps,args.fee_bps)
            if args.action=='backtest':
                date.fromisoformat(args.start)
                if args.end:
                    date.fromisoformat(args.end)
                    if args.end<args.start: raise ValueError('Backtest end cannot be before start')
            with redirect_stdout(sys.stderr): data=inputs(config['market_symbols'])
            if args.action=='backtest' and args.end: data=through(data,args.end)
            result=store.create(args.name,data,config,mode='backtest' if args.action=='backtest' else 'forward',start=getattr(args,'start',None))
            if args.action=='backtest': result=store.update(result['id'],data)
            emit(result); return 0
        _,state,_=store.load(args.id)
        if state['mode']!='forward': raise ValueError('Historical experiments are fixed; create another backtest to change the window')
        if args.action=='watch' and not 60<=args.interval<=86400: raise ValueError('Watch interval must be 60–86400 seconds')
        while True:
            try:
                with redirect_stdout(sys.stderr): data=inputs(state['config'].get('market_symbols',state['config']['symbols']))
                emit(store.update(args.id,data))
            except Exception as error:
                if args.action!='watch': raise
                emit(dict(error=str(error),id=args.id,retry_seconds=args.interval))
            if args.action!='watch': return 0
            clock.sleep(args.interval)
    except KeyboardInterrupt: return 0
    except Exception as error:
        emit(dict(error=str(error))); return 1


if __name__=='__main__': raise SystemExit(main())
