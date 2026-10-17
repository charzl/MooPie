"""SQLite watchlist, one-time legacy import and validated membership changes."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import tempfile

from .market_store import SnapshotStore
from .watchlist import load_watchlist, normalize_stock, precheck


DEFAULT_SYMBOLS = ('US.AVGO', 'US.NVDA', 'US.AAPL')
INITIALIZED = 'watchlist_initialized'


class WatchlistStore:
    def __init__(self, store=None):
        self.store = store or SnapshotStore()

    def initialize(self):
        """Import existing JSON once, without network or modifications to that file."""
        with self.store.connect() as db:
            if db.execute('SELECT 1 FROM settings WHERE key=?', (INITIALIZED,)).fetchone(): return
            db.execute('BEGIN IMMEDIATE')
            if db.execute('SELECT 1 FROM settings WHERE key=?', (INITIALIZED,)).fetchone(): return
            override = os.environ.get('MOOMOO_WATCHLIST_PATH')
            legacy = Path(override).expanduser() if override else self.store.path.with_name('watchlist.json')
            if override and not legacy.is_file(): raise ValueError('旧 Watchlist JSON 不存在：' + str(legacy))
            if legacy.exists():
                symbols = list(dict.fromkeys(normalize_stock(value) for value in load_watchlist(legacy, allow_empty=True)))
                source = 'legacy_json'
            else:
                symbols, source = DEFAULT_SYMBOLS, 'default'
            stamp = datetime.now(timezone.utc).isoformat()
            if not db.execute('SELECT 1 FROM watchlist LIMIT 1').fetchone():
                db.executemany('INSERT INTO watchlist(symbol,added_at,source) VALUES (?,?,?)',
                               [(code, stamp, source) for code in symbols])
            marker = dict(initialized_at=stamp, source=source)
            if source == 'legacy_json': marker['legacy_path'] = str(legacy.resolve())
            db.execute('INSERT INTO settings(key,value) VALUES (?,?)', (INITIALIZED, json.dumps(marker)))


    def symbols(self):
        self.initialize()
        with self.store.connect() as db:
            return [row[0] for row in db.execute('SELECT symbol FROM watchlist ORDER BY id')]

    def status(self):
        self.initialize()
        with self.store.connect() as db:
            rows = db.execute('''SELECT w.id,w.symbol,w.added_at,w.source,s.name
                FROM watchlist w LEFT JOIN securities s ON s.code=w.symbol ORDER BY w.id''').fetchall()
        return dict(storage='sqlite', database=str(self.store.path), symbols=[row[1] for row in rows],
                    items=[dict(id=r[0],symbol=r[1],added_at=r[2],source=r[3],name=r[4]) for r in rows])

    def _merge(self, symbols, source, *, replace=False):
        # Validate provider identities before entering this write transaction.
        codes = list(dict.fromkeys(normalize_stock(value) for value in symbols))
        self.initialize()
        stamp = datetime.now(timezone.utc).isoformat()
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            if replace: db.execute('DELETE FROM watchlist')
            added = 0
            for code in codes:
                added += db.execute('''INSERT INTO watchlist(symbol,added_at,source) VALUES (?,?,?)
                    ON CONFLICT(symbol) DO NOTHING''', (code, stamp, source)).rowcount
            current = [row[0] for row in db.execute('SELECT symbol FROM watchlist ORDER BY id')]
        return dict(added_count=added, symbols=current, storage='sqlite', database=str(self.store.path))

    def remove_items(self, item_ids):
        ids = set(item_ids)
        if any(type(value) is not int or value <= 0 for value in ids): raise ValueError('Invalid Watchlist item ID')
        self.initialize()
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            removed = sum(db.execute('DELETE FROM watchlist WHERE id=?', (value,)).rowcount for value in ids)
            symbols = [row[0] for row in db.execute('SELECT symbol FROM watchlist ORDER BY id')]
        return dict(removed_count=removed, symbols=symbols)

    def import_json(self, service, path, *, replace=False):
        values = load_watchlist(path, allow_empty=True)
        if not values:
            return dict(action='watchlist_import', replaced=replace, precheck=None,
                        **self._merge([], 'json_import', replace=replace))
        check = precheck(service, values)
        if not check['passed']:
            issues = check['invalid'] + check['unverified']
            raise ValueError('名单未导入：' + '; '.join(str(row['input']) + '：' + row['reason'] for row in issues))
        return dict(action='watchlist_import', replaced=replace, precheck=check,
                    **self._merge(check['valid_symbols'], 'json_import', replace=replace))

    def export_json(self, path):
        values = self.symbols()
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile('w', dir=path.parent, prefix=path.name+'.', suffix='.tmp',
                                             encoding='utf-8', delete=False) as handle:
                temporary = Path(handle.name)
                json.dump(dict(symbols=values), handle, ensure_ascii=False, indent=2)
                handle.write('\n')
            os.replace(temporary, path)
        finally:
            if temporary is not None: temporary.unlink(missing_ok=True)
        return dict(action='watchlist_export', symbols=values, path=str(path))


def add_to_watchlist(service, symbol, watchlist=None):
    watchlist = watchlist or WatchlistStore()
    code = normalize_stock(symbol)
    existing = watchlist.symbols()
    if code in existing:
        return dict(action='watchlist_add', symbol=code, added=False, symbols=existing,
                    storage='sqlite', database=str(watchlist.store.path))
    check = precheck(service, [code])
    if not check['passed']:
        raise ValueError('未加入 Watchlist：' + check['entries'][0]['reason'])
    result = watchlist._merge([code], 'verified_add')
    return dict(action='watchlist_add', symbol=code, added=bool(result['added_count']), precheck=check, **result)
