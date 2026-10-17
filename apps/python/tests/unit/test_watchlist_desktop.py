"""Persistent additions and whole-Watchlist ranking for the shared desktop worker."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager, redirect_stdout
import copy
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from test_watchlist import Service
from moopython.watchlist import load_watchlist
from moopython.watchlist_store import WatchlistStore, add_to_watchlist
from moopython.market_store import SnapshotStore
from moopython.watchlist_research import analyze_watchlist_dataset, run_watchlist_research


class WatchlistStorageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='watchlist test ')
        self.path = Path(self.temp.name)/'watchlist.json'
        self.path.write_text('{"symbols":["AAA"]}', encoding='utf-8')
        self.service = Service()
        self.watchlist = WatchlistStore(SnapshotStore(self.path.with_name('market.sqlite3')))

    def tearDown(self): self.temp.cleanup()

    def test_initial_seed_and_one_time_import_preserve_the_legacy_file(self):
        other = WatchlistStore(SnapshotStore(self.path.parent/'new'/'market.sqlite3'))
        self.assertIn('US.AVGO', other.symbols())
        self.assertFalse(other.store.path.with_name('watchlist.json').exists())
        before = self.path.read_bytes()
        self.assertEqual(self.watchlist.symbols(), ['US.AAA'])
        self.assertEqual(self.path.read_bytes(), before)
        self.path.write_text('{"symbols":["CHANGED"]}')
        self.assertEqual(self.watchlist.symbols(), ['US.AAA'])

    def test_valid_stock_is_added_and_duplicate_alias_is_idempotent_without_broker(self):
        result = add_to_watchlist(self.service, 'bbb', self.watchlist)
        self.assertTrue(result['added'])
        self.assertEqual(self.watchlist.symbols(), ['US.AAA', 'US.BBB'])
        before = self.path.read_bytes()
        with patch.object(self.service, 'basic_info', side_effect=AssertionError('Duplicate needs no new verification')):
            result = add_to_watchlist(self.service, 'US.BBB', self.watchlist)
        self.assertFalse(result['added'])
        self.assertEqual(self.path.read_bytes(), before)

    def test_invalid_or_unverified_stock_does_not_change_membership(self):
        before = self.watchlist.status()['items']
        self.service.info['US.BAD'] = dict(code='US.BAD', name='Unknown', stock_type='N/A', delisting=True)
        with self.assertRaises(ValueError): add_to_watchlist(self.service, 'BAD', self.watchlist)
        self.service.failures.add('basic_info')
        with self.assertRaises(ValueError): add_to_watchlist(self.service, 'BBB', self.watchlist)
        self.assertEqual(self.watchlist.status()['items'], before)

    def test_invalid_existing_json_is_not_overwritten(self):
        self.path.write_text('{bad json', encoding='utf-8')
        with self.assertRaises(ValueError): add_to_watchlist(self.service, 'BBB', self.watchlist)
        self.assertEqual(self.path.read_text(encoding='utf-8'), '{bad json')
        with self.watchlist.store.connect() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM watchlist').fetchone()[0],0)
            self.assertIsNone(db.execute("SELECT 1 FROM settings WHERE key='watchlist_initialized'").fetchone())

    def test_simultaneous_additions_keep_both_stocks_and_no_duplicates(self):
        with ThreadPoolExecutor(max_workers=3) as pool:
            list(pool.map(lambda code: add_to_watchlist(self.service, code, self.watchlist), ['BBB', 'CCC', 'BBB']))
        symbols = self.watchlist.symbols()
        self.assertEqual(set(symbols), {'US.AAA', 'US.BBB', 'US.CCC'})
        self.assertEqual(len(symbols), 3)

    def test_environment_selects_legacy_import_once(self):
        with patch.dict(os.environ, {'MOOMOO_WATCHLIST_PATH': str(self.path)}):
            self.assertEqual(self.watchlist.symbols(), ['US.AAA'])
        self.path.unlink()
        self.assertEqual(self.watchlist.symbols(), ['US.AAA'])

    def test_confirmed_removal_preserves_concurrent_additions_and_empty_list_stays_empty(self):
        original = self.watchlist.status()['items']
        add_to_watchlist(self.service,'BBB',self.watchlist)
        self.assertEqual(self.watchlist.remove_items([original[0]['id']])['symbols'],['US.BBB'])
        old_id = self.watchlist.status()['items'][0]['id']
        self.watchlist.remove_items([old_id])
        self.assertEqual(WatchlistStore(self.watchlist.store).symbols(), [])
        add_to_watchlist(self.service,'BBB',self.watchlist)
        self.assertEqual(self.watchlist.remove_items([old_id])['removed_count'],0)
        self.assertEqual(self.watchlist.symbols(),['US.BBB'])

    def test_import_is_validated_atomically_and_export_is_only_an_explicit_copy(self):
        self.watchlist.initialize()
        source = self.path.with_name('import.json')
        source.write_text('{"symbols":["BBB","CCC"]}')
        self.watchlist.import_json(self.service,source)
        self.assertEqual(self.watchlist.symbols(),['US.AAA','US.BBB','US.CCC'])
        source.write_text('{"symbols":["BBB","BAD"]}')
        self.service.info['US.BAD'] = dict(code='US.BAD',name='Unknown',stock_type='N/A',delisting=True)
        before = self.watchlist.status()['items']
        with self.assertRaises(ValueError): self.watchlist.import_json(self.service,source,replace=True)
        self.assertEqual(self.watchlist.status()['items'],before)
        target = self.path.with_name('export.json')
        self.watchlist.export_json(target)
        self.assertEqual(load_watchlist(target),self.watchlist.symbols())
        self.assertEqual(load_watchlist(self.path),['AAA'])
        self.watchlist.remove_items([row['id'] for row in self.watchlist.status()['items']])
        self.watchlist.export_json(target)
        self.watchlist.import_json(self.service,target,replace=True)
        self.assertEqual(self.watchlist.symbols(),[])

    def test_quote_retention_does_not_delete_watchlist(self):
        before = self.watchlist.status()['items']
        self.watchlist.store.cleanup(1)
        self.assertEqual(self.watchlist.status()['items'],before)


class ManyContracts(Service):
    def collect_put_dataset(self, symbols, months=3):
        result = super().collect_put_dataset(symbols, months)
        first = result['contracts'][0]
        result['contracts'] = []
        for index in range(25):
            strike = 90-index*.2
            bid = 2.5 if symbols == ['US.BBB'] else 1.5
            result['contracts'].append(dict(first, code=symbols[0]+f'-{index}', strike=strike,
                                            snapshot_strike=strike, bid=bid, ask=bid+.1))
        return result


class WatchlistRankingTests(unittest.TestCase):
    def test_whole_list_top_is_ranked_from_all_contracts_without_stock_quota(self):
        service = ManyContracts()
        result = run_watchlist_research(service, ['AAA', 'BBB'], 'put', top_n=5)
        self.assertEqual(result['query_scope'], 'watchlist')
        self.assertEqual(result['report']['total_contracts'], 50)
        self.assertEqual(result['report']['qualified_count'], 50)
        self.assertEqual({r['symbol'] for r in result['report']['recommendations']}, {'US.BBB'})
        configuration = dict(sort_order=[['strike', 'asc'], ['symbol', 'asc']])
        reranked = analyze_watchlist_dataset(result['input_dataset'], configuration, 20)
        self.assertEqual(len(reranked['report']['recommendations']), 20)
        self.assertEqual(reranked['report']['total_contracts'], 50)
        self.assertEqual(reranked['collected_at'], result['collected_at'])
        self.assertEqual(len([c for c in service.calls if c[0] == 'put']), 2)

    def test_offline_worker_reuses_merged_dataset_with_no_watchlist_file_or_network(self):
        result = run_watchlist_research(ManyContracts(), ['AAA', 'BBB'], 'put')
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp)/'input.json'; output = Path(temp)/'output.json'
            source.write_text(json.dumps(result['input_dataset']), encoding='utf-8')
            process = subprocess.run([sys.executable, '-m', 'moopython.research_cli', 'put',
                '--watchlist', str(Path(temp)/'not-read.json'), '--input', str(source), '--port', '1',
                '--top', '20', '--output', str(output)], capture_output=True)
            self.assertEqual(process.returncode, 0, process.stderr)
            saved = json.loads(output.read_text(encoding='utf-8'))
            self.assertEqual(len(saved['report']['recommendations']), 20)
            self.assertEqual(saved['input_dataset'], result['input_dataset'])

    def test_precheck_failure_is_clear_and_partial_data_does_not_hide_missing_stock(self):
        service = Service()
        service.info['US.BAD'] = dict(code='US.BAD', name='Unknown', stock_type='N/A', delisting=True)
        with self.assertRaisesRegex(ValueError, 'US.BAD'):
            run_watchlist_research(service, ['AAA', 'BAD'], 'put')
        self.assertFalse(any(c[0] == 'put' for c in service.calls))
        service.failures.add('US.AAA')
        result = run_watchlist_research(service, ['AAA', 'BBB'], 'put')
        self.assertEqual(result['collection_errors'][0]['symbol'], 'US.AAA')
        self.assertEqual(result['input_dataset']['requested_symbols'], ['US.AAA', 'US.BBB'])
        self.assertEqual(result['symbols'], ['US.BBB'])

    def test_trend_keeps_a_report_for_every_successful_stock(self):
        result = run_watchlist_research(Service(), ['AAA', 'BBB'], 'trend')
        self.assertEqual([r['symbol'] for r in result['items']], ['US.AAA', 'US.BBB'])
        self.assertTrue(all(r['trend']['status'] == 'ok' for r in result['items']))

    def test_add_worker_writes_json_stdout_and_validated_database_membership(self):
        from moopython.research_cli import main
        @contextmanager
        def connection(**parameters): yield Service()
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/'watchlist.json'
            path.write_text('{"symbols":["AAA"]}', encoding='utf-8')
            with patch.dict(os.environ,{'MOOMOO_DB_PATH':str(path.with_name('market.sqlite3'))}), \
                    patch('moopython.research_cli.market_data_connection', connection), redirect_stdout(io.StringIO()) as stream:
                self.assertEqual(main(['add', 'BBB', '--refresh']), 0)
            result = json.loads(stream.getvalue())
            self.assertEqual(result['action'], 'watchlist_add')
            self.assertTrue(result['added'])
            self.assertEqual(WatchlistStore(SnapshotStore(path.with_name('market.sqlite3'))).symbols(), ['US.AAA', 'US.BBB'])
            self.assertEqual(load_watchlist(path), ['AAA'])


if __name__ == '__main__': unittest.main()
