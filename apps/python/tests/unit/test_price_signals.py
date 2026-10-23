"""Signals are auditable observations, with no path into the ranking result."""
import copy
from datetime import date, timedelta
import json
import math
from pathlib import Path
import unittest
from unittest.mock import patch

from moopython.price_signals import dataset_signals, price_position
from moopython.price_signal_view import signals_html
from moopython.research import analyze_put_dataset, load_rules, run_research
from moopython.watchlist_research import analyze_watchlist_dataset

ROOT = Path(__file__).resolve().parents[4]


class PriceSignalTests(unittest.TestCase):
    def fixture(self):
        # Synthetic oscillations with repeated lows at 160 and highs at 210.
        bars = []
        for index in range(120):
            price = 185+24*math.cos(index*math.pi/10)
            bars.append(dict(date=(date(2026, 1, 1)+timedelta(days=index)).isoformat(),
                             open=price, close=price, low=price-1, high=price+1, volume=1000, complete=True))
        series = dict(symbol='US.TEST', as_of=bars[-1]['date'], bars=bars)
        trend = dict(symbol='US.TEST', status='ok', as_of=series['as_of'],
                     bar_count=len(bars), available_at=series['as_of']+'T16:05:00-04:00',
                     metrics=dict(close=bars[-1]['close'], atr14=4, ma20=185,
                                  macd_histogram=1, macd_histogram_change=.2))
        return series, trend

    def test_repeated_regions_show_price_location_not_waiting_orders_or_probability(self):
        series, trend = self.fixture()
        before = copy.deepcopy((series, trend))
        result = price_position(series, trend, reference=dict(price=200, time='synthetic', basis='underlying_snapshot'))
        self.assertEqual(result['assessment'], 'closer_to_resistance')
        self.assertAlmostEqual(result['support_zones'][0]['center'],160)
        self.assertAlmostEqual(result['resistance_zones'][0]['center'],210)
        self.assertGreaterEqual(result['support_zones'][0]['independent_touches'],5)
        self.assertEqual(result['ranking_effect'],'none')
        self.assertEqual(result['order_flow'],dict(status='not_verified',buy_sell_ratio=None))
        self.assertEqual((series, trend),before)
        self.assertIn('历史转折推断',signals_html({'US.TEST':result}))

    def test_reference_price_changes_position_but_near_support_does_not_claim_buy(self):
        series, trend = self.fixture()
        result = price_position(series,trend,reference=dict(price=161,time='synthetic',basis='underlying_snapshot'))
        self.assertEqual(result['assessment'],'near_support')
        self.assertIn('确认承接',result['summary'])
        self.assertIn('不是开仓依据',result['next_check'])

    def test_support_centers_are_below_and_resistance_centers_above_reference(self):
        series, trend = self.fixture()
        for price in (159, 161, 209, 211):
            result = price_position(series,trend,reference=dict(price=price,time='synthetic',basis='underlying_snapshot'))
            self.assertTrue(all(zone['center'] < price for zone in result['support_zones']))
            self.assertTrue(all(zone['center'] > price for zone in result['resistance_zones']))

    def test_missing_invalid_or_inconsistent_history_remains_unknown(self):
        series, trend = self.fixture()
        invalid = dict(trend,status='invalid_data',error='history missing')
        result = price_position(None,invalid)
        self.assertEqual(result['status'],'unavailable')
        self.assertEqual(result['support_zones'],[])
        self.assertEqual(price_position(dict(series,as_of='2000-01-01'),trend)['status'],'unavailable')
        self.assertEqual(price_position(series,trend,reference=dict(price=float('nan')))['status'],'unavailable')
        for value in (True, None, {}, '200'):
            self.assertEqual(price_position(series,trend,reference=dict(price=value))['status'],'unavailable')

    def test_monotonic_history_does_not_invent_zones(self):
        series, trend = self.fixture()
        for index, bar in enumerate(series['bars']):
            bar.update(open=100+index,close=100+index,low=99+index,high=101+index)
        result = price_position(series,trend)
        self.assertEqual(result['support_zones'],[])
        self.assertEqual(result['resistance_zones'],[])
        self.assertEqual(result['assessment'],'unconfirmed')

    def test_final_two_bars_are_not_confirmed_pivots_and_each_event_has_confirmation_date(self):
        series, trend = self.fixture()
        series['bars'][-1]['low']=1
        result = price_position(series,trend)
        self.assertTrue(result['support_zones'])
        for zone in result['support_zones']+result['resistance_zones']:
            for event in zone['evidence']:
                self.assertLess(event['date'],event['confirmed_at'])
                self.assertLessEqual(event['confirmed_at'],series['as_of'])
                self.assertNotEqual(event['price'],1)

    def test_signal_failure_leaves_identical_full_engine_report_and_input(self):
        dataset=json.loads((ROOT/'modules/put-screener/example.json').read_text())
        code=dataset['contracts'][0]['symbol']
        dataset['symbols']=[code]
        before=copy.deepcopy(dataset)
        reference=load_rules().recommend(dataset,per_symbol_limit=20)
        normal=analyze_put_dataset(dataset,code)
        self.assertEqual(normal['report'],reference)
        self.assertEqual(normal['price_signals'][code]['status'],'ok')
        with patch('moopython.price_signals.price_position',return_value=dict(status='unavailable')):
            self.assertEqual(analyze_put_dataset(dataset,code)['report'],reference)
            self.assertEqual(analyze_watchlist_dataset(dataset)['report'],reference)
        self.assertEqual(dataset,before)

    def test_cached_trend_adds_signal_without_another_service_call(self):
        dataset=json.loads((ROOT/'modules/put-screener/example.json').read_text())
        code=dataset['contracts'][0]['symbol']
        class Service:
            calls=0
            def daily_bars(self,symbols):
                self.calls+=1
                return dict(daily_series=dataset['daily_series'],fetched_at=dataset['collected_at'],
                            decision_cutoff=dataset['collected_at'])
        service=Service()
        with patch('socket.create_connection',side_effect=AssertionError('No new fetch')):
            result=run_research(service,code,'trend')
        self.assertEqual(service.calls,1)
        self.assertEqual(result['price_signals'][code]['reference']['basis'],'daily_close')

    def test_inconsistent_underlying_references_do_not_guess_a_price(self):
        series, trend = self.fixture()
        dataset=dict(daily_series=[series],contracts=[dict(symbol='US.TEST',underlying_price=200),
                                                    dict(symbol='US.TEST',underlying_price=201)])
        result=dataset_signals(dataset,{'US.TEST':trend})
        self.assertEqual(result['US.TEST']['status'],'unavailable')


if __name__=='__main__': unittest.main()
