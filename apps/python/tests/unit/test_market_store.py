"""Retention boundaries, cross-process policy, schema migration and maintenance CLI."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing, redirect_stdout
from datetime import datetime, timedelta, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
import zlib

from moopython.market_store import SnapshotStore
from moopython.database import SCHEMA_VERSION

NOW = datetime(2026, 10, 17, 12, tzinfo=timezone.utc)


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / 'market.sqlite3'
        self.store = SnapshotStore(self.path)

    def tearDown(self): self.temp.cleanup()

    def save(self, age, symbol='US.AAA', payload=None):
        timestamp = NOW - timedelta(days=age)
        key = json.dumps(dict(operation='collect_put_dataset', parameters=dict(symbols=[symbol], months=3)))
        return self.store.save(key, timestamp.date().isoformat(), timestamp.isoformat(), payload or dict(age=age))

    def test_cleanup_is_strictly_before_cutoff_and_uses_original_collection_time(self):
        old = self.save(181)
        boundary = self.save(180, 'US.BBB')
        recent = self.save(179, 'US.CCC')
        preview = self.store.cleanup(180, dry_run=True, now=NOW)
        self.assertEqual((preview['eligible'], preview['deleted']), (1, 0))
        self.assertGreater(preview['eligible_compressed_bytes'], 0)
        self.assertEqual(self.store.status()['snapshots'], 3)
        result = self.store.cleanup(180, now=NOW)
        self.assertEqual(result['deleted'], 1)
        with self.store.connect() as db:
            self.assertEqual([r[0] for r in db.execute('SELECT id FROM snapshots ORDER BY id')], [boundary, recent])
        self.assertNotEqual(old, boundary)

    def test_automatic_cleanup_disabled_until_configured_and_shared_by_instances(self):
        self.save(181)
        self.assertIsNone(self.store.maybe_cleanup(NOW))
        self.assertEqual(self.store.status()['snapshots'], 1)
        self.store.set_retention(180)
        other = SnapshotStore(self.path)
        self.assertEqual(other.maybe_cleanup(NOW)['deleted'], 1)
        self.assertIsNone(self.store.maybe_cleanup(NOW + timedelta(hours=23)))
        self.assertEqual(self.store.maybe_cleanup(NOW + timedelta(hours=24))['deleted'], 0)
        self.store.set_retention(0)
        self.save(190)
        self.assertIsNone(other.maybe_cleanup(NOW + timedelta(days=2)))
        self.assertEqual(other.status()['snapshots'], 1)

    def test_policy_change_runs_next_query_and_dry_run_never_throttles_automatic_job(self):
        self.save(150)
        self.store.set_retention(180)
        self.store.maybe_cleanup(NOW)
        self.store.set_retention(90)
        self.store.cleanup(dry_run=True, now=NOW)
        self.assertEqual(self.store.maybe_cleanup(NOW)['deleted'], 1)

    def test_concurrent_workers_clean_only_once(self):
        for _ in range(5): self.save(181)
        self.store.set_retention(180)
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(lambda _: SnapshotStore(self.path).maybe_cleanup(NOW), range(4)))
        self.assertEqual(len([r for r in results if r is not None]), 1)
        self.assertEqual(sum(r['deleted'] for r in results if r), 5)

    def test_invalid_days_do_not_delete_and_disabled_policy_requires_explicit_age(self):
        self.save(200)
        for days in (-1, 0, 36501, True, 1.5, '180'):
            with self.subTest(days=days), self.assertRaises(ValueError): self.store.cleanup(days, now=NOW)
        with self.assertRaisesRegex(ValueError, 'policy'): self.store.cleanup(now=NOW)
        for days in (-1, True, 1.5):
            with self.assertRaises(ValueError): self.store.set_retention(days)
        with self.assertRaisesRegex(ValueError, 'timezone'):
            self.store.cleanup(180, now=NOW.replace(tzinfo=None))
        self.assertEqual(self.store.status()['snapshots'], 1)

    def test_timezones_and_subsecond_boundary(self):
        cutoff = NOW - timedelta(days=180)
        key = json.dumps(dict(operation='snapshots', parameters=dict(codes=['US.AAA261218P90000'])))
        self.store.save(key, cutoff.date().isoformat(), cutoff.astimezone(timezone(timedelta(hours=-7))).isoformat(), {})
        self.store.save(key, cutoff.date().isoformat(), (cutoff-timedelta(microseconds=1)).isoformat(), {})
        self.store.save(key, cutoff.date().isoformat(), (cutoff+timedelta(microseconds=1)).isoformat(), {})
        self.assertEqual(self.store.cleanup(180, now=NOW)['deleted'], 1)
        with self.store.connect() as db:
            self.assertEqual({r[0] for r in db.execute('SELECT symbol FROM snapshots')}, {'US.AAA'})

    def seed_v1(self):
        raw = json.dumps(dict(contracts=[dict(symbol='US.AAA', strike=90.5)], note='原始行情')).encode()
        blob = zlib.compress(raw)
        key = json.dumps(dict(operation='collect_put_dataset', parameters=dict(symbols=['US.AAA'], months=3)))
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute('''CREATE TABLE snapshots(id INTEGER PRIMARY KEY, request_key TEXT NOT NULL,
                session_date TEXT NOT NULL, fetched_at TEXT NOT NULL, saved_at TEXT NOT NULL,
                checksum TEXT NOT NULL, payload BLOB NOT NULL)''')
            db.execute('CREATE INDEX snapshot_lookup ON snapshots(request_key, session_date, fetched_at DESC, id DESC)')
            db.execute('INSERT INTO snapshots VALUES (?, ?, ?, ?, ?, ?, ?)',
                       (7, key, '2026-10-16', NOW.isoformat(), NOW.isoformat(), hashlib.sha256(raw).hexdigest(), blob))
            db.execute('PRAGMA user_version=1')
        return key, json.loads(raw), blob

    def test_v1_upgrade_preserves_ids_compressed_history_and_request_keys(self):
        key, payload, blob = self.seed_v1()
        saved = self.store.latest(key, '2026-10-16')
        self.assertEqual((saved['id'], saved['payload']), (7, payload))
        with self.store.connect() as db:
            self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0], SCHEMA_VERSION)
            self.assertEqual(db.execute('SELECT payload, symbol, operation FROM snapshots').fetchone(),
                             (blob, 'US.AAA', 'collect_put_dataset'))
        self.assertEqual(self.store.status()['retention_days'], 0)

    def test_failed_migration_rolls_back_original_database(self):
        key, payload, blob = self.seed_v1()
        with patch.object(SnapshotStore, '_metadata', side_effect=RuntimeError('migration interrupted')):
            with self.assertRaisesRegex(RuntimeError, 'interrupted'): self.store.status()
        with closing(sqlite3.connect(self.path)) as db:
            self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0], 1)
            self.assertEqual(db.execute('SELECT payload FROM snapshots').fetchone()[0], blob)
            self.assertEqual(len(db.execute('PRAGMA table_info(snapshots)').fetchall()), 7)
        self.assertEqual(self.store.latest(key, '2026-10-16')['payload'], payload)

    def test_sql_failure_rolls_back_schema_and_version_before_retry(self):
        from moopython.database import _execute
        key, payload, blob = self.seed_v1()
        def interrupted(connection, script):
            _execute(connection, script)
            connection.execute('INSERT INTO nonexistent_table VALUES (1)')
        with patch('moopython.database._execute', side_effect=interrupted):
            with self.assertRaisesRegex(RuntimeError, 'nonexistent_table'): self.store.status()
        with closing(sqlite3.connect(self.path)) as db:
            self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0], 1)
            self.assertEqual(db.execute('SELECT payload FROM snapshots').fetchone()[0], blob)
            self.assertEqual(db.execute("SELECT count(*) FROM sqlite_master WHERE name='snapshots_v1'").fetchone()[0], 0)
        self.assertEqual(self.store.latest(key, '2026-10-16')['payload'], payload)

    def test_current_database_reopens_without_migration_or_data_changes(self):
        self.save(20)
        self.store.set_retention(180)
        with self.store.connect() as db:
            before = db.execute('SELECT * FROM snapshots').fetchall()
            settings = db.execute('SELECT * FROM settings').fetchall()
        with patch('moopython.market_store.migrate', side_effect=AssertionError('Already current')):
            with SnapshotStore(self.path).connect() as db:
                self.assertEqual(db.execute('SELECT * FROM snapshots').fetchall(), before)
                self.assertEqual(db.execute('SELECT * FROM settings').fetchall(), settings)

    def test_generated_schema_matches_migrations_and_recreates_tables_and_indexes(self):
        from moopython.database import ROOT, schema_sql
        generated = schema_sql()
        self.assertEqual((ROOT / 'schema.sql').read_text(encoding='utf-8'), generated)
        with closing(sqlite3.connect(':memory:')) as recreated, self.store.connect() as migrated:
            recreated.executescript(generated)
            query = "SELECT type, name, sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' ORDER BY name"
            self.assertEqual(recreated.execute(query).fetchall(), migrated.execute(query).fetchall())
            self.assertEqual(recreated.execute('PRAGMA user_version').fetchone()[0], SCHEMA_VERSION)

    def test_schema_command_uses_only_memory_and_does_not_open_user_database(self):
        from moopython.database_cli import main
        with patch.dict(os.environ, {'MOOMOO_DB_PATH': str(self.path)}), \
                patch('moopython.database.sqlite3.connect', wraps=sqlite3.connect) as connect, \
                redirect_stdout(io.StringIO()) as stream:
            self.assertEqual(main(['schema']), 0)
        self.assertTrue(all(call.args == (':memory:',) for call in connect.call_args_list))
        self.assertIn('CREATE TABLE snapshots', stream.getvalue())
        self.assertFalse(self.path.exists())

    def test_deleted_snapshot_ids_are_never_reused(self):
        old = self.save(200)
        self.store.cleanup(180, now=NOW)
        self.assertGreater(self.save(0), old)

    def test_deleted_pages_are_reusable_and_explicit_vacuum_reclaims_them(self):
        self.save(200, payload=dict(data=os.urandom(250000).hex()))
        self.save(1)
        self.store.cleanup(180, now=NOW)
        self.assertGreater(self.store.status()['reusable_bytes'], 0)
        self.assertTrue(self.store.vacuum()['vacuum_completed'])
        self.assertEqual(self.store.status()['reusable_bytes'], 0)
        self.assertEqual(self.store.status()['snapshots'], 1)

    def test_cli_policy_preview_and_cleanup_are_local_only(self):
        from moopython.database_cli import main
        self.save(300)
        with patch.dict(os.environ, {'MOOMOO_DB_PATH': str(self.path)}), \
                patch('socket.create_connection', side_effect=AssertionError('Maintenance cannot connect to OpenD')):
            for arguments, expected in [(['retention', '--days', '180'], 'retention_days'),
                                        (['cleanup', '--dry-run'], 'eligible'),
                                        (['cleanup'], 'deleted'), (['status'], 'snapshots')]:
                with redirect_stdout(io.StringIO()) as stream:
                    self.assertEqual(main(arguments), 0)
                result = json.loads(stream.getvalue())
                self.assertIn(expected, result)
                if '--dry-run' in arguments: self.assertEqual(self.store.status()['snapshots'], 1)
            self.assertEqual(self.store.status()['snapshots'], 0)


if __name__ == '__main__': unittest.main()
