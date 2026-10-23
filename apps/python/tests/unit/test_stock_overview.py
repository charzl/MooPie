from contextlib import contextmanager
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from moopython.order_book import order_book_html, read_order_book
from moopython.stock_overview import build_overview


class StockOverviewTests(unittest.TestCase):
    def test_overview_preserves_watchlist_order_and_marks_missing_quotes(self):
        result = build_overview(['US.AAPL', 'US.MISS'], dict(collected_at='2026-10-22T20:00:00+00:00',
            rows=[dict(code='US.AAPL',name='Provider Apple',last_price=110,prev_close_price=100,
                       update_time='2026-10-22 16:00:00')]),
            {'US.AAPL':dict(name='Apple',security_type='STOCK'), 'US.MISS':dict(name='Missing',security_type='ETF')})
        self.assertEqual([row['symbol'] for row in result['rows']], ['US.AAPL','US.MISS'])
        self.assertEqual(result['rows'][0]['name'],'Apple')
        self.assertNotIn('price_signals', result)
        self.assertAlmostEqual(result['rows'][0]['change_pct'],10)
        self.assertIsNone(result['rows'][1]['price'])

    def test_order_book_reports_largest_visible_levels_and_missing_server_time(self):
        class Context:
            def subscribe(self, codes, kinds, subscribe_push=False):
                self.subscribed=(codes,kinds,subscribe_push)
                return 0,None
            def get_order_book(self, code, num=10):
                return 0,dict(code=code,svr_recv_time_bid='',svr_recv_time_ask='',
                    Bid=[(100,10,1,{}),(99.99,200,2,{}),(99.98,30,1,{})],
                    Ask=[(100.01,50,1,{}),(100.02,150,2,{})])
        context=Context()
        sdk=SimpleNamespace(RET_OK=0,SubType=SimpleNamespace(ORDER_BOOK='book'))
        @contextmanager
        def connection(**_options): yield SimpleNamespace(sdk=sdk,context=context)
        with patch('moopython.order_book.opend_connection',connection):
            result=read_order_book('AAPL')
        self.assertEqual(context.subscribed,(['US.AAPL'],['book'],False))
        self.assertEqual(result['status'],'ok')
        self.assertIsNone(result['bid_server_time'])
        text=order_book_html(result)
        self.assertLess(text.index('$99.99（200 股）'),text.index('$99.98（30 股）'))
        self.assertIn('无法核对交易所更新时间',text)


if __name__ == '__main__': unittest.main()
