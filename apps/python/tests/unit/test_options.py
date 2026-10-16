import csv
from datetime import date
import io
import json
import threading
import time
from types import SimpleNamespace
import unittest

from moopython.options import (
    OptionChainService, OptionQuery, QueryCancelled, add_months, chain_windows,
    option_symbol, write_result,
)


class Rows:
    def __init__(self, rows):
        self.rows = rows

    def to_dict(self, orient):
        return self.rows


class Context:
    def __init__(self):
        self.expirations = ['2027-01-31', '2027-02-01', '2027-03-02', '2027-04-30', '2027-05-01']
        self.calls = []
        self.fail_at = None

    def get_option_expiration_date(self, code):
        return 0, Rows([dict(strike_time=day) for day in self.expirations])

    def get_option_chain(self, code, start, end, option_type):
        self.calls.append((code, start, end, option_type))
        if len(self.calls) == self.fail_at:
            return -1, 'permission denied for a later window'
        rows = [dict(code=f'{code}-{day}-{kind}', name='Test option', stock_owner=code,
                     strike_time=day, option_type=kind, strike_price=100.5, lot_size=100,
                     option_standard_type='STANDARD', expiration_cycle='MONTH', suspension=False)
                for day in self.expirations if start <= day <= end for kind in ('CALL', 'PUT')]
        return 0, Rows(rows + rows[:1])  # Duplicates must not inflate contract counts.


SDK = SimpleNamespace(RET_OK=0, OptionType=SimpleNamespace(ALL='ALL', CALL='CALL', PUT='PUT'))


class OptionTests(unittest.TestCase):
    def test_symbols_and_calendar_months(self):
        self.assertEqual(option_symbol(' nvda '), 'US.NVDA')
        self.assertEqual(option_symbol('BRK.B'), 'US.BRK.B')
        self.assertEqual(option_symbol('hk.00700'), 'HK.00700')
        with self.assertRaises(ValueError):
            option_symbol('SH.600519')
        self.assertEqual(add_months(date(2027, 1, 31), 1), date(2027, 2, 28))
        self.assertEqual(add_months(date(2028, 1, 31), 1), date(2028, 2, 29))
        self.assertEqual(add_months(date(2026, 10, 16), 3), date(2027, 1, 16))

    def test_bad_query_is_rejected_before_sdk_calls(self):
        with self.assertRaises(ValueError):
            OptionQuery('AAPL', date(2027, 2, 1), date(2027, 1, 1))
        with self.assertRaises(ValueError):
            OptionQuery('AAPL', date(2027, 1, 1), date(2030, 1, 1))
        with self.assertRaises(ValueError):
            OptionQuery.upcoming('NVDA', start='2000-01-01')
        with self.assertRaises(ValueError):
            OptionQuery.upcoming('NVDA', months=0)

    def test_windows_preserve_inclusive_boundaries_and_never_exceed_30_days(self):
        days = ['2027-01-01', '2027-01-30', '2027-01-31', '2027-03-01', '2027-03-02']
        windows = list(chain_windows(days + [days[0]]))
        self.assertEqual(windows[0], ('2027-01-01', '2027-01-30'))
        for first, last in windows:
            self.assertLessEqual((date.fromisoformat(last) - date.fromisoformat(first)).days, 29)
        for day in days:
            self.assertEqual(sum(first <= day <= last for first, last in windows), 1)

    def test_multiple_symbols_types_filtering_deduplication_and_metadata(self):
        for code in ('US.NVDA', 'HK.00700'):
            context = Context()
            query = OptionQuery(code, date(2027, 1, 31), date(2027, 4, 30), 'PUT')
            result = OptionChainService(SDK, context, min_interval=0).query(query)
            self.assertEqual(len(result['contracts']), 4)
            self.assertEqual(len(result['expirations']), 4)
            self.assertEqual(result['end'], '2027-04-30')
            self.assertTrue(all(row['option_type'] == 'PUT' for row in result['contracts']))
            self.assertTrue(all(call[0] == code and call[3] == 'PUT' for call in context.calls))
            self.assertIn(result['timezone'], ('America/New_York', 'Asia/Hong_Kong'))
            self.assertEqual(result['contracts'][-1]['strike_time'], '2027-04-30')

    def test_empty_dates_do_not_request_chains(self):
        context = Context()
        result = OptionChainService(SDK, context).query(OptionQuery('AAPL', date(2028, 1, 1), date(2028, 4, 1)))
        self.assertEqual(result['contracts'], [])
        self.assertEqual(context.calls, [])

    def test_later_window_error_does_not_return_partial_success(self):
        context = Context()
        context.fail_at = 2
        with self.assertRaisesRegex(RuntimeError, 'permission denied'):
            OptionChainService(SDK, context, min_interval=0).query(
                OptionQuery('AAPL', date(2027, 1, 31), date(2027, 4, 30)))

    def test_cancellation_interrupts_rate_limit_wait_and_sends_no_chain(self):
        context = Context()
        service = OptionChainService(SDK, context, min_interval=10)
        service.last_chain_call = time.monotonic()
        cancel = threading.Event()
        timer = threading.Timer(.02, cancel.set)
        timer.start()
        try:
            with self.assertRaises(QueryCancelled):
                service.query(OptionQuery('AAPL', date(2027, 1, 31), date(2027, 2, 1)), cancel)
        finally:
            timer.join()
        self.assertEqual(context.calls, [])

    def test_exports_preserve_numeric_strikes_and_contract_identity(self):
        context = Context()
        result = OptionChainService(SDK, context, min_interval=0).query(
            OptionQuery('AAPL', date(2027, 1, 31), date(2027, 2, 1)))
        stream = io.StringIO()
        write_result(result, stream)
        parsed = json.loads(stream.getvalue())
        self.assertEqual(parsed['contracts'][0]['strike_price'], 100.5)
        stream = io.StringIO()
        write_result(result, stream, 'csv')
        rows = list(csv.DictReader(io.StringIO(stream.getvalue())))
        self.assertEqual(len(rows), 4)
        self.assertEqual(rows[0]['code'], result['contracts'][0]['code'])
