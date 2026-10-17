"""Storage/routing contracts using synthetic data; never require a broker login."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import datetime
import io
import json
import os
from pathlib import Path
import sqlite3
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from moopython.market_repository import market_data_connection
from moopython.market_sessions import market_session
from moopython.market_store import SnapshotStore, database_path


def moment(value):
    return datetime.fromisoformat(value)


class SessionTests(unittest.TestCase):
    def state(self, value, kind='options', symbol='US.TEST'):
        return market_session(moment(value), kind, [symbol])

    def test_regular_close_and_weekend(self):
        self.assertTrue(self.state('2026-10-16T13:30:00+00:00')['is_open'])
        self.assertTrue(self.state('2026-10-16T20:14:00+00:00')['is_open'])
        self.assertFalse(self.state('2026-10-16T20:15:00+00:00')['is_open'])
        state = self.state('2026-10-17T18:00:00+00:00')
        self.assertFalse(state['is_open'])
        self.assertEqual(state['session_date'], '2026-10-16')

    def test_dst_holiday_and_early_close(self):
        self.assertTrue(self.state('2026-03-06T14:30:00+00:00')['is_open'])
        self.assertFalse(self.state('2026-03-06T13:30:00+00:00')['is_open'])
        self.assertTrue(self.state('2026-03-09T13:30:00+00:00')['is_open'])
        self.assertFalse(self.state('2026-11-26T16:00:00+00:00')['is_open'])
        self.assertTrue(self.state('2026-11-27T18:14:00+00:00')['is_open'])
        self.assertFalse(self.state('2026-11-27T18:15:00+00:00')['is_open'])
        self.assertEqual(self.state('2026-11-26T16:00:00+00:00')['session_date'], '2026-11-25')

    def test_extended_options_have_effective_date_eligibility_and_break(self):
        self.assertFalse(self.state('2026-10-16T11:35:00+00:00', symbol='US.AVGO')['is_open'])
        self.assertTrue(self.state('2026-10-19T11:35:00+00:00', symbol='US.AVGO')['is_open'])
        self.assertFalse(self.state('2026-10-19T11:35:00+00:00')['is_open'])
        self.assertFalse(self.state('2026-10-19T13:27:00+00:00', symbol='US.AVGO')['is_open'])
        self.assertTrue(self.state('2026-10-19T13:30:00+00:00', symbol='US.AVGO')['is_open'])

    def test_stock_overnight_is_separate_and_daily_has_completion_delay(self):
        self.assertTrue(self.state('2026-10-16T21:00:00+00:00', 'stocks')['is_open'])
        self.assertFalse(self.state('2026-10-16T21:00:00+00:00')['is_open'])
        self.assertTrue(self.state('2026-10-19T00:30:00+00:00', 'stocks')['is_open'])
        self.assertTrue(self.state('2026-10-16T20:04:00+00:00', 'daily')['is_open'])
        self.assertFalse(self.state('2026-10-16T20:05:00+00:00', 'daily')['is_open'])
        self.assertTrue(self.state('2026-09-08T00:30:00+00:00', 'stocks')['is_open'])

    def test_new_year_on_saturday_does_not_close_previous_friday(self):
        self.assertTrue(self.state('2027-12-31T16:00:00+00:00')['is_open'])

    def test_unknown_calendar_and_naive_clock_fail_explicitly(self):
        for value in ('2029-10-16T16:00:00+00:00', '2026-10-16T16:00:00'):
            with self.assertRaises(ValueError): self.state(value)


class RepositoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / 'market.sqlite3'
        self.store = SnapshotStore(self.path)
        self.now = moment('2026-10-16T18:00:00+00:00')
        self.calls, self.opened, self.closed = [], [], []

        def fetch(operation, **parameters):
            self.calls.append((operation, parameters))
            if operation=='basic_info':
                return dict(collected_at=self.now.isoformat(),codes=parameters['codes'],missing_codes=[],
                    rows=[dict(code=c,name=c,stock_type='STOCK',delisting=False) for c in parameters['codes']])
            return dict(collected_at=self.now.isoformat(), fetched_at=self.now.isoformat(),
                        operation=operation, parameters=parameters, rows=[dict(bid=1.23, unknown=None)],
                        daily_series=[dict(as_of='2026-10-16')], missing_codes=['US.TEST2'])

        @contextmanager
        def connection(**parameters):
            self.opened.append(parameters)
            try:
                yield SimpleNamespace(**{op: (lambda _op=op, **kw: fetch(_op, **kw))
                    for op in ('snapshots', 'daily_bars', 'option_chain', 'earnings_calendar', 'collect_put_dataset', 'basic_info')})
            finally:
                self.closed.append(True)
        self.connection = connection

    def tearDown(self):
        self.temp.cleanup()

    def service(self, **parameters):
        return market_data_connection(store=self.store, clock=lambda: self.now,
                                      connection=self.connection, **parameters)

    def test_live_persists_closed_reads_and_restart_preserves_raw_fields(self):
        with self.service() as service:
            live = service.collect_put_dataset(['test'])
        self.assertEqual(len(self.opened), 1)
        self.assertEqual(self.closed, [True])
        self.now = moment('2026-10-17T12:00:00+00:00')
        self.store = SnapshotStore(self.path)  # independent instance / process restart
        with self.service() as service:
            saved = service.collect_put_dataset(['US.TEST'])
        self.assertEqual(len(self.opened), 1)
        self.assertEqual(saved['data_access']['source'], 'database')
        self.assertTrue(saved['data_access']['captured_during_session'])
        self.assertIn('不代表收盘', saved['data_access']['note'])
        self.assertEqual({k: v for k, v in live.items() if k != 'data_access'},
                         {k: v for k, v in saved.items() if k != 'data_access'})
        self.assertEqual(saved['collected_at'], '2026-10-16T18:00:00+00:00')

    def test_after_hours_first_query_fetches_saves_and_second_query_stays_offline(self):
        self.now = moment('2026-10-17T12:00:00+00:00')
        with self.service() as service:
            result = service.collect_put_dataset(['TEST'])
        self.assertEqual(result['data_access']['source'], 'OpenD')
        self.assertTrue(result['data_access']['cache_miss_fetch'])
        self.assertFalse(result['data_access']['explicit_refresh'])
        with self.service() as service:
            self.assertEqual(service.collect_put_dataset(['TEST'])['data_access']['source'], 'database')
        self.assertEqual(len(self.opened), 1)

    def test_after_hours_failed_first_fetch_is_an_error_and_preserves_cached_stock(self):
        with self.service() as service: service.collect_put_dataset(['TEST'])
        self.now = moment('2026-10-17T12:00:00+00:00')
        @contextmanager
        def unavailable(**kwargs):
            raise RuntimeError('OpenD unavailable for US.CBRS')
            yield
        with market_data_connection(store=self.store,clock=lambda:self.now,connection=unavailable) as service:
            with self.assertRaisesRegex(RuntimeError,'CBRS'):
                service.collect_put_dataset(['CBRS'])
            self.assertEqual(service.collect_put_dataset(['TEST'])['data_access']['source'],'database')
        self.assertEqual(self.store.status()['snapshots'],1)

    def test_all_read_operations_share_router_and_cache(self):
        for operation, kwargs in [
            ('snapshots', dict(codes=['US.TEST261218P90000'])),
            ('option_chain', dict(symbol='TEST', months=3)),
            ('daily_bars', dict(symbols=['TEST'])),
            ('earnings_calendar', dict(start='2026-10-19', end='2026-10-25')),
        ]:
            with self.subTest(operation=operation):
                self.now = moment('2026-10-16T18:00:00+00:00')
                with self.service() as service: getattr(service, operation)(**kwargs)
                before = len(self.opened)
                self.now = moment('2026-10-17T12:00:00+00:00')
                with self.service() as service:
                    result = getattr(service, operation)(**kwargs)
                self.assertEqual(result['data_access']['source'], 'database')
                self.assertEqual(len(self.opened), before)

    def test_different_symbol_months_port_and_next_day_cannot_hit_wrong_data(self):
        with self.service() as service: service.collect_put_dataset(['TEST'])
        self.now = moment('2026-10-17T12:00:00+00:00')
        for kwargs in (dict(symbols=['OTHER']), dict(symbols=['TEST'], months=1)):
            with self.service() as service:
                self.assertEqual(service.collect_put_dataset(**kwargs)['data_access']['source'],'OpenD')
        with self.service(port=12345) as service:
            self.assertEqual(service.collect_put_dataset(['TEST'])['data_access']['source'],'OpenD')
        self.now = moment('2026-10-19T22:00:00+00:00')
        with self.service() as service:
            result=service.collect_put_dataset(['TEST'])
        self.assertEqual(result['data_access']['market']['session_date'],'2026-10-19')
        self.assertEqual(result['data_access']['source'],'OpenD')
        self.assertEqual(len(self.opened), 5)

    def test_closed_trend_rejects_snapshot_missing_latest_completed_day(self):
        with self.service() as service:
            result = service.daily_bars(['TEST'])
        with self.store.connect() as db:
            key = db.execute('SELECT request_key FROM snapshots').fetchone()[0]
        result['daily_series'][0]['as_of'] = '2026-10-15'
        self.store.save(key, '2026-10-16', '2026-10-16T19:00:00+00:00', result)
        self.now = moment('2026-10-17T12:00:00+00:00')
        with self.service() as service, self.assertRaisesRegex(RuntimeError, '日线'):
            service.daily_bars(['TEST'])
        self.assertEqual(len(self.opened), 1)

    def test_invalid_request_before_database_or_network_access(self):
        with self.service() as service:
            for operation, kwargs in [('collect_put_dataset', dict(symbols=['TEST'], months=0)),
                ('snapshots', dict(codes=[])), ('option_chain', dict(symbol='TEST', option_type='WRONG')),
                ('daily_bars', dict(symbols=['TEST'], cutoff='2026-10-16T14:00:00')),
                ('earnings_calendar', dict(start='2026-10-01', end='2026-10-09'))]:
                with self.subTest(operation=operation), self.assertRaises(ValueError):
                    getattr(service, operation)(**kwargs)
        self.assertFalse(self.opened)
        self.assertFalse(self.path.exists())

    def test_mcp_cache_path_neither_connects_nor_waits_for_rate_limit(self):
        from moopython.market_mcp import OpenDReader
        reader = OpenDReader(store=self.store, clock=lambda: self.now, connection=self.connection)
        reader('snapshots', codes=['US.TEST261218P90000'])
        self.now = moment('2026-10-17T12:00:00+00:00')
        with patch('moopython.market_mcp.time.sleep', side_effect=AssertionError('database must not wait')):
            result = reader('snapshots', codes=['US.TEST261218P90000'])
        self.assertEqual(result['data_access']['source'], 'database')
        self.assertEqual(len(self.opened), 1)

    def test_database_path_override(self):
        with patch.dict(os.environ, {'MOOMOO_DB_PATH': str(self.path)}):
            self.assertEqual(database_path(), self.path)

    def test_incremental_closed_update_fetches_only_missing_stock_but_force_fetches_again(self):
        self.now=moment('2026-10-17T12:00:00+00:00')
        with self.service(update=True) as service: service.collect_put_dataset(['TEST'])
        first_id=self.store.status()['snapshots']
        self.now=moment('2026-10-17T13:00:00+00:00')
        with self.service(update=True) as service:
            cached=service.collect_put_dataset(['TEST'])
            fresh=service.collect_put_dataset(['NEW'])
        self.assertEqual(cached['data_access']['source'],'database')
        self.assertEqual(cached['collected_at'],'2026-10-17T12:00:00+00:00')
        self.assertEqual(fresh['data_access']['source'],'OpenD')
        self.assertEqual([call[1]['symbols'] for call in self.calls],[['US.TEST'],['US.NEW']])
        with self.service(refresh=True) as service: service.collect_put_dataset(['TEST'])
        self.assertEqual(len(self.calls),3)

    def test_incremental_intraday_expiry_close_boundary_and_new_trading_day(self):
        with self.service(update=True) as service: service.collect_put_dataset(['TEST'])
        self.now=moment('2026-10-16T18:00:59+00:00')
        with self.service(update=True) as service:
            self.assertEqual(service.collect_put_dataset(['TEST'])['data_access']['source'],'database')
        self.now=moment('2026-10-16T18:01:00+00:00')
        with self.service(update=True) as service:
            self.assertEqual(service.collect_put_dataset(['TEST'])['data_access']['source'],'OpenD')
        self.now=moment('2026-10-17T12:00:00+00:00')
        with self.service(update=True) as service:
            self.assertEqual(service.collect_put_dataset(['TEST'])['data_access']['source'],'OpenD')
        with self.service(update=True) as service:
            self.assertEqual(service.collect_put_dataset(['TEST'])['data_access']['source'],'database')
        self.now=moment('2026-10-19T18:00:00+00:00')
        with self.service(update=True) as service:
            self.assertEqual(service.collect_put_dataset(['TEST'])['data_access']['source'],'OpenD')
        self.assertEqual(len(self.calls),4)

    def test_incremental_basic_info_checks_members_and_fetches_only_new_identity(self):
        self.now=moment('2026-10-17T12:00:00+00:00')
        with self.service(refresh=True) as service: service.basic_info(['TEST','OTHER'])
        with self.service(update=True) as service: result=service.basic_info(['TEST','NEW'])
        self.assertEqual([row['code'] for row in result['rows']],['US.TEST','US.NEW'])
        self.assertEqual(result['data_access']['source'],'mixed')
        self.assertEqual(self.calls[1],('basic_info',dict(codes=['US.NEW'])))
        self.assertEqual(len(self.calls),2)

    def test_incremental_daily_can_reuse_previous_completed_session_during_next_session(self):
        self.now=moment('2026-10-16T22:00:00+00:00')
        with self.service(refresh=True) as service: service.daily_bars(['TEST'])
        self.now=moment('2026-10-19T15:00:00+00:00')
        with self.service(update=True) as service:
            result=service.daily_bars(['TEST'])
        self.assertEqual(result['data_access']['source'],'database')
        self.assertEqual(result['daily_series'][0]['as_of'],'2026-10-16')
        self.assertEqual(len(self.calls),1)

    def test_incremental_mode_and_age_are_validated_before_database_access(self):
        for options in (dict(refresh=True,update=True),dict(update=True,max_age_seconds=0),dict(update=True,max_age_seconds=True)):
            with self.assertRaises(ValueError):
                with self.service(**options): pass
        self.assertFalse(self.path.exists())

    def test_real_chain_timestamp_field_is_supported(self):
        @contextmanager
        def connection(**kwargs):
            yield SimpleNamespace(option_chain=lambda **parameters:
                dict(queried_at=self.now.isoformat(), contracts=[]))
        with market_data_connection(store=self.store, clock=lambda: self.now, connection=connection) as service:
            result = service.option_chain('TEST')
        self.assertEqual(result['data_access']['source'], 'OpenD')

    def test_research_and_collect_entrypoints_read_database_without_provider(self):
        from moopython import research_cli, market_data_cli
        root = Path(__file__).resolve().parents[4]
        dataset = json.loads((root / 'modules/put-screener/example.json').read_text())
        dataset.update(fetched_at=dataset['collected_at'], decision_cutoff=dataset['collected_at'])
        @contextmanager
        def seed(**kwargs):
            yield SimpleNamespace(collect_put_dataset=lambda **parameters: dataset)
        self.now = moment('2026-10-17T12:00:00+00:00')
        with market_data_connection(store=self.store, clock=lambda: self.now, connection=seed, refresh=True) as service:
            service.collect_put_dataset(['TEST'])

        @contextmanager
        def forbidden(**kwargs):
            raise AssertionError('After-hours CLI must not connect to OpenD')
            yield
        def cached(**options):
            return market_data_connection(store=self.store, clock=lambda: self.now,
                                           connection=forbidden, **options)
        for action in ('put', 'trend'):
            output = Path(self.temp.name) / f'{action}.json'
            with patch.object(research_cli, 'market_data_connection', cached):
                self.assertEqual(research_cli.main([action, 'TEST', '--output', str(output)]), 0)
            result = json.loads(output.read_text(encoding='utf-8'))
            self.assertEqual(result['data_access']['source'], 'database')
            self.assertEqual(result['collected_at'], dataset['collected_at'])
            if action == 'put':
                self.assertEqual(len(result['report']['recommendations']), 1)
            else:
                self.assertEqual(result['trend']['status'], 'ok')
        output = Path(self.temp.name) / 'collect.json'
        with patch.object(market_data_cli, 'market_data_connection', cached), patch('sys.stdout', new_callable=io.StringIO):
            market_data_cli.main(['TEST', '--output', str(output)])
        self.assertEqual(json.loads(output.read_text(encoding='utf-8'))['data_access']['source'], 'database')

    def test_history_is_lossless_and_latest_is_by_collection_time(self):
        original = dict(source='synthetic', prices=[1.23, None], note='原始数据')
        self.store.save('key', '2026-10-16', '2026-10-16T20:00:00+00:00', original)
        self.store.save('key', '2026-10-16', '2026-10-16T18:00:00+00:00', {'older': True})
        self.assertEqual(self.store.latest('key', '2026-10-16')['payload'], original)
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM snapshots').fetchone()[0], 2)
            self.assertIsInstance(db.execute('SELECT payload FROM snapshots LIMIT 1').fetchone()[0], bytes)

    def test_concurrent_writers_and_unknown_schema_and_corruption(self):
        self.store.latest('key', '2026-10-16')  # initialize once
        def save(index):
            self.store.save('key', '2026-10-16', f'2026-10-16T18:00:{index:02d}+00:00', {'index': index})
        with ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(save, range(10)))
        self.assertEqual(self.store.latest('key', '2026-10-16')['payload']['index'], 9)
        with self.store.connect() as db:
            db.execute("UPDATE snapshots SET payload=x'00'")
        with self.assertRaisesRegex(RuntimeError, 'damaged'):
            self.store.latest('key', '2026-10-16')
        db = sqlite3.connect(self.path)
        try:
            with db: db.execute('PRAGMA user_version=99')
        finally:
            db.close()
        with self.assertRaisesRegex(RuntimeError, 'schema'):
            self.store.latest('key', '2026-10-16')


class MultiStockTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = SnapshotStore(Path(self.temp.name)/'market.sqlite3')
        self.now = moment('2026-10-16T18:00:00+00:00')
        self.calls = []
        self.bids = {'US.AAA': 1.1, 'US.BBB': 2.2}
        self.base = json.loads((Path(__file__).resolve().parents[4]/'modules/put-screener/example.json').read_text())

        def fetch(operation, **parameters):
            self.calls.append((operation, parameters))
            names = parameters.get('symbols', parameters.get('codes'))
            if 'US.MISSING' in names: raise RuntimeError('US.MISSING: provider data unavailable')
            if operation == 'snapshots':
                return dict(codes=names, collected_at=self.now.isoformat(),
                            rows=[dict(code=code, bid_price=index+1) for index, code in enumerate(names)], missing_codes=[])
            datasets = [json.loads(json.dumps(self.base).replace('TEST', name.removeprefix('US.'))) for name in names]
            result = dict(datasets[0], symbols=names, collected_at=self.now.isoformat(),
                          fetched_at=self.now.isoformat(), decision_cutoff=self.now.isoformat(),
                          contracts=[c for dataset in datasets for c in dataset['contracts']],
                          daily_series=[s for dataset in datasets for s in dataset['daily_series']],
                          coverage=[dict(symbol=name, months=parameters.get('months', 3)) for name in names],
                          missing_quote_codes=[name+'261218P95000' for name in names], calendar_errors=[])
            for contract in result['contracts']: contract['bid'] = self.bids[contract['symbol']]
            return result

        @contextmanager
        def connection(**kwargs):
            yield SimpleNamespace(**{op: (lambda _op=op, **kw: fetch(_op, **kw))
                                     for op in ('collect_put_dataset', 'daily_bars', 'snapshots')})
        self.connection = connection

    def tearDown(self): self.temp.cleanup()

    def service(self):
        return market_data_connection(store=self.store, clock=lambda: self.now, connection=self.connection)

    def closed(self): self.now = moment('2026-10-17T12:00:00+00:00')

    def test_one_batch_fetch_populates_individual_stocks_and_shared_batch_ids(self):
        with self.service() as service: live = service.collect_put_dataset(['AAA', 'BBB'])
        self.assertEqual(len(self.calls), 1)
        with self.store.connect() as db:
            members = db.execute("SELECT symbol, batch_id FROM snapshots WHERE operation='collect_put_dataset' AND symbol IS NOT NULL ORDER BY symbol").fetchall()
        self.assertEqual([r[0] for r in members], ['US.AAA', 'US.BBB'])
        self.assertTrue(all(row[1] == live['data_access']['batch_id'] for row in members))
        self.closed()
        with self.service() as service:
            for symbol in ('US.AAA', 'US.BBB'):
                saved = service.collect_put_dataset([symbol])
                self.assertEqual(saved['symbols'], [symbol])
                self.assertEqual({row['symbol'] for row in saved['contracts']}, {symbol})
                self.assertEqual(saved['missing_quote_codes'], [symbol+'261218P95000'])
                daily = service.daily_bars([symbol])
                self.assertEqual({row['symbol'] for row in daily['daily_series']}, {symbol})
        self.assertEqual(len(self.calls), 1)

    def test_independent_stock_snapshots_can_form_list_in_requested_order(self):
        with self.service() as service: service.collect_put_dataset(['AAA'])
        self.now = moment('2026-10-16T19:00:00+00:00')
        with self.service() as service: service.collect_put_dataset(['BBB'])
        self.closed()
        with self.service() as service: result = service.collect_put_dataset(['BBB', 'AAA'])
        self.assertEqual(result['symbols'], ['US.BBB', 'US.AAA'])
        self.assertEqual([c['symbol'] for c in result['contracts']], ['US.BBB', 'US.AAA'])
        self.assertEqual(result['collected_at'], '2026-10-16T19:00:00+00:00')
        self.assertEqual([m['subject'] for m in result['data_access']['members']], ['US.BBB', 'US.AAA'])
        self.assertNotEqual(*[m['fetched_at'] for m in result['data_access']['members']])
        self.assertIn('不代表同时报价', result['data_access']['note'])
        self.assertEqual(len(self.calls), 2)

    def test_single_stock_refresh_supersedes_older_saved_batch(self):
        with self.service() as service: service.collect_put_dataset(['AAA', 'BBB'])
        self.now = moment('2026-10-16T19:00:00+00:00')
        self.bids['US.AAA'] = 3.3
        with self.service() as service: service.collect_put_dataset(['AAA'])
        self.closed()
        with self.service() as service: result = service.collect_put_dataset(['AAA', 'BBB'])
        self.assertEqual([c['bid'] for c in result['contracts']], [3.3, 2.2])
        self.assertEqual(len(self.calls), 2)

    def test_missing_member_is_named_without_discarding_other_stocks(self):
        with self.service() as service: service.collect_put_dataset(['AAA'])
        self.closed()
        with self.service() as service:
            with self.assertRaisesRegex(RuntimeError, 'US.MISSING'):
                service.collect_put_dataset(['AAA', 'MISSING'])
            saved = service.collect_put_dataset(['AAA'])
            self.assertEqual(saved['symbols'], ['US.AAA'])
        self.assertEqual(len(self.calls), 2)

    def test_closed_batch_automatically_fetches_only_the_uncached_stock(self):
        with self.service() as service: service.collect_put_dataset(['AAA'])
        self.closed()
        with self.service() as service: result=service.collect_put_dataset(['AAA','BBB'])
        self.assertEqual(result['data_access']['source'],'mixed')
        self.assertEqual([m['source'] for m in result['data_access']['members']],['database','OpenD'])
        self.assertEqual(self.calls[1],('collect_put_dataset',dict(symbols=['US.BBB'],months=3)))
        self.assertEqual(len(self.calls),2)
        with self.service() as service: cached=service.collect_put_dataset(['BBB','AAA'])
        self.assertEqual(cached['data_access']['source'],'database')
        self.assertEqual(len(self.calls),2)

    def test_entirely_uncached_after_hours_batch_is_collected_in_one_request(self):
        self.closed()
        with self.service() as service: result=service.collect_put_dataset(['AAA','BBB'])
        self.assertEqual(result['data_access']['source'],'OpenD')
        self.assertTrue(result['data_access']['cache_miss_fetch'])
        self.assertEqual(self.calls,[('collect_put_dataset',dict(symbols=['US.AAA','US.BBB'],months=3))])

    def test_adjusted_missing_contract_root_is_preserved_without_guessing_owner(self):
        from moopython.market_payloads import project
        payload = dict(symbols=['US.AAA', 'US.BBB'], missing_quote_codes=[
            'US.AAA261218P90000', 'US.BBB261218P90000', 'US.AAA1261218P90000'])
        single = project(payload, 'collect_put_dataset', 'US.AAA')
        self.assertEqual(single['missing_quote_codes'], ['US.AAA261218P90000'])
        self.assertEqual(single['unassigned_missing_quote_codes'], ['US.AAA1261218P90000'])
        self.assertIn('cannot be assigned', single['collection_notes'][0])

    def test_snapshot_code_batches_support_individual_and_reordered_reads(self):
        codes = ['US.AAA261218P90000', 'US.BBB261218P90000']
        with self.service() as service: service.snapshots(codes)
        self.closed()
        with self.service() as service:
            single = service.snapshots([codes[1]])
            reverse = service.snapshots(codes[::-1])
        self.assertEqual(single['rows'], [dict(code=codes[1], bid_price=2)])
        self.assertEqual([r['code'] for r in reverse['rows']], codes[::-1])
        self.assertEqual(len(self.calls), 1)

    def test_query_runs_configured_retention_without_provider_refresh(self):
        self.store.save('old', '2026-01-01', '2026-01-01T18:00:00+00:00', {'historical': True})
        with self.service() as service: service.collect_put_dataset(['AAA'])
        self.store.set_retention(180)
        self.closed()
        with self.service() as service: result = service.collect_put_dataset(['AAA'])
        self.assertEqual(result['data_access']['source'], 'database')
        self.assertEqual(result['data_access']['cleanup']['deleted'], 1)
        self.assertEqual(len(self.calls), 1)


if __name__ == '__main__': unittest.main()
