import os, tempfile, time, unittest
from types import SimpleNamespace
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from PySide6.QtCore import QSettings, QTimer
from PySide6.QtWidgets import QApplication
from moopython.ui import MainWindow
from moopython.account_ui import WatchlistDialog, AccountsDialog
from moopython.gateway import Gateway
class Rows:
 def __init__(self,rows): self.rows=rows
 def to_dict(self,orient): return self.rows
class UserDataTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls): cls.app=QApplication.instance() or QApplication([])
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(); self.window=MainWindow(QSettings(self.temp.name+'/settings.ini',QSettings.Format.IniFormat))
  self.window.mode='live'; self.dialogs=[]
 def wait(self,predicate):
  deadline=time.monotonic()+4
  while not predicate() and time.monotonic()<deadline: self.app.processEvents(); time.sleep(.005)
  self.assertTrue(predicate())
 def tearDown(self):
  for dialog in self.dialogs: dialog.reject()
  self.window.close(); self.wait(lambda:self.window.closed); self.temp.cleanup()
 def test_group_results_and_stale_responses(self):
  dialog=WatchlistDialog(self.window); self.dialogs.append(dialog)
  dialog.receive(self.window.token,'user_data',dict(op='watchlist_groups',request=dialog.request,rows=[dict(group_name='我的自选')]))
  self.assertEqual(dialog.groups.currentText(),'我的自选')
  dialog.load_group(); request=dialog.request
  dialog.receive(self.window.token,'user_data',dict(op='watchlist',request='old',rows=[dict(code='US.BAD')]))
  self.assertEqual(dialog.table.rowCount(),0)
  dialog.receive(self.window.token,'user_data',dict(op='watchlist',request=request,rows=[dict(code='US.AAPL',name='Apple')]))
  self.assertEqual(dialog.table.rowCount(),1); self.assertTrue(dialog.apply.isEnabled())
  self.window.token='changed'; dialog.check_session()
  self.assertEqual(dialog.table.rowCount(),0); self.assertFalse(dialog.apply.isEnabled())
 def test_large_watchlist_import_persists_names_and_filters(self):
  rows=[dict(code=f'US.TEST{i}',name=f'公司{i}') for i in range(45)]
  rows += [rows[0],dict(code='SG.BAD',name='Unsupported')]
  self.window.import_watchlist(rows,'自选')
  self.assertEqual(len(self.window.state.symbols),45)
  self.window.search.setText('公司44'); self.assertEqual(self.window.table_model.rows,['US.TEST44'])
  self.assertEqual(len(self.window.settings.value('symbols')),45)
  self.assertEqual(self.window.state.names['US.TEST44'],'公司44')
  self.window.import_watchlist([], 'empty')
  self.assertEqual(len(self.window.state.symbols),45)
 def test_account_is_embedded_in_main_window_and_navigation_returns_to_chart(self):
  self.window.show_accounts()
  self.assertIs(self.window.pages.currentWidget(),self.window.account_page)
  self.assertTrue(self.window.nav_buttons['账户'].isChecked())
  self.assertTrue(self.window.account_page.tabs.isTabEnabled(2))
  self.window.show_charts(); self.assertEqual(self.window.pages.currentIndex(),0)
  self.assertFalse(self.window.nav_buttons['账户'].isChecked())
 def test_account_display_clears_on_selection_change_and_error(self):
  dialog=AccountsDialog(self.window); self.dialogs.append(dialog)
  dialog.receive(self.window.token,'user_data',dict(op='accounts',request=dialog.request,accounts=[dict(acc_id='9007199254740993',trd_env='REAL')]))
  self.assertEqual(dialog.accounts.currentData(),'9007199254740993')
  dialog.load_details()
  dialog.receive(self.window.token,'user_data',dict(op='account_details',request=dialog.request,currency='USD',funds=[dict(cash=100)],positions=[]))
  self.assertIn('100.00',dialog.summary.text()); self.assertIn('—',dialog.summary.text())
  dialog.currency.setCurrentText('HKD'); self.assertNotIn('100.00',dialog.summary.text())
  dialog.load_details()
  dialog.receive(self.window.token,'user_data_error',dict(request=dialog.request,error='test permission denied'))
  self.assertIn('permission denied',dialog.status.text()); self.assertEqual(dialog.table.rowCount(),0)
 def test_slow_watchlist_read_runs_off_gui_thread(self):
  events=[]
  class Context:
   def __init__(self,**kwargs): pass
   def set_handler(self,handler): pass
   def get_global_state(self): return 0,{}
   def get_user_security_group(self): time.sleep(.2); return 0,Rows([dict(group_name='Test')])
   def close(self): pass
  sdk=SimpleNamespace(RET_OK=0,OpenQuoteContext=Context,StockQuoteHandlerBase=object,CurKlineHandlerBase=object)
  gateway=Gateway(sdk_factory=lambda:sdk)
  gateway.event.connect(lambda token,kind,data:events.append(kind))
  try:
   gateway.send('connect','test',host='127.0.0.1',port=11111,symbols=[]); self.wait(lambda:'connected' in events)
   gateway.send('watchlist_groups','test',request='test'); QTimer.singleShot(20,lambda:events.append('heartbeat'))
   self.wait(lambda:'user_data' in events); self.assertLess(events.index('heartbeat'),events.index('user_data'))
  finally:
   gateway.shutdown(); self.wait(lambda:not gateway.thread.isRunning())
