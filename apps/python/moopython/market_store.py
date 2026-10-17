"""Compressed market history, versioned migrations and configurable retention."""
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import sys
import time
from uuid import uuid4
import zlib

from .database import SCHEMA_VERSION, migrate


def database_path():
    override = os.environ.get('MOOMOO_DB_PATH')
    if override:
        return Path(override).expanduser()
    if sys.platform == 'win32':
        root = Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData/Local'))
    elif sys.platform == 'darwin':
        root = Path.home() / 'Library/Application Support'
    else:
        root = Path(os.environ.get('XDG_DATA_HOME', Path.home() / '.local/share'))
    return root / 'MooPie' / 'market.sqlite3'


class SnapshotStore:
    def __init__(self, path=None):
        self.path = Path(path) if path is not None else database_path()

    @contextmanager
    def connect(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            connection = sqlite3.connect(self.path, timeout=10)
        except sqlite3.Error as error:
            raise RuntimeError(f'Market database error ({self.path}): {error}') from error
        try:
            connection.execute('PRAGMA foreign_keys=ON')
            version = connection.execute('PRAGMA user_version').fetchone()[0]
            if not 0 <= version <= SCHEMA_VERSION:
                raise RuntimeError('Unsupported market database schema; use the matching application version')
            # SQLite's journal-mode transition can return BUSY immediately even
            # with busy_timeout when two fresh processes initialize the file.
            deadline = time.monotonic()+10
            while True:
                try:
                    connection.execute('PRAGMA journal_mode=WAL')
                    break
                except sqlite3.OperationalError as error:
                    if getattr(error,'sqlite_errorcode',0) & 255 != sqlite3.SQLITE_BUSY or time.monotonic() >= deadline:
                        raise
                    time.sleep(.02)
            if version < SCHEMA_VERSION:
                # Serialize migration and recheck after acquiring the lock: another
                # process might have upgraded the same database while we waited.
                connection.execute('BEGIN IMMEDIATE')
                with connection:
                    if connection.execute('PRAGMA user_version').fetchone()[0] < SCHEMA_VERSION:
                        self._migrate(connection)
            with connection:
                yield connection
        except sqlite3.Error as error:
            raise RuntimeError(f'Market database error ({self.path}): {error}') from error
        finally:
            connection.close()

    @staticmethod
    def _migrate(connection):
        migrate(connection, SnapshotStore._metadata)

    @staticmethod
    def _metadata(request_key):
        try:
            request = json.loads(request_key)
            parameters = request.get('parameters', {})
            symbols = parameters.get('symbols', parameters.get('codes', []))
            symbol = parameters.get('symbol') or (symbols[0] if len(symbols) == 1 else None)
            if symbol:
                from .market_payloads import underlying
                symbol = underlying(symbol)
            return symbol, request.get('operation', 'unknown')
        except (ValueError, AttributeError, TypeError):
            return None, 'unknown'

    def save(self, request_key, session_date, fetched_at, payload, *, batch_id=None):
        timestamp = datetime.fromisoformat(fetched_at)
        if timestamp.tzinfo is None:
            raise ValueError('Snapshot collection timestamp must include a timezone')
        fetched_at = timestamp.astimezone(timezone.utc).isoformat()
        raw = json.dumps(payload, sort_keys=True, ensure_ascii=False, allow_nan=False,
                         separators=(',', ':')).encode('utf-8')
        saved_at = datetime.now(timezone.utc).isoformat()
        symbol, operation = self._metadata(request_key)
        with self.connect() as connection:
            cursor = connection.execute('''INSERT INTO snapshots
                (request_key, session_date, fetched_at, saved_at, checksum, payload, symbol, operation, batch_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''', (request_key, session_date, fetched_at,
                saved_at, hashlib.sha256(raw).hexdigest(), zlib.compress(raw), symbol, operation,
                batch_id or str(uuid4())))
            return cursor.lastrowid

    def latest(self, request_key, session_date):
        with self.connect() as connection:
            row = connection.execute('''SELECT id, fetched_at, saved_at, checksum, payload, batch_id
                FROM snapshots WHERE request_key=? AND session_date=?
                ORDER BY fetched_at DESC, id DESC LIMIT 1''',
                (request_key, session_date)).fetchone()
        if row is None:
            return None
        return self._decode(row)

    @staticmethod
    def _decode(row):
        try:
            raw = zlib.decompress(row[4])
            if hashlib.sha256(raw).hexdigest() != row[3]:
                raise ValueError('checksum mismatch')
            payload = json.loads(raw)
        except (zlib.error, UnicodeError, ValueError) as error:
            raise RuntimeError('Market database snapshot is damaged; refresh explicitly') from error
        return dict(id=row[0], fetched_at=row[1], saved_at=row[2], payload=payload, batch_id=row[5])

    def record(self, snapshot_id):
        with self.connect() as connection:
            row = connection.execute('''SELECT id, fetched_at, saved_at, checksum, payload, batch_id
                FROM snapshots WHERE id=?''', (snapshot_id,)).fetchone()
        if row is None:
            raise RuntimeError('已保存的行情已清理，请点击「更新行情」。')
        return self._decode(row)

    def records(self, operation):
        """Read the small snapshot index without decompressing market payloads."""
        with self.connect() as connection:
            rows = connection.execute('''SELECT id, request_key, session_date, fetched_at
                FROM snapshots WHERE operation=? ORDER BY session_date DESC, fetched_at DESC, id DESC''',
                (operation,)).fetchall()
        return [dict(id=r[0], request_key=r[1], session_date=r[2], fetched_at=r[3]) for r in rows]

    @staticmethod
    def _days(value, allow_zero=False):
        if type(value) is not int or not (0 if allow_zero else 1) <= value <= 36500:
            raise ValueError('Retention days must be an integer from ' + ('0' if allow_zero else '1') + ' to 36500')
        return value

    @staticmethod
    def _setting(connection, key, default=None):
        row = connection.execute('SELECT value FROM settings WHERE key=?', (key,)).fetchone()
        return row[0] if row else default

    @staticmethod
    def _set(connection, key, value):
        connection.execute('INSERT INTO settings(key, value) VALUES (?, ?) '
                           'ON CONFLICT(key) DO UPDATE SET value=excluded.value', (key, str(value)))

    def set_retention(self, days):
        self._days(days, allow_zero=True)
        with self.connect() as connection:
            self._set(connection, 'retention_days', days)
            connection.execute("DELETE FROM settings WHERE key='last_cleanup_at'")
        return dict(retention_days=days, automatic_cleanup_enabled=days > 0)

    def status(self):
        with self.connect() as connection:
            total, first, last = connection.execute('SELECT count(*), min(fetched_at), max(fetched_at) FROM snapshots').fetchone()
            days = int(self._setting(connection, 'retention_days', '0'))
            return dict(path=str(self.path), schema=SCHEMA_VERSION, snapshots=total, oldest_fetched_at=first,
                        newest_fetched_at=last, retention_days=days, automatic_cleanup_enabled=days > 0,
                        last_cleanup_at=self._setting(connection, 'last_cleanup_at'),
                        reusable_bytes=connection.execute('PRAGMA freelist_count').fetchone()[0]
                            * connection.execute('PRAGMA page_size').fetchone()[0])

    def _cleanup(self, connection, days, now, dry_run):
        self._days(days)
        if now.tzinfo is None:
            raise ValueError('Cleanup clock must include a timezone')
        now = now.astimezone(timezone.utc)
        cutoff = (now - timedelta(days=days)).isoformat()
        count, size = connection.execute('SELECT count(*), coalesce(sum(length(payload)), 0) '
                                         'FROM snapshots WHERE fetched_at < ?', (cutoff,)).fetchone()
        if not dry_run:
            connection.execute('DELETE FROM snapshots WHERE fetched_at < ?', (cutoff,))
            self._set(connection, 'last_cleanup_at', now.isoformat())
            self._set(connection, 'last_cleanup_policy_days', days)
        return dict(older_than_days=days, cutoff=cutoff, eligible=count, eligible_compressed_bytes=size,
                    deleted=0 if dry_run else count, dry_run=dry_run)

    def cleanup(self, older_than_days=None, *, dry_run=False, now=None):
        if older_than_days is not None: self._days(older_than_days)
        now = now or datetime.now(timezone.utc)
        with self.connect() as connection:
            connection.execute('BEGIN IMMEDIATE')
            days = older_than_days if older_than_days is not None else int(self._setting(connection, 'retention_days', '0'))
            if days == 0:
                raise ValueError('No retention policy is enabled; specify --older-than-days N or set db retention --days N')
            return self._cleanup(connection, days, now, dry_run)

    def maybe_cleanup(self, now=None):
        now = now or datetime.now(timezone.utc)
        if now.tzinfo is None: raise ValueError('Cleanup clock must include a timezone')
        with self.connect() as connection:
            # All processes share this check, so concurrent desktop/MCP workers
            # cannot each launch a daily deletion for the same database.
            connection.execute('BEGIN IMMEDIATE')
            days = int(self._setting(connection, 'retention_days', '0'))
            if days == 0: return None
            last = self._setting(connection, 'last_cleanup_at')
            same_policy = self._setting(connection, 'last_cleanup_policy_days') == str(days)
            if last and same_policy and now - datetime.fromisoformat(last) < timedelta(days=1):
                return None
            return self._cleanup(connection, days, now, False)

    def vacuum(self):
        # Explicit maintenance only: VACUUM can block other writers and needs free
        # disk space. Ordinary deletion leaves pages available for future reuse.
        with self.connect() as connection:
            connection.execute('VACUUM')
        return dict(path=str(self.path), vacuum_completed=True)
