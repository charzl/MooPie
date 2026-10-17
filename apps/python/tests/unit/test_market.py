import unittest
from moopython.market import Candle, Quote, symbol, display_symbol, parse_candles, merge_candles, averages, demo_candles

class MarketTests(unittest.TestCase):
 def test_symbols(self):
  self.assertEqual(symbol(' hk.00700 '), 'HK.00700')
  self.assertEqual(symbol('US.BRK.B'), 'US.BRK.B')
  self.assertEqual(symbol(' pltr '),'US.PLTR')
  self.assertEqual(symbol('AAPL'),'US.AAPL')
  self.assertEqual(symbol('BRK.B'),'US.BRK.B')
  for value in ('00700','US.bad symbol','https://example.com'):
   with self.assertRaises(ValueError): symbol(value)
  with self.assertRaises(ValueError): symbol('SG.BAD',allow_short=False)
 def test_display_codes_preserve_market_and_share_class(self):
  self.assertEqual(display_symbol('US.PLTR'),'PLTR')
  self.assertEqual(display_symbol('US.BRK.B'),'BRK.B')
  self.assertEqual(display_symbol('HK.00700'),'HK.00700')
  self.assertIsNone(display_symbol(None))
 def test_quote_nan_and_int64(self):
  quote=Quote.from_row(dict(code='US.AAPL',last_price=110,prev_close_price=100,volume='123456789',after_price=float('nan')))
  self.assertEqual(quote.percent,10)
  self.assertEqual(quote.volume,123456789)
  self.assertIsNone(quote.after)
 def test_candle_push_replaces_latest_and_keeps_order(self):
  bars=parse_candles([dict(time_key='2026-01-01',open=1,high=3,low=1,close=2,volume=4),dict(time_key='bad',open=float('nan'))])
  updated=Candle('2026-01-01',1,4,1,3,8)
  next_bar=Candle('2026-01-02',3,4,2,4,10)
  result=merge_candles(bars,[next_bar,updated])
  self.assertEqual(result,[updated,next_bar])
  self.assertEqual(averages(result,2),[None,3.5])
 def test_demo_is_repeatable_and_ohlc_valid(self):
  bars=demo_candles('US.AAPL'); self.assertEqual(bars,demo_candles('US.AAPL'))
  for bar in bars:
   self.assertLessEqual(bar.low,min(bar.open,bar.close)); self.assertGreaterEqual(bar.high,max(bar.open,bar.close))

if __name__=='__main__': unittest.main()
