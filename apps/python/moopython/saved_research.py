"""Desktop opening policy: completed-session inputs and memoized Put reports.

This read-only market service cannot connect to OpenD. Explicit updates keep using
the shared live router. Reports share snapshot compression and retention; their
keys include the exact inputs, settings and analysis source, so changes cannot
silently reuse an obsolete ranking.
"""
from datetime import date, datetime, time, timedelta, timezone
import hashlib
import json
from pathlib import Path

from .market_payloads import assemble, partition, project
from .market_repository import CacheMissError
from .market_sessions import EARLY, NY, market_session, previous_session
from .market_store import SnapshotStore
from .research import load_rules, run_research
from .watchlist_research import run_watchlist_research


def completed_session(now, kind='options'):
    session = market_session(now, kind)
    day = date.fromisoformat(session['session_date'])
    close = time(13, 15) if day.isoformat() in EARLY else time(16, 15)
    if kind == 'daily': close = time(13, 5) if day.isoformat() in EARLY else time(16, 5)
    if now < datetime.combine(day, close, NY):
        day = previous_session(day-timedelta(days=1))
    return day.isoformat()


class SavedMarketData:
    def __init__(self, symbols, port=11111, *, store=None, now=None):
        self.store = store or SnapshotStore()
        self.now = now or datetime.now(timezone.utc)
        self.port = port
        self.target = completed_session(self.now)
        self.store.maybe_cleanup(self.now)
        self.indices = {}
        self.put_records = {symbol:self.candidates('collect_put_dataset', symbol) for symbol in symbols}
        date_sets = [{r['session_date'] for r in rows} for rows in self.put_records.values() if rows]
        common = set.intersection(*date_sets) if date_sets else set()
        # Never merge different quote dates. When no common date exists, display
        # the newest available date and explicitly report missing members.
        self.quote_day = max(common) if common else max((max(days) for days in date_sets), default=self.target)

    def index(self, operation):
        if operation not in self.indices:
            self.indices[operation] = self.store.records(operation)
        return self.indices[operation]

    def candidates(self, operation, symbol, *, completed=True):
        values = []
        for row in self.index(operation):
            key = json.loads(row['request_key'])
            if key.get('provider') != 'moomoo OpenD' or key.get('port') != self.port:
                continue
            if key.get('host') not in ('127.0.0.1','localhost','::1'): continue
            parameters = key.get('parameters', {})
            _, subjects = partition(operation, parameters)
            if symbol not in subjects: continue
            if operation == 'collect_put_dataset' and parameters.get('months') != 3: continue
            if operation == 'daily_bars' and (parameters.get('cutoff') or parameters.get('session_date')): continue
            fetched = datetime.fromisoformat(row['fetched_at'])
            if fetched > self.now: continue
            if completed and operation == 'collect_put_dataset':
                if row['session_date'] > self.target: continue
                day = date.fromisoformat(row['session_date'])
                close = time(13,15) if row['session_date'] in EARLY else time(16,15)
                if fetched < datetime.combine(day,close,NY): continue
            values.append(row)
        return values

    def never_collected(self, symbol, action):
        operation = 'collect_put_dataset' if action == 'put' else 'daily_bars'
        return not self.candidates(operation, symbol, completed=False)

    def selected(self, symbol):
        return next((r for r in self.put_records[symbol] if r['session_date']==self.quote_day), None)

    def read(self, operation, symbol):
        rows = ([self.selected(symbol)] if operation=='collect_put_dataset'
                else self.candidates(operation,symbol))
        for row in rows:
            if row is None: continue
            saved = self.store.record(row['id'])
            payload = project(saved['payload'],operation,symbol)
            if operation=='collect_put_dataset' and payload.get('session_date')!=row['session_date']:
                continue
            if operation=='daily_bars':
                series=payload.get('daily_series',[])
                if not series or any(s.get('as_of','9999') > completed_session(self.now,'daily') for s in series): continue
            access = dict(source='database', snapshot_id=row['id'], fetched_at=row['fetched_at'],
                batch_id=saved['batch_id'], saved_at=saved['saved_at'], explicit_refresh=False,
                market=market_session(self.now,'daily' if operation in ('basic_info','daily_bars') else 'options',[symbol]),
                captured_during_session=False,
                note='读取已保存的收盘数据；点击「更新行情」才刷新已有行情。')
            return dict(payload,data_access=access)
        raise CacheMissError(symbol+' 没有可用的已保存收盘数据，请点击「更新行情」。')

    def collect_put_dataset(self, symbols, months=3):
        return self.read('collect_put_dataset',symbols[0])

    def basic_info(self, codes):
        parts = [self.read('basic_info',code) for code in codes]
        return assemble(parts,'basic_info',dict(codes=codes))

    def daily_bars(self, symbols):
        return self.read('daily_bars',symbols[0])


def analysis_revision():
    rules = load_rules()
    digest = hashlib.sha256(Path(rules.__file__).read_bytes())
    for name in ('research.py','watchlist_research.py','price_signals.py','saved_research.py'):
        # Frozen installations do not necessarily ship source files. Include the
        # compiled module code as a stable implementation identity in that case.
        import importlib, marshal
        module = importlib.import_module('moopython.'+name.removesuffix('.py'))
        code = module.__loader__.get_code(module.__name__)
        digest.update(marshal.dumps(code))
    return digest.hexdigest()


def report_key(service, symbols, configuration, top_n, watchlist):
    config = load_rules().recommendation_configuration(configuration)
    return json.dumps(dict(provider='moomoo research', operation='research_put_report',
        parameters=dict(symbols=symbols, configuration=config, top_n=top_n, watchlist=watchlist,
            source_ids=[[s,(service.selected(s) or {}).get('id')] for s in symbols],
            analysis_revision=analysis_revision())), sort_keys=True)


def remember_closing_result(result, port=11111, *, store=None, now=None):
    """Persist an already-computed close report; intraday updates stay separate."""
    if result.get('action')!='put' or result.get('collection_errors'): return
    access = result.get('data_access',{})
    if not access.get('snapshot_id') and not any(m.get('snapshot_id') for m in access.get('members',[])): return
    dataset = result.get('input_dataset',{})
    symbols = dataset.get('symbols') or [result['symbol']]
    service = SavedMarketData(symbols,port,store=store,now=now)
    if dataset.get('session_date') != service.quote_day: return
    expected = {s:(service.selected(s) or {}).get('id') for s in symbols}
    actual = ({m.get('symbol'):m.get('snapshot_id') for m in access['members']}
              if access.get('members') else {symbols[0]:access.get('snapshot_id')})
    if not all(expected.values()) or expected != actual: return
    report = result['report']
    key = report_key(service,symbols,report['configuration'],report['top_n_requested'],
                     result.get('query_scope')=='watchlist')
    service.store.save(key,service.quote_day,result['collected_at'],result)


def database_access(access, now):
    """Refresh only read provenance, preserving every original quote timestamp."""
    access['source'] = 'database'
    access['explicit_refresh'] = False
    if 'market' in access: access['market'] = market_session(now)
    for member in access.get('members',[]): database_access(member,now)
    if 'reused_symbols' in access:
        access['reused_symbols'] = [m['symbol'] for m in access.get('members',[]) if m.get('symbol')]
        access['fetched_symbols'] = []


def saved_research(symbols, action, configuration=None, top_n=10, *, port=11111,
                   watchlist=False, store=None, now=None):
    service = SavedMarketData(symbols,port,store=store,now=now)
    memo_key = None
    if action=='put':
        memo_key = report_key(service,symbols,configuration,top_n,watchlist)
        memo = service.store.latest(memo_key, service.quote_day)
        if memo:
            result = memo['payload']
        else: result = None
    else: result = None
    precomputed = result is not None
    if result is None:
        result = (run_watchlist_research(service,symbols,action,configuration,top_n) if watchlist
                  else run_research(service,symbols[0],action,configuration,top_n))
    result['saved_view'] = dict(precomputed=precomputed, latest_completed_session=service.target,
                               displayed_session=service.quote_day)
    if action=='put':
        database_access(result['data_access'],service.now)
        result['data_access']['note'] = '读取已保存的收盘结果；点击「更新行情」才刷新已有行情。 最近完成交易日：'+service.target+'。'
        if service.quote_day < service.target:
            result['data_access']['note'] += ' 当前显示更早的结果，请点击「更新行情」获取最近收盘数据。'
        result['input_dataset']['data_access'] = result['data_access']
        if not precomputed: service.store.save(memo_key,service.quote_day,result['collected_at'],result)
    return result
