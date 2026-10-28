from copy import deepcopy
from contextlib import contextmanager, redirect_stdout
from datetime import date, timedelta
import io
import json
import math
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from moopython.market_store import SnapshotStore
from moopython.support_study import PARAMETERS, _outcome, advance_zone, support_study
from moopython.support_study_store import SupportStudyStore
from moopython.support_study_view import backtest_html, lifecycle_html


def fixture(count=380):
    bars = []
    for index in range(count):
        price = 110+10*math.cos(index*math.pi/10)
        bars.append(dict(date=(date(2025, 1, 1)+timedelta(days=index)).isoformat(),
                         open=price, high=price+1, low=price-1, close=price,
                         volume=1000, complete=True))
    return dict(symbol='US.TEST', interval='1d', adjustment='qfq', session='regular',
                as_of=bars[-1]['date'], bars=bars, calendar_dates=[bar['date'] for bar in bars])


def trend(series):
    return dict(symbol=series['symbol'], status='ok', as_of=series['as_of'], bar_count=len(series['bars']))


class SupportStudyTests(unittest.TestCase):
    def test_historical_definitions_do_not_read_future_bars(self):
        early = fixture(300)
        before = deepcopy(early)
        initial = support_study(early, trend(early))
        extended = fixture(380)
        for bar in extended['bars'][300:]:
            for key in ('open', 'high', 'low', 'close'):
                bar[key] *= 10  # A large future shock must not alter historical zone definitions.
        later = support_study(extended, trend(extended))
        self.assertEqual(initial['status'], 'ok')
        self.assertTrue(initial['backtest']['samples'])
        self.assertEqual(early, before)
        old_samples = {sample['touch_date']: sample for sample in initial['backtest']['samples']}
        for sample in later['backtest']['samples']:
            if sample['touch_date'] in old_samples:
                self.assertEqual(sample['zone'], old_samples[sample['touch_date']]['zone'])
            for item in sample['zone']['evidence']:
                self.assertLessEqual(item['confirmed_at'], sample['signal_date'])
            self.assertLess(sample['signal_date'], sample['touch_date'])
        continued = support_study(extended, trend(extended), previous=initial)
        self.assertEqual(continued['lifecycle'], later['lifecycle'])
        old = {record['zone_id']: record for record in initial['lifecycle']['records']}
        for record in continued['lifecycle']['records']:
            if record['zone_id'] in old:
                self.assertEqual((record['low'], record['high']), (old[record['zone_id']]['low'], old[record['zone_id']]['high']))

    def test_sample_windows_do_not_overlap_and_incomplete_outcomes_stay_pending(self):
        series = fixture()
        result = support_study(series, trend(series))
        positions = {bar['date']: index for index, bar in enumerate(series['bars'])}
        samples = result['backtest']['samples']
        self.assertGreater(len(samples), 2)
        for previous, current in zip(samples, samples[1:]):
            self.assertGreater(positions[current['touch_date']]-positions[previous['touch_date']], PARAMETERS['separation_bars'])
        self.assertTrue(any(outcome['status'] == 'pending' for sample in samples for outcome in sample['outcomes']))
        for summary in result['backtest']['summaries']:
            self.assertEqual(summary['complete']+summary['pending'], len(samples))
            self.assertEqual(summary['positive']+summary['negative']+summary['flat'], summary['complete'])
        for sample in samples:
            for outcome in sample['outcomes']:
                if outcome['status'] == 'pending':
                    self.assertIsNone(outcome['close_return_pct'])

    def test_forward_statistics_start_after_touch_close(self):
        bars = [dict(date=f'2026-01-{index+1:02d}', close=100 if index == 0 else 110,
                     high=200 if index == 0 else 120, low=50 if index == 0 else 80) for index in range(6)]
        outcome = _outcome(bars, 0, dict(low=90), 5)
        self.assertAlmostEqual(outcome['close_return_pct'], 10)
        self.assertAlmostEqual(outcome['max_rise_pct'], 20)
        self.assertAlmostEqual(outcome['max_drop_pct'], -20)
        self.assertEqual(outcome['first_break_date'], None)  # Breaks use closes, not intraday lows.
        self.assertEqual(_outcome(bars, 1, dict(low=90), 5)['status'], 'pending')

    def test_frozen_zone_tracks_break_retest_rejection_and_reclaim_once(self):
        record = dict(low=90, high=95, state='active', phase='support', tests=0, breaks=0,
                      resistance_tests=0, in_contact=False, last_evaluated='2026-01-01', events=[])
        def observe(day, low, high, close):
            advance_zone(record, dict(date=f'2026-01-{day:02d}', low=low, high=high, close=close))
        observe(2, 92, 98, 96)
        self.assertEqual(record['state'], 'held')
        observe(3, 89, 93, 89)
        self.assertEqual(record['state'], 'broken')
        observe(4, 86, 88, 87)
        observe(5, 88, 92, 89)
        self.assertEqual(record['state'], 'resistance')
        observe(6, 94, 98, 96)
        self.assertEqual(record['state'], 'reclaimed')
        frozen = deepcopy(record)
        observe(6, 1, 2, 1)
        self.assertEqual(record, frozen)
        self.assertEqual((record['tests'], record['breaks'], record['resistance_tests']), (1, 1, 1))
        self.assertEqual((record['low'], record['high']), (90, 95))

    def test_gap_below_support_records_failure_without_inventing_a_touch(self):
        record = dict(low=90, high=95, state='active', phase='support', tests=0, breaks=0,
                      resistance_tests=0, in_contact=False, last_evaluated='2026-01-01', events=[])
        advance_zone(record, dict(date='2026-01-02', low=80, high=85, close=82))
        self.assertEqual(record['tests'], 0)
        self.assertTrue(record['events'][0]['gap_through'])
        self.assertEqual(record['state'], 'broken')

    def test_role_change_resets_contact_sequence_for_next_days_retest(self):
        record = dict(low=90, high=95, state='testing', phase='support', tests=1, breaks=0,
                      resistance_tests=0, in_contact=True, last_evaluated='2026-01-01', events=[])
        advance_zone(record, dict(date='2026-01-02', low=88, high=92, close=89))
        advance_zone(record, dict(date='2026-01-03', low=88, high=92, close=89))
        self.assertEqual(record['state'], 'resistance')
        self.assertEqual(record['resistance_tests'], 1)
        self.assertEqual(record['events'][-1]['kind'], 'resistance')

    def test_price_revisions_and_missing_history_do_not_silently_rewrite_old_zones(self):
        early = fixture(300)
        previous = support_study(early, trend(early))
        current = fixture(320)
        current['bars'][220]['high'] += 1
        revised = support_study(current, trend(current), previous=previous)
        repeated = support_study(current, trend(current), previous=revised)
        self.assertEqual(repeated, revised)
        old_ids = {record['zone_id'] for record in previous['lifecycle']['records']}
        self.assertTrue(old_ids)
        self.assertTrue(all(record['state'] == 'basis_changed' for record in revised['lifecycle']['records']
                            if record['zone_id'] in old_ids))
        missing = fixture(620)
        missing['bars'] = missing['bars'][310:]
        missing['calendar_dates'] = [bar['date'] for bar in missing['bars']]
        report = support_study(missing, trend(missing), previous=previous)
        self.assertEqual(report['lifecycle']['notices'][0]['kind'], 'history_gap')
        self.assertTrue(all(record['state'] == 'history_gap' for record in report['lifecycle']['records']
                            if record['zone_id'] in old_ids))

    def test_invalid_history_is_not_backtested(self):
        series = fixture()
        series['bars'][-1]['complete'] = False
        self.assertEqual(support_study(series, trend(series))['status'], 'unavailable')
        self.assertEqual(support_study(fixture(120), trend(fixture(120)))['status'], 'unavailable')

    def test_valid_history_without_pivots_keeps_zero_samples(self):
        series = fixture()
        for index, bar in enumerate(series['bars']):
            price = 100+index
            bar.update(open=price, close=price, low=price-1, high=price+1)
        report = support_study(series, trend(series))
        self.assertEqual(report['status'], 'ok')
        self.assertEqual(report['backtest']['sample_count'], 0)
        self.assertEqual(report['lifecycle']['records'], [])
        self.assertIsNone(report['backtest']['summaries'][0]['median_return_pct'])

    def test_sqlite_retains_inputs_and_continues_frozen_history(self):
        with tempfile.TemporaryDirectory() as directory:
            market = SnapshotStore(Path(directory)/'market.sqlite3')
            store = SupportStudyStore(market)
            early = fixture(300)
            saved = store.evaluate(early, trend(early))
            self.assertIsNotNone(saved['calculated_at'])
            repeated = store.evaluate(early, trend(early))
            self.assertEqual(saved['study'], repeated['study'])
            self.assertEqual(len(store.history('US.TEST')), 1)
            later = fixture(320)
            current = store.evaluate(later, trend(later))
            self.assertEqual(len(store.history('US.TEST')), 2)
            self.assertEqual(store.latest('US.TEST', as_of=early['as_of'])['study'], saved['study'])
            self.assertEqual(store.latest('US.TEST')['study'], current['study'])
            self.assertEqual(current['study']['input_series'], later)
            self.assertIsNone(store.save(dict(status='unavailable')))
            from moopython.database_cli import main
            output = io.StringIO()
            with patch.dict(os.environ, {'MOOMOO_DB_PATH': str(market.path)}), redirect_stdout(output), \
                 patch('socket.create_connection', side_effect=AssertionError('Local history only')):
                self.assertEqual(main(['support-studies', 'TEST', '--limit', '1']), 0)
            self.assertEqual(json.loads(output.getvalue())['history'][0]['study'], current['study'])

    def test_views_show_small_sample_and_pending_without_claiming_a_win_probability(self):
        series = fixture()
        study = support_study(series, trend(series))
        html = backtest_html(study)
        self.assertIn('样本偏少', html)
        self.assertIn('待观察', html)
        self.assertIn('当前版本前复权', html)
        self.assertIn('生命周期', lifecycle_html(study))
        import re
        self.assertIsNone(re.search('[\u4e00-\u9fff]', backtest_html(study, 'en')))
        self.assertIsNone(re.search('[\u4e00-\u9fff]', lifecycle_html(study, 'en')))
        self.assertIn('&lt;missing&gt;', backtest_html(dict(status='unavailable', reason='<missing>')))

    def test_detail_cli_can_compute_daily_study_even_if_latest_quote_fails(self):
        from moopython.research_cli import main
        series = fixture()
        evidence = dict(trend(series), metrics=dict(close=series['bars'][-1]['close'], atr14=4,
                        ma20=110, macd_histogram=1, macd_histogram_change=.1))
        @contextmanager
        def market(**_options):
            class Service:
                def snapshots(self, _symbols): raise RuntimeError('quote unavailable')
                def daily_bars(self, _symbols):
                    return dict(daily_series=[series], decision_cutoff='2026-10-27T20:05:00+00:00')
            yield Service()
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {'MOOMOO_DB_PATH': str(Path(folder)/'market.sqlite3')}):
            output = Path(folder)/'result.json'
            with patch('moopython.research_cli.market_data_connection', market), \
                 patch('moopython.research_cli.run_research', return_value=dict(action='trend', symbol='US.TEST', trend=evidence)), \
                 patch('moopython.order_book.read_order_book', return_value=dict(status='unavailable', reason='no permission')):
                self.assertEqual(main(['trend', 'TEST', '--depth', '--output', str(output)]), 0)
            result = json.loads(output.read_text())
            self.assertEqual(result['support_study']['status'], 'ok')
            self.assertEqual(result['quote_error'], 'quote unavailable')
            self.assertTrue(result['support_study_saved_at'])
            self.assertEqual(SupportStudyStore().latest('US.TEST')['study'], result['support_study'])


if __name__ == '__main__': unittest.main()
