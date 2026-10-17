from contextlib import contextmanager, redirect_stdout
from datetime import datetime
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from moopython.market_collection import MarketDataService, opend_connection, us_symbols
from moopython.market_mcp import OpenDReader, register_tools


class Rows:
    def __init__(self, rows): self.rows = rows
    def to_dict(self, orient): return self.rows


class CollectionApiTests(unittest.TestCase):
    def test_snapshots_normalize_nan_preserve_missing_and_no_qt(self):
        context = SimpleNamespace(get_market_snapshot=lambda codes: (0, Rows([dict(code=codes[0], option_delta=float('nan'))])))
        service = MarketDataService(SimpleNamespace(RET_OK=0), context)
        result = service.snapshots(['avgo', 'nvda'])
        self.assertEqual(result['codes'], ['US.AVGO', 'US.NVDA'])
        self.assertEqual(result['missing_codes'], ['US.NVDA'])
        self.assertIsNone(result['rows'][0]['option_delta'])
        json.dumps(result, allow_nan=False)

    def test_bad_input_does_not_reach_broker(self):
        for value in ([], ['HK.00700'], ['AAPL']*201):
            with self.assertRaises(ValueError): us_symbols(value, maximum=200)
        with self.assertRaises(ValueError):
            with opend_connection(host='example.com'): pass
        with self.assertRaises(ValueError):
            with opend_connection(port=0): pass
        service = MarketDataService(None, None)
        with self.assertRaises(ValueError): service.earnings_calendar('2026-10-01', '2026-10-09')
        with self.assertRaises(ValueError): service.daily_bars(['AAPL'], cutoff='2026-10-16T15:00:00')
        with self.assertRaises(ValueError): service.daily_bars(['AAPL'], cutoff='2999-10-16T15:00:00+00:00')
        with self.assertRaises(ValueError): service.collect_put_dataset(['AAPL'], months=0)

    def test_basic_info_preserves_authoritative_type_and_delisting(self):
        calls = []
        def basic(market, code_list):
            calls.append((market, code_list))
            return 0, Rows([dict(code='US.AVGO', name='Broadcom', stock_type='STOCK', delisting=False),
                            dict(code='US.INVALID', name='Unknown stock.', stock_type='N/A', delisting=True)])
        service = MarketDataService(SimpleNamespace(RET_OK=0, Market=SimpleNamespace(US='US')), SimpleNamespace(get_stock_basicinfo=basic))
        result = service.basic_info(['AVGO', 'INVALID'])
        self.assertEqual(calls, [('US', ['US.AVGO', 'US.INVALID'])])
        self.assertFalse(result['rows'][0]['delisting'])
        self.assertEqual(result['rows'][1]['stock_type'], 'N/A')
        self.assertEqual(result['missing_codes'], [])

    def test_directory_collects_both_security_types_and_propagates_partial_failure(self):
        calls = []
        def basic(market, stock_type):
            calls.append((market,stock_type))
            return 0, Rows([dict(code='US.TEST',stock_type=stock_type)])
        sdk = SimpleNamespace(RET_OK=0,Market=SimpleNamespace(US='US'),SecurityType=SimpleNamespace(STOCK='STOCK',ETF='ETF'))
        context = SimpleNamespace(get_stock_basicinfo=basic)
        service = MarketDataService(sdk,context)
        result = service.security_directory()
        self.assertEqual(calls,[('US','STOCK'),('US','ETF')])
        self.assertEqual(len(result['rows']),2)
        context.get_stock_basicinfo = lambda market,stock_type: ((-1,'permission denied') if stock_type=='ETF' else (0,Rows([])))
        with self.assertRaisesRegex(RuntimeError,'permission denied'): service.security_directory()

    def test_calendar_failure_propagates_and_empty_result_means_unknown(self):
        context = SimpleNamespace(get_earnings_calendar=lambda *a, **k: (0, Rows([])))
        service = MarketDataService(SimpleNamespace(RET_OK=0, Market=SimpleNamespace(US='US')), context)
        result = service.earnings_calendar('2026-10-16', '2026-10-22')
        self.assertEqual(result['rows'], [])
        self.assertIn('unknown', result['note'])
        context.get_earnings_calendar = lambda *a, **k: (-1, 'permission denied')
        with self.assertRaisesRegex(RuntimeError, 'permission denied'):
            service.earnings_calendar('2026-10-16', '2026-10-22')

    def test_reader_closes_context_redirects_logs_and_allows_only_reads(self):
        closed = []
        @contextmanager
        def connection(**kwargs):
            print('SDK CONNECT LOG')
            try: yield SimpleNamespace(snapshots=lambda codes: dict(codes=codes, collected_at='2026-10-16T18:00:00+00:00'))
            finally: closed.append(True)
        stream = io.StringIO()
        from moopython.market_store import SnapshotStore
        with tempfile.TemporaryDirectory() as temp, redirect_stdout(stream):
            reader = OpenDReader(connection=connection, store=SnapshotStore(Path(temp)/'market.sqlite3'),
                                 clock=lambda: datetime.fromisoformat('2026-10-16T18:00:00+00:00'))
            result = reader('snapshots', codes=['US.AAPL'])
            self.assertEqual(result['codes'], ['US.AAPL'])
            self.assertEqual(result['data_access']['source'], 'OpenD')
        self.assertEqual(stream.getvalue(), '')
        self.assertEqual(closed, [True])
        with self.assertRaises(ValueError): reader('place_order')

    def test_adapter_only_delegates_to_same_python_api(self):
        class Server:
            def __init__(self): self.tools = {}
            def tool(self, **kwargs):
                def add(function): self.tools[function.__name__] = function; return function
                return add
        calls = []
        def read(operation, **parameters):
            calls.append((operation, parameters)); return {'operation': operation, 'parameters': parameters}
        server = register_tools(Server(), read)
        self.assertEqual(set(server.tools), {'get_market_snapshots', 'get_option_chain', 'get_daily_bars', 'get_earnings_calendar'})
        server.tools['get_market_snapshots'](['US.AAPL'])
        server.tools['get_option_chain']('AVGO', months=3)
        server.tools['get_daily_bars'](['NVDA'])
        server.tools['get_earnings_calendar']('2026-10-16', '2026-10-22')
        self.assertEqual([c[0] for c in calls], ['snapshots', 'option_chain', 'daily_bars', 'earnings_calendar'])
        self.assertEqual(calls[1][1]['months'], 3)


if __name__ == '__main__': unittest.main()
