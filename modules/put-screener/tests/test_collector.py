from datetime import datetime
import importlib.util
import math
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location('put_collector', ROOT / 'scripts/collect-put-data.py')
collector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(collector)


class Rows:
    def __init__(self, rows): self.rows = rows
    def to_dict(self, orient): return self.rows


class Context:
    def __init__(self):
        self.omit = False
        self.calendar_error = False
        self.calls = []
        self.day = datetime.now(ZoneInfo('America/New_York')).date().isoformat()
        self.expiry = self.day

    def request_trading_days(self, *args, **kwargs):
        return 0, [dict(time=self.day)]

    def get_market_state(self, codes):
        return 0, Rows([dict(code=code, market_state='AFTER_HOURS_BEGIN') for code in codes])

    def get_market_snapshot(self, codes):
        self.calls.append(codes)
        if codes == ['US.TEST']:
            return 0, Rows([dict(code='US.TEST', last_price=100, update_time=self.day + ' 16:00:00')])
        if self.omit: return 0, Rows([])
        return 0, Rows([dict(code=code, stock_owner='US.TEST', strike_time=self.expiry,
            option_strike_price=90, option_type='PUT', option_valid=True, option_contract_size=100,
            bid_price=1.5, ask_price=1.6, bid_vol=10, volume=100, option_open_interest=1000,
            option_delta=-.2, option_implied_volatility=float('nan'), update_time=self.day + ' 15:59:00',
            suspension=False) for code in codes])

    def get_earnings_calendar(self, *args, **kwargs):
        if self.calendar_error: raise RuntimeError('test calendar permission denied')
        return 0, Rows([])


class CollectorTests(unittest.TestCase):
    def setUp(self):
        self.context = Context()
        context = self.context
        class Service:
            def __init__(self, sdk, ctx): pass
            def query(self, query):
                context.expiry = query.end.isoformat()
                return dict(symbol=query.code, start=query.start.isoformat(), end=context.expiry,
                    expirations=[context.expiry], queried_at='test', contracts=[dict(
                    code='US.TESTOPTION', stock_owner=query.code, option_type='PUT',
                    strike_time=context.expiry, strike_price=90, lot_size=100,
                    option_standard_type='STANDARD', suspension=False)])
        self.service_patch = patch.object(collector, 'OptionChainService', Service)
        self.sleep_patch = patch.object(collector.time, 'sleep')
        self.service_patch.start(); self.sleep_patch.start()
        self.sdk = SimpleNamespace(RET_OK=0, Market=SimpleNamespace(US='US'))

    def tearDown(self):
        self.service_patch.stop(); self.sleep_patch.stop()

    def collect(self):
        return collector.collect(self.sdk, self.context, ['TEST'], months=1)

    def test_snapshot_fields_and_unknown_earnings_are_preserved(self):
        result = self.collect(); row = result['contracts'][0]
        self.assertEqual(row['bid'], 1.5)
        self.assertEqual(row['snapshot_symbol'], 'US.TEST')
        self.assertIsNone(row['iv_pct'])
        self.assertIsNone(row['earnings'])
        self.assertTrue(row['earnings_calendar_complete'])
        self.assertEqual(result['missing_quote_codes'], [])

    def test_missing_snapshots_are_reported_and_not_synthesized(self):
        self.context.omit = True
        result = self.collect()
        self.assertEqual(result['contracts'], [])
        self.assertEqual(result['missing_quote_codes'], ['US.TESTOPTION'])

    def test_calendar_errors_are_visible_and_block_clearance(self):
        self.context.calendar_error = True
        result = self.collect()
        self.assertFalse(result['contracts'][0]['earnings_calendar_complete'])
        self.assertIn('permission denied', result['calendar_errors'][0]['error'])

    def test_other_markets_rejected_before_snapshot_calls(self):
        with self.assertRaises(ValueError): collector.collect(self.sdk, self.context, ['HK.00700'])
        self.assertEqual(self.context.calls, [])


if __name__ == '__main__': unittest.main()
