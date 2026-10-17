import copy
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('trend_rules', ROOT / 'put_rules.py')
rules = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rules)


class TrendTests(unittest.TestCase):
    def setUp(self):
        self.dataset = json.loads((ROOT / 'example.json').read_text())
        self.series = self.dataset['daily_series'][0]
        self.original_rules = copy.deepcopy(rules.TREND_RULES)

    def tearDown(self):
        rules.TREND_RULES = self.original_rules

    def result(self):
        return rules.scan(self.dataset)['underlyings']['US.TEST']

    def test_known_ema_seed_and_wilder_rsi_example(self):
        self.assertEqual(rules.ema([1, 2, 3, 4, 5], 3), [(2, 2), (3, 3), (4, 4)])
        close = [44.34, 44.09, 44.15, 43.61, 44.33, 44.83, 45.10, 45.42,
                 45.84, 46.08, 45.89, 46.03, 45.61, 46.28, 46.28]
        changes = [b-a for a,b in zip(close, close[1:])]
        gain = rules.wilder([max(c, 0) for c in changes])
        loss = rules.wilder([max(-c, 0) for c in changes])
        self.assertAlmostEqual(100 - 100/(1+gain/loss), 70.4641350211)
        self.assertAlmostEqual(rules.wilder([14]*14+[28]), 15)

    def test_moving_averages_exclude_future_and_support_excludes_current(self):
        result = self.result(); m = result['metrics']
        closes = [bar['close'] for bar in self.series['bars']]
        self.assertAlmostEqual(m['ma50'], sum(closes[-50:])/50)
        self.assertAlmostEqual(m['ma200'], sum(closes[-200:])/200)
        self.assertEqual(m['prior_20d_low'], min(b['low'] for b in self.series['bars'][-21:-1]))
        self.assertTrue(result['allowed'])
        self.assertEqual(m['rsi14'], 100)
        self.assertEqual(m['volume_ratio_20d'], 1)
        self.assertTrue(all(r['passed'] for r in result['rules']))

    def test_crash_blocks_all_puts_even_high_yield_and_unknown_earnings(self):
        for index, bar in enumerate(self.series['bars'][-12:]):
            value = 94-index*3
            bar.update(open=value+.2, high=value+.5, low=value-.5, close=value, volume=4000)
        self.dataset['contracts'][0].update(bid=3, ask=3.1, earnings=None)
        report = rules.scan(self.dataset)
        t = report['underlyings']['US.TEST']
        self.assertFalse(t['allowed'])
        self.assertIn('above-ma50', t['failed_rules'])
        self.assertIn('no-20d-breakdown', t['failed_rules'])
        self.assertIn('rsi-floor', t['failed_rules'])
        self.assertGreater(t['metrics']['volume_ratio_20d'], 1)
        self.assertEqual(report['ranked'], [])
        self.assertEqual(report['earnings_unverified_watchlist'], [])
        self.assertIn('underlying-trend', report['results'][0]['failed_rules'])

    def test_steady_downtrend_and_oversold_are_not_reversal(self):
        for index, bar in enumerate(self.series['bars']):
            value = 200-index*.4
            bar.update(open=value, high=value+.5, low=value-.5, close=value)
        result = self.result()
        self.assertEqual(result['state'], 'downtrend')
        self.assertEqual(result['metrics']['rsi14'], 0)
        self.assertAlmostEqual(result['metrics']['atr14'], 1)
        self.assertFalse(result['allowed'])

    def test_flat_market_has_defined_rsi_and_zero_atr(self):
        for bar in self.series['bars']:
            bar.update(open=100, high=100, low=100, close=100, volume=0)
        result = self.result()
        self.assertEqual(result['metrics']['rsi14'], 50)
        self.assertEqual(result['metrics']['atr14'], 0)
        self.assertEqual(result['metrics']['macd_histogram_change'], 0)
        m = rules.scan(self.dataset)['results'][0]['metrics']
        self.assertIsNone(m['strike_below_20d_low_atr'])

    def test_missing_failed_or_insufficient_history_fails_closed(self):
        original = copy.deepcopy(self.series)
        for series in (None, dict(original, error='No permission'),
                       dict(original, bars=original['bars'][-100:]), dict(original, adjustment='none')):
            self.dataset['daily_series'] = [] if series is None else [series]
            report = rules.scan(self.dataset)
            self.assertEqual(report['qualified_count'], 0)
            self.assertEqual(report['underlyings']['US.TEST']['status'], 'invalid_data')

    def test_gaps_duplicates_bad_ohlcv_and_unfinished_bar_fail_closed(self):
        original = copy.deepcopy(self.series['bars'])
        variants = [original[:-1], original+[copy.deepcopy(original[-1])], original[1:]]
        for change in ({'complete': False}, {'volume': -1}, {'low': 1000}, {'close': None}):
            bars = copy.deepcopy(original); bars[-1].update(change); variants.append(bars)
        for bars in variants:
            self.series['bars'] = bars
            self.assertEqual(self.result()['status'], 'invalid_data')

    def test_current_day_bar_unavailable_intraday_and_stale_daily_data_rejected(self):
        self.dataset['collected_at'] = '2026-10-16T18:00:00+00:00'
        self.assertIn('not finalized', self.result()['error'])
        self.dataset['collected_at'] = '2026-10-16T22:00:00+00:00'
        for key in ('bars', 'calendar_dates'): self.series[key] = self.series[key][:-1]
        self.series.update(as_of='2026-10-15', available_at='2026-10-15T16:05:00-04:00')
        self.assertIn('completed quote session', self.result()['error'])
        # Prior completed day IS usable before today's close.
        self.dataset['collected_at'] = '2026-10-16T18:00:00+00:00'
        self.assertEqual(self.result()['status'], 'ok')

    def test_calendar_and_session_finalization_are_validated(self):
        self.series['available_at'] = '2026-10-16T12:00:00-04:00'
        self.assertIn('before session finalization', self.result()['error'])
        self.series['available_at'] = '2026-10-16T16:05:00-04:00'
        self.series['calendar_dates'][-1] = '2026-10-15'
        self.assertEqual(self.result()['status'], 'invalid_data')

    def test_trend_rule_edits_change_audit_fingerprint(self):
        old = rules.scan(self.dataset)
        rules.TREND_RULES[0] = ('above-ma50', 'distance_to_ma50_pct', '>=', 100)
        new = rules.scan(self.dataset)
        self.assertNotEqual(old['rules_sha256'], new['rules_sha256'])
        self.assertEqual(new['qualified_count'], 0)
        rules.TREND_RULES[0] = ('oops', 'made_up_metric', '>=', 0)
        with self.assertRaises(ValueError): rules.scan(self.dataset)

    def test_duplicate_daily_series_rejected(self):
        self.dataset['daily_series'].append(copy.deepcopy(self.series))
        with self.assertRaisesRegex(ValueError, 'Duplicate daily series'): rules.scan(self.dataset)


if __name__ == '__main__': unittest.main()
