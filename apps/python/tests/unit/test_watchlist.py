"""Real-symbol gate, whole-list coverage and offline watchlist entrypoint."""
from contextlib import contextmanager, redirect_stdout
from datetime import datetime
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from moopython.market_repository import market_data_connection
from moopython.market_store import SnapshotStore
from moopython.watchlist import load_watchlist, normalize_stock, precheck, run_watchlist
from moopython.watchlist_cli import main

ROOT = Path(__file__).resolve().parents[4]
STAMP = '2026-10-16T22:00:00+00:00'


class Service:
    def __init__(self):
        self.calls, self.info, self.failures = [], {}, set()

    def basic_info(self, codes):
        self.calls.append(('basic_info', codes))
        if 'basic_info' in self.failures: raise RuntimeError('Permission denied, not evidence of an invalid code')
        rows = [self.info.get(code, dict(code=code, name=code+' company', stock_type='STOCK', delisting=False)) for code in codes]
        return dict(codes=codes, rows=[r for r in rows if r is not None], collected_at=STAMP, missing_codes=[])

    def dataset(self, code):
        source = (ROOT/'modules/put-screener/example.json').read_text()
        result = json.loads(source.replace('TEST', code.removeprefix('US.')))
        result.update(symbols=[code], fetched_at=STAMP, decision_cutoff=STAMP)
        return result

    def collect_put_dataset(self, symbols, months=3):
        self.calls.append(('put', symbols))
        if symbols[0] in self.failures: raise RuntimeError('No option permission for '+symbols[0])
        return self.dataset(symbols[0])

    def daily_bars(self, symbols, session_date=None, cutoff=None):
        self.calls.append(('trend', symbols))
        dataset = self.dataset(symbols[0])
        return dict(daily_series=dataset['daily_series'], decision_cutoff=STAMP, fetched_at=STAMP)


class WatchlistTests(unittest.TestCase):
    def setUp(self): self.service = Service()

    def run_list(self, values, **options):
        return run_watchlist(self.service, values, progress=lambda message: None, **options)

    def test_file_supports_object_array_and_utf8_bom(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/'股票列表.json'
            for value in ({'symbols': ['AVGO', 'NVDA']}, ['AVGO', 'NVDA']):
                path.write_text(json.dumps(value), encoding='utf-8-sig')
                self.assertEqual(load_watchlist(path), ['AVGO', 'NVDA'])
            for text in ('{}', '[]', '{"symbols":"AVGO"}', '{"symbols":[],"typo":1}',
                         '{"symbols":["AVGO"],"symbols":["NVDA"]}', '[NaN]'):
                path.write_text(text, encoding='utf-8')
                with self.subTest(text=text), self.assertRaises(ValueError): load_watchlist(path)

    def test_format_errors_are_reported_together_before_any_provider_call(self):
        result = self.run_list(['AAA', None, 42, '', 'HK.00700', 'US.AAA261218P90000', 'bad code'])
        self.assertEqual(result['status'], 'precheck_failed')
        self.assertEqual(result['summary']['invalid_count'], 6)
        self.assertFalse(self.service.calls)
        self.assertFalse(result['results'])

    def test_class_shares_case_whitespace_and_duplicate_aliases(self):
        self.assertEqual(normalize_stock(' brk.b '), 'US.BRK.B')
        result = self.run_list(['aaa', 'US.AAA', ' AAA ', 'BBB'])
        self.assertEqual(result['summary']['duplicate_count'], 2)
        self.assertEqual([r['symbol'] for r in result['results']], ['US.AAA', 'US.BBB'])
        self.assertEqual([call for call in self.service.calls if call[0] == 'put'],
                         [('put', ['US.AAA']), ('put', ['US.BBB'])])

    def test_authoritative_invalid_or_delisted_or_wrong_type_blocks_all_analysis(self):
        for override in (dict(name='Unknown stock.', stock_type='N/A', delisting=True),
                         dict(name='Delisted', stock_type='STOCK', delisting=True),
                         dict(name='Index', stock_type='IDX', delisting=False)):
            self.service = Service()
            self.service.info['US.BAD'] = dict(code='US.BAD', **override)
            result = self.run_list(['AAA', 'BAD', 'BBB'])
            self.assertEqual(result['summary']['invalid_count'], 1)
            self.assertEqual(result['precheck']['valid_symbols'], ['US.AAA', 'US.BBB'])
            self.assertEqual(result['status'], 'precheck_failed')
            self.assertEqual([c[0] for c in self.service.calls], ['basic_info'])

    def test_missing_records_and_permission_errors_are_unverified_not_invalid(self):
        self.service.info['US.UNKNOWN'] = None
        result = self.run_list(['AAA', 'UNKNOWN'])
        self.assertEqual(result['summary']['invalid_count'], 0)
        self.assertEqual(result['summary']['unverified_count'], 1)
        self.service.failures.add('basic_info')
        result = self.run_list(['AAA', 'BBB'])
        self.assertEqual(result['summary']['unverified_count'], 2)
        self.assertEqual(result['summary']['invalid_count'], 0)
        self.assertFalse(result['results'])

    def test_incomplete_or_conflicting_metadata_cannot_pass(self):
        self.service.info['US.AAA'] = dict(code='US.AAA', name='AAA', stock_type='STOCK')
        self.assertFalse(precheck(self.service, ['AAA'])['passed'])
        self.service.info['US.AAA'] = dict(code='US.WRONG', name='AAA', stock_type='STOCK', delisting=False)
        result = precheck(self.service, ['AAA'])
        self.assertFalse(result['passed'])
        self.assertEqual(len(result['unverified']), 1)

    def test_etf_and_stock_without_any_price_can_pass(self):
        self.service.info['US.FUND'] = dict(code='US.FUND', name='ETF', stock_type='ETF', delisting=False)
        self.assertTrue(precheck(self.service, ['AAA', 'FUND'])['passed'])

    def test_large_list_is_prechecked_in_batches_and_every_stock_is_analyzed(self):
        values = [f'TICKER{i}' for i in range(205)]
        with patch('moopython.watchlist.run_research', return_value={'trend': {}}) as research:
            result = self.run_list(values, action='trend')
        self.assertEqual([len(c[1]) for c in self.service.calls], [200, 5])
        self.assertEqual(research.call_count, 205)
        self.assertEqual(result['summary']['analyzed_count'], 205)

    def test_both_analyzes_all_stocks_reuses_daily_input_and_keeps_top_per_stock(self):
        result = self.run_list(['AAA', 'BBB'], top_n=5)
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(result['ranking_scope'], 'per_symbol')
        self.assertEqual([c[0] for c in self.service.calls], ['basic_info', 'put', 'put'])
        for item in result['results']:
            self.assertEqual(item['put']['report']['top_n_requested'], 5)
            self.assertEqual(len(item['put']['report']['recommendations']), 1)
            self.assertEqual(item['trend']['trend']['status'], 'ok')

    def test_analysis_failure_is_recorded_and_remaining_stocks_continue(self):
        self.service.failures.add('US.AAA')
        result = self.run_list(['AAA', 'BBB'])
        self.assertEqual(result['status'], 'partial_failure')
        first, second = result['results']
        self.assertEqual(first['status'], 'partial')
        self.assertIn('No option permission', first['put']['error'])
        self.assertEqual(first['trend']['trend']['status'], 'ok')
        self.assertEqual(second['status'], 'ok')
        self.assertEqual(result['summary']['failed_count'], 1)

    def test_check_only_and_trend_only_do_not_collect_options(self):
        result = self.run_list(['AAA', 'BBB'], check_only=True)
        self.assertEqual(result['status'], 'precheck_passed')
        self.assertFalse(result['results'])
        self.assertEqual([c[0] for c in self.service.calls], ['basic_info'])
        self.service.calls.clear()
        result = self.run_list(['AAA', 'BBB'], action='trend')
        self.assertEqual(result['status'], 'completed')
        self.assertEqual([c[0] for c in self.service.calls], ['basic_info', 'trend', 'trend'])

    def test_invalid_strategy_configuration_precedes_any_provider_call(self):
        with self.assertRaises(ValueError):
            self.run_list(['AAA'], configuration=dict(sort_order=[['nonexistent', 'asc']]))
        self.assertFalse(self.service.calls)


class WatchlistCliTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name)
        self.list_file = self.path/'股票 list.json'
        self.list_file.write_text(json.dumps({'symbols': ['AAA', 'BBB']}), encoding='utf-8')
        self.store = SnapshotStore(self.path/'market.sqlite3')
        self.provider = Service()
        @contextmanager
        def live(**options):
            yield self.provider
        self.live = live
        self.closed = lambda: datetime.fromisoformat('2026-10-17T15:00:00+00:00')

    def tearDown(self): self.temp.cleanup()

    def cached(self, **options):
        return market_data_connection(store=self.store, clock=self.closed, connection=self.live, **options)

    def test_end_to_end_refresh_then_offline_precheck_and_analysis(self):
        output = self.path/'nested folder'/'results.json'
        with patch('moopython.watchlist_cli.market_data_connection', self.cached):
            self.assertEqual(main([str(self.list_file), '--refresh', '--output', str(output)]), 0)
            calls = len(self.provider.calls)
            with patch('socket.create_connection', side_effect=AssertionError('After-hours must stay offline')):
                self.assertEqual(main([str(self.list_file), '--top', '20', '--rank-by', 'risk', '--output', str(output)]), 0)
        self.assertEqual(len(self.provider.calls), calls)
        result = json.loads(output.read_text(encoding='utf-8'))
        self.assertEqual(result['summary']['analyzed_count'], 2)
        for row in result['precheck']['entries']:
            self.assertEqual(row['data_access']['source'], 'database')
        for item in result['results']:
            self.assertEqual(item['put']['data_access']['source'], 'database')
            self.assertEqual(item['put']['report']['top_n_requested'], 20)
            self.assertEqual(item['put']['report']['sort_order'][0], ['risk_score', 'asc'])

    def test_empty_after_hours_cache_automatically_verifies_new_symbols(self):
        with patch('moopython.watchlist_cli.market_data_connection', self.cached), redirect_stdout(io.StringIO()) as stream:
            self.assertEqual(main([str(self.list_file), '--check-only']), 0)
        result = json.loads(stream.getvalue())
        self.assertEqual(result['summary']['unverified_count'], 0)
        self.assertEqual(result['summary']['invalid_count'], 0)
        self.assertTrue(self.provider.calls)

    def test_file_errors_precede_connection_and_json_stdout_has_no_logs(self):
        self.list_file.write_text('{bad json', encoding='utf-8')
        with patch('moopython.watchlist_cli.market_data_connection', side_effect=AssertionError('No connection')), redirect_stdout(io.StringIO()) as stream:
            self.assertEqual(main([str(self.list_file)]), 1)
        self.assertIn('error', json.loads(stream.getvalue()))

    def test_static_batch_cache_is_reusable_for_a_single_stock(self):
        with self.cached(refresh=True) as service: service.basic_info(['AAA', 'BBB'])
        with self.cached() as service:
            check = precheck(service, ['BBB'])
        self.assertTrue(check['passed'])
        self.assertEqual(len(self.provider.calls), 1)

    def test_uncached_member_does_not_hide_existing_verification_evidence(self):
        with self.cached(refresh=True) as service: service.basic_info(['AAA'])
        with self.cached() as service: check = precheck(service, ['AAA', 'BBB'])
        self.assertTrue(check['passed'])
        self.assertEqual(check['valid_symbols'], ['US.AAA','US.BBB'])
        self.assertEqual(check['unverified'], [])
        self.assertEqual(len(self.provider.calls), 2)


if __name__ == '__main__': unittest.main()
