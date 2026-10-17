from contextlib import contextmanager, redirect_stdout
from datetime import datetime
import copy
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from moopython.market_repository import CachedMarketData, CacheMissError
from moopython.market_store import SnapshotStore
from moopython.research import load_rules
from moopython.saved_research import completed_session, saved_research

ROOT = Path(__file__).resolve().parents[4]


class SavedResearchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = SnapshotStore(Path(self.temp.name)/'quotes.sqlite3')
        self.dataset = json.loads((ROOT/'modules/put-screener/example.json').read_text())

    def save(self, timestamp, day='2026-10-16', codes=('US.TEST',)):
        data = copy.deepcopy(self.dataset)
        data.update(symbols=list(codes),session_date=day,collected_at=timestamp,
                    fetched_at=timestamp,decision_cutoff=timestamp)
        def collect(symbols, months=3): return data
        def basic(codes):
            return dict(codes=codes,collected_at=timestamp,missing_codes=[],rows=[
                dict(code=c,name=c,stock_type='STOCK',delisting=False) for c in codes])
        @contextmanager
        def connection(**options): yield SimpleNamespace(collect_put_dataset=collect,basic_info=basic)
        router=CachedMarketData(store=self.store,refresh=True,connection=connection,
                                clock=lambda:datetime.fromisoformat(timestamp))
        try:
            router.basic_info(list(codes)); router.collect_put_dataset(list(codes))
        finally: router.close()

    def read(self, now='2026-10-19T15:00:00+00:00', **options):
        with patch('socket.create_connection',side_effect=AssertionError('Saved view must be offline')):
            return saved_research(['US.TEST'],'put',store=self.store,now=datetime.fromisoformat(now),**options)

    def test_completed_session_handles_premarket_intraday_weekend_holiday_and_early_close(self):
        for now, expected in [
            ('2026-10-19T10:00:00-04:00','2026-10-16'),
            ('2026-10-19T07:00:00-04:00','2026-10-16'),
            ('2026-10-19T16:14:59-04:00','2026-10-16'),
            ('2026-10-19T16:15:00-04:00','2026-10-19'),
            ('2026-10-17T18:00:00-04:00','2026-10-16'),
            ('2026-11-26T18:00:00-05:00','2026-11-25'),
            ('2026-11-27T13:14:59-05:00','2026-11-25'),
            ('2026-11-27T13:15:00-05:00','2026-11-27')]:
            with self.subTest(now=now): self.assertEqual(completed_session(datetime.fromisoformat(now)),expected)

    def test_opening_intraday_ignores_newer_live_snapshot_and_reuses_precomputed_report(self):
        self.save('2026-10-16T22:00:00+00:00')
        first=self.read()
        self.save('2026-10-19T14:00:00+00:00','2026-10-19')
        # Memoized view must not recalculate the recommendation on reopening.
        rules=load_rules()
        with patch('moopython.research.load_rules',return_value=rules), \
             patch.object(rules,'recommend',side_effect=AssertionError('Should reuse report')):
            second=self.read()
        self.assertTrue(second['saved_view']['precomputed'])
        self.assertEqual(json.dumps(first['report'],sort_keys=True),json.dumps(second['report'],sort_keys=True))
        self.assertEqual(second['report']['session_date'],'2026-10-16')
        self.assertEqual(second['collected_at'],'2026-10-16T22:00:00+00:00')

    def test_after_close_selects_new_closing_snapshot_and_never_relabels_intraday_as_close(self):
        self.save('2026-10-16T22:00:00+00:00')
        self.save('2026-10-19T14:00:00+00:00','2026-10-19')
        old=self.read('2026-10-19T22:00:00+00:00')
        self.assertEqual(old['report']['session_date'],'2026-10-16')
        self.assertIn('更早',old['data_access']['note'])
        self.save('2026-10-19T21:00:00+00:00','2026-10-19')
        new=self.read('2026-10-19T22:00:00+00:00')
        self.assertEqual(new['report']['session_date'],'2026-10-19')
        self.assertFalse(new['saved_view']['precomputed'])

    def test_sort_top_filters_and_rule_revision_cannot_reuse_the_wrong_report(self):
        self.save('2026-10-16T22:00:00+00:00')
        original=self.read()
        config=load_rules().recommendation_configuration()
        config['sort_order']=[list(row) for row in load_rules().RANKING_SORT_ORDERS['cost']]
        changed=self.read(configuration=config,top_n=5)
        self.assertFalse(changed['saved_view']['precomputed'])
        self.assertEqual(changed['report']['top_n_requested'],5)
        self.assertEqual(changed['report']['sort_order'],config['sort_order'])
        self.assertEqual(changed['input_dataset']['collected_at'],original['collected_at'])
        self.assertTrue(self.read(configuration=config,top_n=5)['saved_view']['precomputed'])
        with patch('moopython.saved_research.analysis_revision',return_value='new engine'):
            self.assertFalse(self.read(configuration=config,top_n=5)['saved_view']['precomputed'])

    def test_cache_absence_or_only_intraday_data_requires_explicit_update(self):
        with self.assertRaisesRegex(CacheMissError,'更新行情'): self.read()
        self.save('2026-10-16T15:00:00+00:00')
        with self.assertRaisesRegex(CacheMissError,'更新行情'): self.read()

    def test_legacy_batch_projection_and_saved_watchlist_remain_offline(self):
        self.save('2026-10-16T22:00:00+00:00',codes=('US.TEST','US.OTHER'))
        # Emulate old batch-only storage, before per-stock cache partitions.
        with self.store.connect() as connection:
            connection.execute('DELETE FROM snapshots WHERE symbol IS NOT NULL')
        result=self.read(watchlist=True)
        self.assertEqual(result['symbols'],['US.TEST'])
        self.assertEqual(result['collection_errors'],[])
        self.assertEqual(result['data_access']['source'],'database')

    def test_cleanup_removes_report_and_market_inputs_together(self):
        self.save('2026-10-16T22:00:00+00:00'); self.read()
        self.store.cleanup(older_than_days=1,now=datetime.fromisoformat('2026-10-20T22:00:00+00:00'))
        with self.assertRaises(CacheMissError): self.read('2026-10-20T23:00:00+00:00')

    def test_explicit_closing_result_is_precomputed_before_the_next_opening(self):
        from moopython.research import run_research
        from moopython.saved_research import SavedMarketData, remember_closing_result
        self.save('2026-10-16T22:00:00+00:00')
        now=datetime.fromisoformat('2026-10-17T15:00:00+00:00')
        service=SavedMarketData(['US.TEST'],store=self.store,now=now)
        result=run_research(service,'US.TEST','put')
        result['data_access']['source']='OpenD'
        remember_closing_result(result,store=self.store,now=now)
        default=self.read()
        self.assertTrue(default['saved_view']['precomputed'])
        self.assertEqual(default['data_access']['source'],'database')
        self.assertEqual(default['data_access']['market']['checked_at'],'2026-10-19T15:00:00+00:00')
        self.assertEqual(default['report']['recommendations'],result['report']['recommendations'])

    def test_cli_saved_output_stays_on_stdout_and_no_provider_is_opened(self):
        from moopython import research_cli
        self.save('2026-10-16T22:00:00+00:00')
        with patch.dict('os.environ',{'MOOMOO_DB_PATH':str(self.store.path)}), \
             patch.object(research_cli,'market_data_connection',side_effect=AssertionError('No live route')), \
             patch('moopython.saved_research.datetime',wraps=datetime) as clock, redirect_stdout(io.StringIO()) as output:
            clock.now.return_value=datetime.fromisoformat('2026-10-19T15:00:00+00:00')
            code=research_cli.main(['put','TEST','--saved'])
        self.assertEqual(code,0)
        self.assertEqual(json.loads(output.getvalue())['report']['session_date'],'2026-10-16')


if __name__=='__main__': unittest.main()
