"""Verify the distributable works outside the checkout, with its frozen rule snapshot."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
wheel = Path(sys.argv[1]).resolve()
with tempfile.TemporaryDirectory(prefix='moomoo wheel ') as directory:
    target = Path(directory)
    with zipfile.ZipFile(wheel) as archive:
        assert 'moopython/data/watchlist.json' not in archive.namelist(), 'Removed JSON seed must not survive in build cache'
        archive.extractall(target)
    assert (target/'moopython/_bundled_put_rules.py').read_bytes() == (ROOT/'modules/put-screener/put_rules.py').read_bytes()
    program = '''
from moopython.research import load_rules
from moopython.market_repository import market_data_connection
from moopython.market_store import SnapshotStore
from moopython.database import ROOT as DATABASE_ROOT, schema_sql
from moopython.watchlist_cli import main as watchlist_main
from moopython.watchlist_store import WatchlistStore
from moopython.watchlist_research import analyze_watchlist_dataset
from moopython.security_directory import SecurityDirectory
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
import json
import os
r = load_rules()
assert (DATABASE_ROOT/'schema.sql').read_text(encoding='utf-8') == schema_sql()
assert Path(r.__file__).name == '_bundled_put_rules.py'
watchlist = WatchlistStore(SnapshotStore(Path('user data')/'market.sqlite3'))
assert 'US.AVGO' in watchlist.symbols()
assert not Path('user data/watchlist.json').exists()
with patch('socket.create_connection', side_effect=AssertionError('Cache query must stay offline')):
    directory = SecurityDirectory(SnapshotStore('wheel-check.sqlite3'))
    directory.ingest(dict(source='synthetic wheel check', collected_at='2026-10-17T15:00:00+00:00',
        rows=[dict(code='US.AVGO',name='Broadcom',stock_type='STOCK',delisting=False)]))
    assert directory.search('avago')[0]['code'] == 'US.AVGO'
    assert directory.search('*roadcom*')[0]['code'] == 'US.AVGO'
    with market_data_connection(store=SnapshotStore('wheel-check.sqlite3'),
            clock=lambda: datetime.fromisoformat('2026-10-17T15:00:00+00:00')) as service:
        try:
            service.collect_put_dataset(['TEST'])
        except RuntimeError as error:
            assert 'refresh' in str(error), str(error)
        else:
            raise AssertionError('Missing cache must not generate a dataset')
    os.environ['MOOMOO_DB_PATH'] = str(Path('wheel-check.sqlite3').resolve())
    Path('watchlist.json').write_text('{"symbols":["TEST"]}', encoding='utf-8')
    assert watchlist_main(['watchlist.json', '--check-only', '--output', 'watchlist-result.json']) == 2
    assert json.loads(Path('watchlist-result.json').read_text(encoding='utf-8'))['status'] == 'precheck_failed'
print(r.ENGINE_VERSION, 'standalone SQLite router passed')
'''
    subprocess.run([sys.executable, '-c', program], cwd=target, env=dict(os.environ, PYTHONPATH=directory), check=True)
    subprocess.run([sys.executable, '-m', 'moopython.database_cli', 'status'], cwd=target,
                   env=dict(os.environ, PYTHONPATH=directory, MOOMOO_DB_PATH=str(target/'wheel-check.sqlite3')), check=True)
