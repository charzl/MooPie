import os, tempfile, time, unittest
from types import SimpleNamespace
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from PySide6.QtCore import QSettings, Qt
from PySide6.QtWidgets import QApplication
from moopython.ui import MainWindow
from moopython.pages import OptionsPage, ObservePage, MarketPage, snapshot_rows
from moopython.gateway import GatewayWorker

class Rows:
    def __init__(self,rows): self.rows=rows
    def to_dict(self,orient): return self.rows

class PageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.app=QApplication.instance() or QApplication([])
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.window=MainWindow(QSettings(self.temp.name+'/settings.ini',QSettings.Format.IniFormat)); self.commands=[]
        self.window.gateway.command.connect(self.commands.append)
    def tearDown(self):
        self.window.close(); deadline=time.monotonic()+3
        while not self.window.closed and time.monotonic()<deadline: self.app.processEvents(); time.sleep(.005)
        self.assertTrue(self.window.closed); self.temp.cleanup()
    def response(self,page,op,**data): page.receive(self.window.token,'user_data',dict(op=op,request=page.request,**data))
    def test_navigation_opens_real_pages_offline_and_brand_has_no_framework_label(self):
        self.assertEqual(self.window.windowTitle(),'MooPie')
        for name,kind in [('期权',OptionsPage),('观察',ObservePage),('市场',MarketPage)]:
            self.window.nav_buttons[name].click()
            self.assertIsInstance(self.window.pages.currentWidget(),kind)
            self.assertTrue(self.window.nav_buttons[name].isChecked())
            self.assertIn('连接 OpenD',self.window.pages.currentWidget().status.text())
        self.window.show_charts(); self.assertEqual(self.window.pages.currentIndex(),0)
    def test_option_expirations_chain_quotes_and_connection_changes(self):
        self.window.mode='live'; self.window.show_data_page('期权'); page=self.window.data_pages['期权']
        self.assertEqual(page.underlying.text(),'PLTR'); self.assertEqual(self.commands[-1]['code'],'US.PLTR')
        self.response(page,'option_dates',rows=[dict(strike_time='2026-10-16')])
        self.assertEqual(self.commands[-1]['op'],'option_chain'); self.assertEqual(self.commands[-1]['date'],'2026-10-16')
        self.response(page,'option_chain',rows=[dict(code='US.AAPL261016C200000',option_type='CALL',strike_price=200),dict(code='US.AAPL261016P200000',option_type='PUT',strike_price=200)])
        self.assertEqual(page.tables['CALL'].rowCount(),1); self.assertEqual(page.tables['PUT'].rowCount(),1)
        self.assertEqual(page.tables['CALL'].item(0,0).text(),'AAPL261016C200000')
        page.tables['PUT'].selectRow(0); page.load_quote()
        self.assertEqual(self.commands[-1]['codes'],['US.AAPL261016P200000'])
        self.response(page,'snapshots',rows=[dict(code='US.AAPL261016P200000',last_price=3.125,option_delta=-.5,update_time='test')])
        self.assertEqual(page.quote_table.rowCount(),11)
        self.window.token='new'; page.check_session(); self.assertEqual(page.quote_table.rowCount(),0); self.assertEqual(page.tables['CALL'].rowCount(),0)
    def test_observation_filters_group_paginates_and_opens_chart(self):
        self.window.mode='live'; self.window.show_data_page('观察'); page=self.window.data_pages['观察']
        page.group_rows=[dict(code='US.AAPL',name='Apple')]
        self.response(page,'snapshots',rows=[dict(code='US.AAPL',name='Apple',last_price=101,prev_close_price=100)])
        self.assertEqual(page.rows[0]['change'],1); self.assertAlmostEqual(page.rows[0]['change_pct'],1)
        self.assertEqual(page.table.item(0,0).text(),'AAPL')
        self.assertEqual(page.table.item(0,0).data(Qt.ItemDataRole.UserRole),'US.AAPL')
        page.search.setText('apple'); self.assertEqual(page.table.rowCount(),1)
        page.market.setCurrentText('港股'); self.assertEqual(page.table.rowCount(),0)
        page.market.setCurrentText('全部'); page.open_row(page.table,0); self.assertEqual(self.window.pages.currentIndex(),0)
        before=list(self.window.state.symbols);self.window.open_chart_code('SG.BAD')
        self.assertEqual(self.window.state.symbols,before)
        page.group_rows=[dict(code=f'US.TEST{i}') for i in range(205)]; page.page=0; page.move_page(1)
        self.assertEqual(len(self.commands[-1]['codes']),5); self.assertEqual(self.commands[-1]['codes'][0],'US.TEST200')
    def test_market_error_never_fills_synthetic_prices_and_map_renders(self):
        self.window.mode='live'; self.window.show_data_page('市场'); page=self.window.data_pages['市场']
        self.response(page,'snapshots',rows=[dict(code='US.SPY',last_price=101,prev_close_price=100,update_time='test')])
        self.assertEqual(page.table.rowCount(),1); self.assertEqual(page.cards.count(),3)
        self.window.show(); self.app.processEvents(); self.assertFalse(page.map.grab().isNull())
        page.load(); page.receive(self.window.token,'user_data_error',dict(request=page.request,error='permission denied'))
        self.assertEqual(page.table.rowCount(),0); self.assertEqual(page.cards.count(),0); self.assertIn('permission denied',page.status.text())
    def test_accounts_automatically_load_cash_and_official_profit_fields(self):
        self.window.mode='live'; self.window.show_accounts(); page=self.window.account_page
        self.response(page,'accounts',accounts=[dict(acc_id='9007199254740993',trd_env='REAL',acc_type='CASH')])
        self.assertEqual(self.commands[-1]['op'],'account_details'); self.assertEqual(self.commands[-1]['acc_id'],'9007199254740993')
        self.response(page,'account_details',currency='USD',funds=[dict(total_assets=1200,cash=100,power=150,avl_withdrawal_cash=90,realized_pl=-20,unrealized_pl=30)],positions=[])
        self.assertIn('现金：100.00',page.cash_summary.text()); self.assertIn('已实现盈亏: -20.00',page.summary.text())
        self.assertIn('未实现盈亏: 30.00',page.summary.text())
        page.tabs.setCurrentIndex(3); self.assertEqual(self.commands[-1]['op'],'account_activity'); self.assertEqual(self.commands[-1]['kind'],'history')
        self.response(page,'account_activity',kind='history',rows=[dict(code='US.AAPL',trd_side='SELL',qty=2,price=100)])
        self.assertEqual(page.activity_tables['history'].rowCount(),1)
        self.assertEqual(page.activity_tables['history'].item(0,0).text(),'AAPL')
        self.assertIn('现金：100.00',page.cash_summary.text())
    def test_cloud_groups_load_automatically_without_replacing_local_watchlist(self):
        self.window.mode='live'; before=list(self.window.state.symbols)
        self.window.show_data_page('观察');page=self.window.data_pages['观察']
        self.assertEqual(self.commands[-1]['op'],'watchlist_groups')
        self.response(page,'watchlist_groups',rows=[dict(group_name='Cloud test')])
        self.assertEqual(self.commands[-1]['op'],'watchlist');self.assertEqual(self.commands[-1]['group'],'Cloud test')
        self.response(page,'watchlist',rows=[dict(code='US.AAPL',name='Apple')])
        self.assertEqual(self.commands[-1]['codes'],['US.AAPL'])
        self.response(page,'snapshots',rows=[dict(code='US.AAPL',last_price=100)])
        self.assertEqual(page.table.rowCount(),1);self.assertIn('云端',page.status.text())
        self.assertEqual(self.window.state.symbols,before)
        self.assertNotIn('自定义',self.window.nav_buttons);self.assertNotIn('发现',self.window.nav_buttons)

    def test_cloud_watchlist_remains_visible_when_some_markets_have_no_quote_permission(self):
        self.window.mode='live';self.window.show_data_page('观察');page=self.window.data_pages['观察']
        self.response(page,'watchlist_groups',rows=[dict(group_name='Cloud test')])
        self.response(page,'watchlist',rows=[dict(code='US.AAPL',name='Apple'),dict(code='SH.000001',name='Index')])
        self.assertEqual(self.commands[-1]['op'],'market_snapshots')
        self.response(page,'market_snapshots',rows=[dict(code='US.AAPL',last_price=100)],errors=[dict(market='SH',codes=['SH.000001'],error='CN permission denied')])
        self.assertEqual(page.table.rowCount(),2)
        missing=next(row for row in page.rows if row['code']=='SH.000001')
        self.assertEqual(missing['name'],'Index');self.assertNotIn('last_price',missing);self.assertIn('permission denied',missing['quote_status'])

    def test_partial_market_response_keeps_permitted_quotes_and_marks_missing_cards(self):
        self.window.settings.setValue('selected_markets',['美股','港股','沪深'])
        self.window.mode='live';self.window.show_data_page('市场');page=self.window.data_pages['市场']
        self.assertEqual(self.commands[-1]['op'],'market_snapshots')
        self.response(page,'market_snapshots',rows=[dict(code='US.SPY',last_price=100,prev_close_price=99)],errors=[dict(market='SH',codes=['SH.000001'],error='CN index permission denied')])
        self.assertEqual(page.table.rowCount(),1);self.assertEqual(page.cards.count(),7)
        self.assertIn('CN index permission denied',page.status.text());self.assertEqual(len(page.map.rows),1)

    def test_market_only_queries_selected_markets_and_remembers_selection(self):
        self.window.mode='live';self.window.show_data_page('市场');page=self.window.data_pages['市场']
        self.assertTrue(all(code.startswith('US.') for code in self.commands[-1]['codes']))
        self.response(page,'market_snapshots',rows=[])
        page.market_checks['港股'].setChecked(True)
        self.assertEqual(set(code.split('.')[0] for code in self.commands[-1]['codes']),{'US','HK'})
        self.response(page,'market_snapshots',rows=[])
        page.market_checks['美股'].setChecked(False)
        self.assertEqual(self.commands[-1]['codes'],['HK.800000'])
        self.window.settings.sync()
        saved=QSettings(self.temp.name+'/settings.ini',QSettings.Format.IniFormat)
        self.assertEqual(saved.value('selected_markets'),['港股'])
        restored=MarketPage(self.window)
        self.assertEqual([code for code,name in restored.selected_symbols()],['HK.800000'])
        restored.cleanup();restored.deleteLater()

    def test_empty_market_selection_sends_no_queries_and_ignores_old_response(self):
        self.window.mode='live';self.window.show_data_page('市场');page=self.window.data_pages['市场']
        old=page.request;count=len(self.commands)
        page.market_checks['美股'].setChecked(False)
        self.assertEqual(len(self.commands),count);self.assertIn('请选择',page.status.text())
        page.receive(self.window.token,'user_data',dict(op='market_snapshots',request=old,rows=[dict(code='US.SPY',last_price=100)]))
        self.assertEqual(page.table.rowCount(),0);self.assertEqual(page.cards.count(),0)

    def test_missing_close_does_not_create_a_change_percentage(self):
        self.assertNotIn('change_pct',snapshot_rows([dict(last_price=100,prev_close_price=0)])[0])
        self.assertNotIn('change_pct',snapshot_rows([dict(last_price=float('nan'),prev_close_price=100)])[0])
    def test_gateway_uses_readonly_sdk_calls_and_rejects_oversized_snapshot(self):
        calls=[]
        class Context:
            def get_option_expiration_date(self,code): calls.append(('dates',code)); return 0,Rows([dict(strike_time='2026-10-16')])
            def get_option_chain(self,code,**kwargs): calls.append(('chain',code,kwargs)); return 0,Rows([])
            def get_market_snapshot(self,codes): calls.append(('snapshots',codes)); return -1,'permission denied'
        worker=GatewayWorker(); worker.ctx=Context(); worker.sdk=SimpleNamespace(RET_OK=0); worker.token='test'; events=[]
        worker.event.connect(lambda token,kind,data:events.append((kind,data)))
        worker.execute(dict(op='option_dates',token='test',request='1',code='US.AAPL'))
        worker.execute(dict(op='option_chain',token='test',request='2',code='US.AAPL',date='2026-10-16'))
        worker.execute(dict(op='snapshots',token='test',request='3',codes=['US.AAPL']))
        worker.execute(dict(op='snapshots',token='test',request='4',codes=[f'US.TEST{i}' for i in range(201)]))
        self.assertEqual(calls[1][2],dict(start='2026-10-16',end='2026-10-16'))
        self.assertEqual(len(calls),3); self.assertEqual(events[-1][0],'user_data_error'); self.assertIn('200',events[-1][1]['error'])
        self.assertIn('permission denied',events[-2][1]['error'])
