from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from moopython.market_store import SnapshotStore
from moopython.security_directory import SecurityDirectory


def payload():
    return dict(source='synthetic test directory', collected_at='2026-10-17T15:00:00+00:00', rows=[
        dict(code='US.AVGO', name='Broadcom', stock_type='STOCK', delisting=False),
        dict(code='US.AVG', name='Example company', stock_type='STOCK', delisting=False),
        dict(code='US.AVGOX', name='Different Broadcom fund', stock_type='ETF', delisting=False),
        dict(code='US.BRK.B', name='Berkshire Hathaway Class B', stock_type='STOCK', delisting=False),
        dict(code='US.OLD', name='Old company', stock_type='STOCK', delisting=True)])


class DirectoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = SnapshotStore(Path(self.temp.name)/'market.sqlite3')
        self.directory = SecurityDirectory(self.store)
        self.directory.ingest(payload())

    def tearDown(self): self.temp.cleanup()

    def test_prefix_case_alias_unicode_and_wildcard_matches_are_deduplicated(self):
        for text in ('avago', ' AVAGO ', 'Ａｖａｇｏ', '博通', 'broad*', '*roadcom', 'av?o'):
            with self.subTest(text=text):
                self.assertEqual(self.directory.search(text)[0]['code'], 'US.AVGO')
        self.assertEqual(self.directory.search('avgo')[0]['code'], 'US.AVGO')
        self.assertEqual(self.directory.search('US.AVGO')[0]['code'], 'US.AVGO')
        self.assertEqual(len(self.directory.search('av*')), 3)
        self.assertEqual(self.directory.search('avago')[0]['matched_alias'], 'Avago')
        self.assertEqual(self.directory.search('brk.b')[0]['code'], 'US.BRK.B')
        for value in ('', '*', '???', 'old', "%", '_', "' OR 1=1 --", '[AVGO]'):
            self.assertEqual(self.directory.search(value), [])

    def test_shared_alias_keeps_multiple_candidates_and_does_not_overwrite_identity(self):
        self.directory.add_alias('AVGO', 'Shared name', source='synthetic')
        self.directory.add_alias('AVG', 'Shared name', source='synthetic')
        self.assertEqual({r['code'] for r in self.directory.search('shared')}, {'US.AVGO', 'US.AVG'})
        before = self.directory.status()
        self.directory.ingest(payload())
        self.assertEqual(self.directory.status(), before)
        self.assertEqual(len(self.directory.search('shared')), 2)

    def test_updates_keep_ids_aliases_and_reject_invalid_or_older_data(self):
        with self.store.connect() as db: before = db.execute('SELECT id FROM securities WHERE code=?',('US.AVGO',)).fetchone()
        newer = payload(); newer['collected_at'] = '2026-10-18T15:00:00+00:00'
        newer['rows'][0]['name'] = 'New provider name'
        self.directory.ingest(newer)
        self.directory.ingest(payload())
        self.assertEqual(self.directory.search('avago')[0]['name'], 'New provider name')
        with self.store.connect() as db: self.assertEqual(db.execute('SELECT id FROM securities WHERE code=?',('US.AVGO',)).fetchone(),before)
        broken = payload(); broken['rows'][0]['delisting'] = None
        with self.assertRaises(ValueError): self.directory.ingest(broken)
        self.assertEqual(self.directory.search('avago')[0]['name'], 'New provider name')
        empty = dict(payload(), rows=[])
        with self.assertRaises(ValueError): self.directory.ingest(empty)

    def test_quote_cleanup_preserves_directory_and_aliases_and_special_codes_are_reported(self):
        data = payload(); data['rows'].append(dict(code='US.XYZ*', name='Special',stock_type='STOCK',delisting=False))
        result = self.directory.ingest(data)
        self.assertEqual(result['skipped'][0]['code'], 'US.XYZ*')
        self.store.cleanup(1)
        self.assertEqual(self.directory.search('avago')[0]['code'],'US.AVGO')

    def test_v2_upgrade_preserves_snapshot_bytes_and_settings(self):
        from moopython.database import migrate
        from moopython import database
        import sqlite3
        path = Path(self.temp.name)/'old.sqlite3'
        db = sqlite3.connect(path)
        with db, patch.object(database,'SCHEMA_VERSION',2):
            db.execute('BEGIN IMMEDIATE'); migrate(db, lambda key: (None,'unknown'))
            db.execute("INSERT INTO settings VALUES ('retention_days','365')")
            db.execute("INSERT INTO snapshots VALUES (10,'key','2026-10-16','time','time','hash',X'0102','US.AVGO','test','batch')")
        before = db.execute('SELECT * FROM snapshots').fetchall(); db.close()
        with SnapshotStore(path).connect() as db:
            self.assertEqual(db.execute('SELECT * FROM snapshots').fetchall(), before)
            self.assertEqual(db.execute('SELECT value FROM settings').fetchone()[0], '365')
            from moopython.database import SCHEMA_VERSION
            self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0], SCHEMA_VERSION)

    def test_cli_search_is_offline(self):
        from moopython.database_cli import main
        with patch.dict('os.environ',{'MOOMOO_DB_PATH':str(self.store.path)}), \
                patch('socket.create_connection',side_effect=AssertionError('Search stays local')), \
                redirect_stdout(io.StringIO()) as stream:
            self.assertEqual(main(['search','avago']),0)
        self.assertEqual(json.loads(stream.getvalue())['candidates'][0]['code'],'US.AVGO')
