"""Shared session router: live collection during trading, persisted snapshots after.

The live connection is lazy: cache-only requests never open a socket/import the SDK.
Raw collection and strategy analysis remain separate from this storage policy.
"""
from contextlib import contextmanager, ExitStack
from datetime import date, datetime, timezone, timedelta, time
import json
import re
from uuid import uuid4

from .market_collection import opend_connection, us_symbols
from .market_sessions import market_session, previous_session, EARLY, NY
from .market_store import SnapshotStore
from .market_payloads import partition, project, assemble, underlying


class CacheMissError(RuntimeError):
    """A matching snapshot is absent; this does not establish an invalid symbol."""


class CachedMarketData:
    def __init__(self, host='127.0.0.1', port=11111, *, store=None, refresh=False,
                 update=False, max_age_seconds=60, connection=opend_connection, clock=None):
        if host not in ('127.0.0.1', 'localhost', '::1') or type(port) is not int or not 1 <= port <= 65535:
            raise ValueError('OpenD must use a loopback host and port 1–65535')
        if refresh and update: raise ValueError('Choose incremental update or force refresh')
        if type(max_age_seconds) is not int or not 1 <= max_age_seconds <= 3600:
            raise ValueError('Cache max age must be 1–3600 seconds')
        self.host, self.port = host, port
        self.store = store or SnapshotStore()
        self.refresh, self.connection = refresh, connection
        self.update, self.max_age_seconds = update, max_age_seconds
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.stack, self.live = ExitStack(), None
        self.maintenance_checked, self.maintenance = False, None

    def close(self):
        self.stack.close()

    def _key(self, operation, parameters):
        return json.dumps(dict(provider='moomoo OpenD', host=self.host, port=self.port,
                               cache_schema=1, operation=operation, parameters=parameters), sort_keys=True)

    def _save(self, operation, parameters, kind, symbols, fetched_at, payload, batch_id):
        session = market_session(datetime.fromisoformat(fetched_at), kind, symbols)
        snapshot_id = self.store.save(self._key(operation, parameters), session['session_date'],
                                      fetched_at, payload, batch_id=batch_id)
        field, subjects = partition(operation, parameters)
        if len(subjects) > 1:
            for subject in subjects:
                single = dict(parameters, **{field: [subject]})
                part_session = market_session(datetime.fromisoformat(fetched_at), kind, [underlying(subject)])
                self.store.save(self._key(operation, single), part_session['session_date'], fetched_at,
                                project(payload, operation, subject), batch_id=batch_id)
        return snapshot_id

    def _read(self, operation, parameters, session_date):
        field, subjects = partition(operation, parameters)
        parent = self.store.latest(self._key(operation, parameters), session_date)
        if len(subjects) < 2: return parent
        parts, members, missing = [], [], []
        for subject in subjects:
            single = self.store.latest(self._key(operation, dict(parameters, **{field: [subject]})), session_date)
            if parent is not None and (single is None or datetime.fromisoformat(parent['fetched_at']) > datetime.fromisoformat(single['fetched_at'])):
                # Existing v1 batches remain readable without discarding history.
                single = dict(parent, payload=project(parent['payload'], operation, subject))
            if single is None:
                missing.append(subject)
            else:
                parts.append(single)
                members.append(dict(subject=subject, snapshot_id=single['id'], batch_id=single['batch_id'],
                                    fetched_at=single['fetched_at']))
        if missing:
            raise CacheMissError('盘后数据库缺少这些股票 / 合约的匹配快照：' + ', '.join(missing)
                               + '。请使用 --refresh 主动采集；已有股票的数据仍保留。')
        if parent is not None and all(part['batch_id'] == parent['batch_id'] for part in parts):
            return dict(parent, members=members)
        latest = max(parts, key=lambda part: datetime.fromisoformat(part['fetched_at']))
        return dict(id=None, batch_id=None, fetched_at=latest['fetched_at'], saved_at=latest['saved_at'],
                    payload=assemble([part['payload'] for part in parts], operation, parameters), members=members)

    def _reusable(self, saved, operation, parameters, kind, symbols, session, now):
        if saved is None: return False
        collected = datetime.fromisoformat(saved['fetched_at'])
        if collected > now: return False
        if operation == 'basic_info':
            return set(parameters['codes']) <= {row.get('code') for row in saved['payload'].get('rows', [])}
        if operation == 'daily_bars':
            if parameters.get('cutoff') or parameters.get('session_date'): return True
            expected = session['session_date']
            if session['is_open']: expected = previous_session(date.fromisoformat(expected)-timedelta(days=1)).isoformat()
            series = saved['payload'].get('daily_series', [])
            return bool(series) and all(not row.get('error') and row.get('as_of') == expected for row in series)
        if session['is_open']:
            return (now-collected).total_seconds() < self.max_age_seconds
        # An intraday/break snapshot cannot become a closing snapshot by waiting.
        day = date.fromisoformat(session['session_date'])
        close = time(13,15) if day.isoformat() in EARLY else time(16,15)
        if kind == 'daily': close = time(13,5) if day.isoformat() in EARLY else time(16,5)
        if kind == 'stocks': close = time(20)
        return collected >= datetime.combine(day, close, NY)

    def _call(self, operation, parameters, kind, symbols=()):
        now = self.clock()
        session = market_session(now, kind, symbols)
        if not self.maintenance_checked:
            self.maintenance = self.store.maybe_cleanup(self.clock())
            self.maintenance_checked = True
        saved = None
        if self.update:
            field, subjects = partition(operation, parameters)
            if len(subjects) > 1:
                parts = [self._call(operation, dict(parameters, **{field:[subject]}), kind, [underlying(subject)])
                         for subject in subjects]
                result = assemble(parts, operation, parameters)
                members = [dict(subject=subject, **part['data_access']) for subject,part in zip(subjects,parts)]
                sources = {part['data_access']['source'] for part in parts}
                result['data_access'] = dict(source=next(iter(sources)) if len(sources)==1 else 'mixed',
                    fetched_at=max((part['data_access']['fetched_at'] for part in parts), key=datetime.fromisoformat),
                    snapshot_id=None, batch_id=None, explicit_refresh=False, market=session,
                    incremental_update=True, members=members,
                    note='逐项检查缓存，只补抓缺失或过期数据；成员保留各自采集时间。')
                return result
            saved = self._read(operation, parameters, session['session_date'])
            if operation == 'daily_bars' and session['is_open'] and not saved and not parameters.get('cutoff') and not parameters.get('session_date'):
                previous = previous_session(date.fromisoformat(session['session_date'])-timedelta(days=1)).isoformat()
                saved = self._read(operation, parameters, previous)
            if not self._reusable(saved, operation, parameters, kind, symbols, session, now): saved = None
        fetch = (saved is None) if self.update else (self.refresh or session['is_open'])
        if fetch:
            if self.live is None:
                self.live = self.stack.enter_context(self.connection(host=self.host, port=self.port))
            payload = getattr(self.live, operation)(**parameters)
            fetched_at = payload.get('collected_at') or payload.get('fetched_at') or payload.get('queried_at')
            if not fetched_at:
                raise RuntimeError('Provider result is missing its original collection timestamp')
            # Route/store by the time collection actually completed. Never label a
            # request crossing a session boundary with its starting trading date.
            raw = dict(payload)
            raw.pop('data_access', None)
            batch_id = str(uuid4())
            snapshot_id = self._save(operation, parameters, kind, symbols, fetched_at, raw, batch_id)
            if operation == 'collect_put_dataset' and payload.get('decision_cutoff') and payload.get('fetched_at'):
                # The integrated collector already fetched these exact daily-bar
                # records. Reuse them for the trend action instead of fetching twice.
                daily = {k: v for k, v in raw.items() if k in (
                    'schema', 'source', 'trend_as_of', 'trend_collected_at',
                    'trend_decision_cutoff', 'daily_series', 'decision_cutoff', 'fetched_at')}
                self._save('daily_bars', dict(symbols=parameters['symbols'], session_date=None, cutoff=None),
                           'daily', symbols, daily['fetched_at'], daily, batch_id)
            access = dict(source='OpenD', snapshot_id=snapshot_id, fetched_at=fetched_at,
                          batch_id=batch_id, explicit_refresh=self.refresh, market=session)
        else:
            if saved is None: saved = self._read(operation, parameters, session['session_date'])
            if saved is None:
                raise CacheMissError(f'盘后数据库没有 {session["session_date"]} 的匹配快照。'
                                   '默认不会连接 OpenD；请在桌面选择“更新行情”，或使用 --refresh'
                                   '（MCP: refresh=true）。旧交易日的数据不会冒充最新行情。')
            payload = saved['payload']
            if not self.update and operation == 'daily_bars' and not parameters.get('cutoff') and not parameters.get('session_date'):
                if any(s.get('as_of', '') < session['session_date'] for s in payload.get('daily_series', [])):
                    raise RuntimeError('数据库日线尚未包含最近完成的交易日，请选择“更新行情”或使用 --refresh。')
            access = dict(source='database', snapshot_id=saved['id'],
                          fetched_at=saved['fetched_at'], saved_at=saved['saved_at'],
                          batch_id=saved['batch_id'], explicit_refresh=False, market=session)
            if saved.get('members'): access['members'] = saved['members']
        collected = datetime.fromisoformat(access['fetched_at'])
        original = market_session(collected, kind, symbols)
        access['captured_during_session'] = original['is_open']
        access['note'] = ('数据库保存的原始快照；不是当前可成交报价。'
                          + ('采集于盘中，不代表收盘快照。' if original['is_open'] else '')
                          if access['source'] == 'database' else '已抓取 OpenD 并保存原始快照。')
        if access.get('members'):
            access['note'] += '多股票组合保留各自采集时间，不代表同时报价。'
        if operation == 'basic_info':
            access['note'] = ('数据库保存的证券基本资料；验证时点为原始采集时间。'
                              if access['source'] == 'database' else '已读取 OpenD 证券基本资料并保存。')
        if self.update:
            access['incremental_update'] = True
            access['cache_reused'] = access['source'] == 'database'
            access['max_age_seconds'] = self.max_age_seconds
        if self.maintenance is not None: access['cleanup'] = self.maintenance
        return dict(payload, data_access=access)

    def collect_put_dataset(self, symbols, months=3):
        symbols = us_symbols(symbols)
        if type(months) is not int or not 1 <= months <= 24:
            raise ValueError('months must be 1–24')
        return self._call('collect_put_dataset', dict(symbols=symbols, months=months), 'options', symbols)

    def snapshots(self, codes):
        codes = us_symbols(codes, maximum=200)
        options_only = all(re.fullmatch(r'US\.[A-Z.]+\d{6}[CP]\d+', code) for code in codes)
        roots = [re.sub(r'\d{6}[CP]\d+$', '', code) for code in codes]
        return self._call('snapshots', dict(codes=codes), 'options' if options_only else 'stocks', roots)

    def basic_info(self, codes):
        codes = us_symbols(codes, maximum=200)
        return self._call('basic_info', dict(codes=codes), 'daily', codes)

    def option_chain(self, symbol, months=3, option_type='PUT', start=None, end=None):
        from .options import OptionQuery
        symbol = us_symbols([symbol])[0]
        if type(months) is not int or not 1 <= months <= 24:
            raise ValueError('months must be 1–24')
        # Validate explicit dates/type using the canonical collector query model.
        OptionQuery.upcoming(symbol, months=months, option_type=option_type, start=start, end=end)
        return self._call('option_chain', dict(symbol=symbol, months=months,
                          option_type=option_type.upper(), start=start, end=end), 'options', [symbol])

    def daily_bars(self, symbols, session_date=None, cutoff=None):
        symbols = us_symbols(symbols)
        now = self.clock()
        if cutoff is not None:
            parsed = datetime.fromisoformat(cutoff)
            if parsed.tzinfo is None or parsed > now:
                raise ValueError('cutoff must be timezone-aware and cannot be in the future')
        if session_date is not None:
            from .market_sessions import NY
            limit = datetime.fromisoformat(cutoff) if cutoff else now
            if date.fromisoformat(session_date) > limit.astimezone(NY).date():
                raise ValueError('session_date cannot be after the decision cutoff')
        return self._call('daily_bars', dict(symbols=symbols, session_date=session_date, cutoff=cutoff), 'daily', symbols)

    def earnings_calendar(self, start, end):
        if not 0 <= (date.fromisoformat(end) - date.fromisoformat(start)).days <= 6:
            raise ValueError('Earnings windows must contain 1–7 calendar days')
        return self._call('earnings_calendar', dict(start=start, end=end), 'daily')


@contextmanager
def market_data_connection(host='127.0.0.1', port=11111, **options):
    service = CachedMarketData(host, port, **options)
    try:
        yield service
    finally:
        service.close()
