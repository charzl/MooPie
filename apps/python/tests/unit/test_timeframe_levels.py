import copy
from datetime import date, timedelta
import math
import unittest

from moopython.timeframe_levels import timeframe_levels
from moopython.price_signal_view import signals_html


class TimeframeLevelTests(unittest.TestCase):
    def fixture(self):
        bars = []
        day = date(2025, 1, 1)
        while day <= date(2026, 5, 22):
            if day.weekday() < 5:
                index = len(bars)
                price = 100 + 11*math.sin(index*math.pi/22)
                bars.append(dict(date=day.isoformat(), open=price-.4, high=price+1.2,
                                 low=price-1.3, close=price, volume=1000, complete=True))
            day += timedelta(days=1)
        series = dict(symbol='US.TEST', as_of=bars[-1]['date'], bars=bars)
        signal = dict(symbol='US.TEST', status='ok', as_of=series['as_of'],
                      reference=dict(price=103, basis='underlying_snapshot', time='2026-05-22 16:00:00'),
                      support_zones=[], resistance_zones=[])
        return series, signal

    def test_unfinished_week_and_month_do_not_confirm_pivots(self):
        series, signal = self.fixture()
        before = copy.deepcopy((series, signal))
        result = timeframe_levels(series, signal, '2026-05-22T21:00:00+00:00')
        self.assertEqual(result['status'], 'ok')
        self.assertEqual(result['periods']['week']['as_of'], '2026-05-15')
        self.assertEqual(result['periods']['month']['as_of'], '2026-04-30')
        self.assertEqual((series, signal), before)
        later = timeframe_levels(series, signal, '2026-05-25T21:00:00+00:00')
        self.assertEqual(later['periods']['week']['as_of'], '2026-05-22')
        self.assertEqual(later['periods']['month']['as_of'], '2026-04-30')

    def test_short_history_and_invalid_signal_are_explicit(self):
        series, signal = self.fixture()
        short = dict(series, bars=series['bars'][-80:])
        result = timeframe_levels(short, signal, '2026-05-22T21:00:00+00:00')
        self.assertEqual(result['periods']['month']['status'], 'unavailable')
        self.assertEqual(result['periods']['month']['support_zones'], [])
        self.assertEqual(timeframe_levels(series, dict(signal, status='unavailable'), '2026-05-22T21:00:00+00:00')['status'], 'unavailable')
        self.assertEqual(timeframe_levels(series, signal, 'bad timestamp')['status'], 'unavailable')

    def test_overlap_display_reports_only_intersecting_zones(self):
        series, signal = self.fixture()
        signal.update(summary='测试', version='1.0', lookback_bars=120, atr14=4,
                      reasons=[], next_check='观察', limitations=[], support_zones=[dict(low=90,high=93,
                      distance_pct=1,distance_atr=1, independent_touches=1,
                      evidence=[dict(date='2026-05-01')])])
        multi = timeframe_levels(series, signal, '2026-05-22T21:00:00+00:00')
        multi['periods']['week']['support_zones'] = [dict(low=92, high=95)]
        multi['periods']['month']['support_zones'] = [dict(low=80, high=85)]
        signal['multi_timeframe'] = multi
        html = signals_html({'US.TEST': signal})
        self.assertIn('日线与周线', html)
        self.assertNotIn('日线与月线', html)
        self.assertIn('2026-04-30', html)


if __name__ == '__main__': unittest.main()
