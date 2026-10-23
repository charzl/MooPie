"""Persistent security identities and explicit aliases, independent of quotes."""
from datetime import datetime, timezone
import json
from pathlib import Path
import unicodedata

from .market_store import SnapshotStore
from .watchlist import normalize_stock


def normalize_name(value):
    return ' '.join(unicodedata.normalize('NFKC', value).casefold().split())


def search_pattern(value):
    """Only * and ? are wildcards; SQL %, _ and backslash remain literal."""
    value = normalize_name(value)
    if len(value) > 120: raise ValueError('搜索内容不能超过120个字符。')
    if not value or not any(c not in '*? ' for c in value): return None
    pattern = ''.join({'*': '%', '?': '_', '%': '\\%', '_': '\\_', '\\': '\\\\'}.get(c, c) for c in value)
    return pattern if '*' in value or '?' in value else pattern + '%'


class SecurityDirectory:
    def __init__(self, store=None):
        self.store = store or SnapshotStore()

    def ingest(self, payload):
        """Atomically merge explicit provider records; absence never implies delisting."""
        timestamp = datetime.fromisoformat(payload['collected_at'])
        if timestamp.tzinfo is None: raise ValueError('Directory timestamp must include a timezone')
        stamp = timestamp.astimezone(timezone.utc).isoformat()
        source = payload['source']
        rows, skipped = {}, []
        for item in payload['rows']:
            if item.get('stock_type') not in ('STOCK', 'ETF'): continue
            try: code = normalize_stock(item['code'])
            except ValueError:
                skipped.append(dict(code=item['code'], reason='Unsupported stock code format'))
                continue
            if not isinstance(item.get('name'), str) or not item['name'].strip() or type(item.get('delisting')) is not bool:
                raise ValueError('Incomplete security metadata: ' + code)
            row = (code, code.removeprefix('US.'), item['name'].strip(), normalize_name(item['name']),
                   item['stock_type'], 'delisted' if item['delisting'] else 'active', source, stamp)
            if code in rows and rows[code] != row: raise ValueError('Conflicting directory records: ' + code)
            rows[code] = row
        if not rows: raise ValueError('Empty security directory; previous records retained')
        aliases = json.loads((Path(__file__).with_name('data')/'security_aliases.json').read_text(encoding='utf-8'))
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            db.executemany('''INSERT INTO securities
                (code,ticker,name,normalized_name,security_type,status,source,updated_at) VALUES (?,?,?,?,?,?,?,?)
                ON CONFLICT(code) DO UPDATE SET name=excluded.name, normalized_name=excluded.normalized_name,
                security_type=excluded.security_type,status=excluded.status,source=excluded.source,updated_at=excluded.updated_at
                WHERE excluded.updated_at >= securities.updated_at''', rows.values())
            for entry in aliases:
                for alias in entry['aliases']:
                    db.execute('''INSERT INTO security_aliases(security_id,alias,normalized_alias,alias_type,source)
                        SELECT id,?,?,?,? FROM securities WHERE code=?
                        ON CONFLICT(security_id,normalized_alias) DO NOTHING''',
                        (alias, normalize_name(alias), entry['alias_type'], entry['source'], entry['code']))
        return dict(action='directory_sync', imported=len(rows), skipped=skipped, **self.status())

    def status(self):
        with self.store.connect() as db:
            count, updated = db.execute('SELECT count(*),max(updated_at) FROM securities').fetchone()
            aliases = db.execute('SELECT count(*) FROM security_aliases').fetchone()[0]
        return dict(securities=count, aliases=aliases, updated_at=updated)

    def lookup(self, codes):
        """Read local names and security types for an explicit stock list."""
        if not codes: return {}
        normalized = [normalize_stock(code) for code in codes]
        placeholders = ','.join('?' for _ in normalized)
        with self.store.connect() as db:
            rows = db.execute(f'SELECT code,name,security_type FROM securities WHERE code IN ({placeholders})',
                              normalized).fetchall()
        return {code: dict(name=name, security_type=kind) for code,name,kind in rows}

    def search(self, text, limit=20):
        pattern = search_pattern(text)
        if pattern is None: return []
        if type(limit) is not int or not 1 <= limit <= 50: raise ValueError('Search limit must be 1–50')
        query = normalize_name(text)
        with self.store.connect() as db:
            rows = db.execute(r'''WITH matches AS (
                SELECT s.*, '' AS matched_alias, 0 AS alias_match FROM securities s
                WHERE status='active' AND (ticker LIKE :pattern ESCAPE '\' OR code LIKE :pattern ESCAPE '\'
                                          OR normalized_name LIKE :pattern ESCAPE '\')
                UNION ALL
                SELECT s.*, a.alias AS matched_alias, 1 AS alias_match FROM securities s
                JOIN security_aliases a ON a.security_id=s.id
                WHERE s.status='active' AND a.normalized_alias LIKE :pattern ESCAPE '\'
            ), ranked AS (
                SELECT *, CASE WHEN lower(code)=:query OR lower(ticker)=:query THEN 0
                    WHEN normalized_name=:query THEN 1
                    WHEN lower(matched_alias)=:query THEN 2
                    WHEN ticker LIKE :pattern ESCAPE '\' OR code LIKE :pattern ESCAPE '\' THEN 3
                    WHEN normalized_name LIKE :pattern ESCAPE '\' THEN 4 ELSE 5 END AS relevance
                FROM matches
            ), unique_matches AS (
                SELECT *, row_number() OVER (PARTITION BY id ORDER BY relevance,alias_match,matched_alias) AS position
                FROM ranked
            ) SELECT code,name,security_type,matched_alias FROM unique_matches WHERE position=1
              ORDER BY relevance,length(ticker),ticker LIMIT :limit''',
                dict(pattern=pattern, query=query, limit=limit)).fetchall()
        return [dict(code=r[0], name=r[1], security_type=r[2], matched_alias=r[3]) for r in rows]

    def add_alias(self, code, alias, *, source, alias_type='user'):
        code = normalize_stock(code)
        if not normalize_name(alias) or '*' in alias or '?' in alias: raise ValueError('Provide a literal alias')
        with self.store.connect() as db:
            row = db.execute('SELECT id FROM securities WHERE code=?', (code,)).fetchone()
            if row is None: raise ValueError('Security is not in the directory: ' + code)
            db.execute('''INSERT INTO security_aliases VALUES (?,?,?,?,?)
                ON CONFLICT(security_id,normalized_alias) DO UPDATE SET alias=excluded.alias,
                alias_type=excluded.alias_type,source=excluded.source''',
                (row[0], alias.strip(), normalize_name(alias), alias_type, source))
