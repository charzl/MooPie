import os, tempfile, time, unittest
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication
from moopython.ui import MainWindow
class UIIntegrationTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls): cls.app=QApplication.instance() or QApplication([])
 def setUp(self):
  self.directory=tempfile.TemporaryDirectory(); self.settings=QSettings(self.directory.name+'/settings.ini',QSettings.Format.IniFormat)
  self.window=MainWindow(self.settings); self.window.show(); self.app.processEvents()
 def wait(self,predicate,timeout=3):
  deadline=time.monotonic()+timeout
  while not predicate() and time.monotonic()<deadline: self.app.processEvents(); time.sleep(.01)
  self.assertTrue(predicate())
 def tearDown(self):
  self.window.close(); self.wait(lambda:self.window.closed)
  self.assertFalse(self.window.gateway.thread.isRunning()); self.directory.cleanup()
 def test_search_selection_and_chart_render(self):
  self.window.search.setText('AAPL'); self.app.processEvents(); self.assertEqual(self.window.table_model.rows,['US.AAPL'])
  self.window.select_symbol('US.AAPL'); self.assertEqual(len(self.window.chart.bars),180)
  self.assertFalse(self.window.grab().toImage().isNull())
 def test_old_session_and_wrong_chart_request_are_ignored(self):
  original=dict(self.window.state.quotes)
  self.window.on_event('old-session','quotes',[dict(code='US.AAPL',last_price=999)])
  self.assertEqual(self.window.state.quotes,original)
  bars=list(self.window.chart.bars)
  self.window.on_event(self.window.token,'candles',dict(request='stale-chart',rows=[]))
  self.assertEqual(self.window.chart.bars,bars)
 def test_quote_batch_and_same_timestamp_kline_update(self):
  self.window.mode='live'; self.window.selected='US.AAPL'
  self.window.on_event(self.window.token,'quotes',[dict(code='US.AAPL',last_price=111,prev_close_price=100)])
  self.wait(lambda:self.window.state.quotes['US.AAPL'].price==111)
  rows=[dict(code='US.AAPL',k_type='K_DAY',time_key='2026-01-01',open=100,high=120,low=95,close=110,volume=5)]
  self.window.chart.set_bars([],'日K'); self.window.on_event(self.window.token,'candle_push',rows)
  rows[0]['close']=112; self.window.on_event(self.window.token,'candle_push',rows)
  self.assertEqual(len(self.window.chart.bars),1); self.assertEqual(self.window.chart.bars[0].close,112)
 def test_connection_failure_returns_to_disconnected(self):
  self.window.on_event(self.window.token,'connection_error','test: OpenD not running')
  self.assertEqual(self.window.mode,'disconnected'); self.assertFalse(self.window.health_timer.isActive())
if __name__=='__main__': unittest.main()
