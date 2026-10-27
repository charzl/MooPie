from contextlib import contextmanager
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from moopython.order_book import (BOOK_BUCKET_RANGE_FRACTION, auto_bucket_width, quote_reference,
                                  read_order_book, visible_price_buckets, visible_price_zones,
                                  visible_value_ratio)
from moopython.stock_overview import build_overview


class StockOverviewTests(unittest.TestCase):
    def test_price_buckets_use_thirty_percent_range_and_keep_outer_volume(self):
        self.assertEqual(BOOK_BUCKET_RANGE_FRACTION, 0.30)
        self.assertEqual(auto_bucket_width(100), 5)
        self.assertEqual(auto_bucket_width(1000), 50)
        book=dict(status='ok', bids=[dict(price=499, volume=100), dict(price=699, volume=10),
                                     dict(price=700, volume=20), dict(price=749, volume=30),
                                     dict(price=750, volume=40)],
                  asks=[dict(price=1299, volume=50), dict(price=1300, volume=60),
                        dict(price=1500, volume=70)])
        buckets=visible_price_buckets(book, 50, 1000)
        self.assertEqual((buckets['lower'],buckets['upper']), (700,1300))
        self.assertEqual([(x['kind'],x['volume']) for x in buckets['bids']],
                         [('normal',40),('normal',50),('below',110)])
        self.assertEqual([(x['kind'],x['volume']) for x in buckets['asks']],
                         [('normal',50),('above',130)])
        self.assertEqual(sum(x['volume'] for x in buckets['bids']),200)
        self.assertEqual(sum(x['notional'] for x in buckets['asks']),
                         sum(row['price']*row['volume'] for row in book['asks']))
        finer=visible_price_buckets(book, 10, 1000)
        self.assertEqual(finer['width'],10)
        self.assertEqual(sum(x['volume'] for x in finer['bids']),200)

    def test_visible_value_ratio_uses_price_times_shares_across_all_returned_levels(self):
        book=dict(status='ok', bids=[dict(price=90, volume=1000), dict(price=80, volume=100)],
                  asks=[dict(price=110, volume=900), dict(price=120, volume=50)])
        ratio=visible_value_ratio(book)
        self.assertEqual((ratio['bid_value'], ratio['ask_value']), (98000, 105000))
        self.assertAlmostEqual(ratio['bid_to_ask'], 98000/105000)
        self.assertAlmostEqual(ratio['bid_share']+ratio['ask_share'], 1)
        self.assertEqual(visible_value_ratio(dict(status='ok', bids=book['bids'], asks=[]))['status'], 'insufficient')

    def test_order_book_uses_session_price_without_replacing_regular_last_price(self):
        quote = dict(last_price=216, after_price=216.4288, pre_price=211,
                     update_time='2026-10-26 17:45:57.947')
        self.assertEqual(quote_reference(quote), dict(price=216.4288, field='after_price',
                                                      session='after', update_time=quote['update_time']))
        self.assertEqual(quote['last_price'], 216)
        self.assertEqual(quote_reference(dict(quote, update_time='2026-10-26 10:00:00'))['price'], 216)
        self.assertEqual(quote_reference(dict(quote, update_time='2026-10-26 08:00:00'))['price'], 211)
        self.assertEqual(quote_reference(dict(quote, after_price=None))['price'], 216)

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

    def test_order_book_groups_neighboring_visible_prices_without_merging_distant_levels(self):
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
        self.assertEqual(result['depth'], 60)
        self.assertEqual((result['returned_bids'], result['returned_asks']), (3, 2))
        self.assertEqual(result['status'],'ok')
        self.assertIsNone(result['bid_server_time'])
        zones=visible_price_zones(result,100.01)
        self.assertEqual(len(zones['bids']),1)
        self.assertEqual((zones['bids'][0]['low'],zones['bids'][0]['high']), (99.98,100))
        self.assertEqual(zones['bids'][0]['volume'],240)
        self.assertAlmostEqual(zones['bids'][0]['notional'],
                               100*10 + 99.99*200 + 99.98*30)
        self.assertEqual(len(zones['asks']),1)
        self.assertEqual(zones['asks'][0]['volume'],200)
        distant=dict(result,bids=[dict(price=100,volume=10),dict(price=99.99,volume=20),
                                  dict(price=99.50,volume=100)])
        self.assertEqual([zone['volume'] for zone in visible_price_zones(distant,100.10)['bids']], [30,100])
        self.assertEqual([zone['volume'] for zone in visible_price_zones(distant,99.40)['bids']], [100,30])


if __name__ == '__main__': unittest.main()
