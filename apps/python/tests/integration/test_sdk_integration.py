import importlib.util, json, os, pathlib, subprocess, sys, threading, unittest
from datetime import date
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from PySide6.QtWidgets import QApplication
import moomoo
path=pathlib.Path(__file__).resolve().parents[4]/'tests/support/mock_opend.py'
spec=importlib.util.spec_from_file_location('mock_opend',path); mock=importlib.util.module_from_spec(spec); spec.loader.exec_module(mock)
class SDKIntegrationTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls): cls.app=QApplication.instance() or QApplication([])
 def setUp(self):
  self.server=mock.Server().start(); self.ctx=moomoo.OpenQuoteContext(host='127.0.0.1',port=self.server.server_address[1])
 def tearDown(self): self.ctx.close(); self.server.close()
 def test_official_sdk_reads_watchlist_and_account_without_trade_operations(self):
  from moopython.account_data import query_accounts
  ret,groups=self.ctx.get_user_security_group(); self.assertEqual(ret,moomoo.RET_OK,str(groups))
  self.assertEqual(groups.iloc[0]['group_name'],'My watchlist')
  ret,stocks=self.ctx.get_user_security('My watchlist'); self.assertEqual(ret,moomoo.RET_OK,str(stocks))
  self.assertEqual(stocks.iloc[0]['code'],'US.AAPL')
  command=dict(op='account_details',market='US',firm='FUTUINC',currency='USD',acc_id='9007199254740993')
  result=query_accounts(moomoo,'127.0.0.1',self.server.server_address[1],command)
  self.assertEqual(result['acc_id'],'9007199254740993')
  self.assertEqual(result['funds'][0]['cash'],100)
  self.assertEqual(result['positions'][0]['code'],'US.AAPL')
  self.assertNotIn(2005,self.server.protocols); self.assertNotIn(2202,self.server.protocols)
 def test_official_sdk_handshake_quote_kline_push_and_reconnect(self):
  ret,state=self.ctx.get_global_state(); self.assertEqual(ret,moomoo.RET_OK); self.assertTrue(state['qot_logined'])
  event=threading.Event(); pushed=[]
  class Handler(moomoo.StockQuoteHandlerBase):
   def on_recv_rsp(handler,response):
    ret,data=super().on_recv_rsp(response)
    if ret==moomoo.RET_OK: pushed.extend(data.to_dict('records')); event.set()
    return ret,data
  self.ctx.set_handler(Handler())
  ret,data=self.ctx.subscribe(['US.AAPL'],[moomoo.SubType.QUOTE,moomoo.SubType.K_DAY]); self.assertEqual(ret,moomoo.RET_OK,str(data))
  ret,data=self.ctx.get_stock_quote(['US.AAPL']); self.assertEqual(ret,moomoo.RET_OK,str(data))
  self.assertEqual(data.iloc[0]['last_price'],110); self.assertEqual(data.iloc[0]['volume'],123456789)
  self.assertTrue(event.wait(3)); self.assertEqual(pushed[0]['last_price'],111)
  ret,data=self.ctx.get_cur_kline('US.AAPL',200); self.assertEqual(ret,moomoo.RET_OK,str(data)); self.assertEqual(data.iloc[0]['close'],110)
  self.ctx.close(); self.ctx=moomoo.OpenQuoteContext(host='127.0.0.1',port=self.server.server_address[1])
  ret,_=self.ctx.get_stock_quote(['US.AAPL']); self.assertEqual(ret,moomoo.RET_OK)
 def test_worker_surfaces_entitlement_error(self):
  from moopython.gateway import GatewayWorker
  self.server.reject=True; events=[]
  worker=GatewayWorker(sdk_factory=lambda:moomoo); worker.event.connect(lambda token,kind,data:events.append((kind,data)))
  try:
   worker.execute(dict(op='connect',token='session',host='127.0.0.1',port=self.server.server_address[1],symbols=['US.AAPL']))
   worker.execute(dict(op='chart',token='session',code='US.AAPL',period='日K',request='chart1'))
   self.assertTrue(any(kind=='chart_error' and 'mock entitlement denied' in str(data) for kind,data in events))
  finally: worker.close_context()
 def test_official_sdk_queries_option_windows_and_preserves_symbol_type_and_strikes(self):
  from moopython.options import OptionQuery, OptionChainService
  first,last=self.server.option_expirations
  query=OptionQuery('US.NVDA',date.fromisoformat(first),date.fromisoformat(last),'PUT')
  result=OptionChainService(moomoo,self.ctx,min_interval=0).query(query)
  self.assertEqual(len(result['contracts']),2)
  self.assertEqual(result['expirations'],[first,last])
  self.assertTrue(all(row['stock_owner']=='US.NVDA' and row['option_type']=='PUT' and row['strike_price']==100 for row in result['contracts']))
  self.assertEqual(self.server.option_requests,[(first,first,2),(last,last,2)])
  self.assertNotIn(2202,self.server.protocols)
 def test_official_sdk_option_entitlement_failure_is_reported(self):
  from moopython.options import OptionQuery, OptionChainService
  self.server.reject=True
  with self.assertRaisesRegex(RuntimeError,'mock option entitlement denied'):
   OptionChainService(moomoo,self.ctx,min_interval=0).query(OptionQuery('AAPL',*(date.fromisoformat(day) for day in self.server.option_expirations)))
 def test_cli_stdout_is_json_and_errors_return_nonzero(self):
  first=self.server.option_expirations[0]
  base=[sys.executable,'-m','moopython.options_cli','NVDA','--port',str(self.server.server_address[1]),'--start',first,'--end',first]
  result=subprocess.run(base,capture_output=True,text=True,timeout=15)
  self.assertEqual(result.returncode,0,result.stderr)
  parsed=json.loads(result.stdout)
  self.assertEqual(parsed['symbol'],'US.NVDA'); self.assertEqual(len(parsed['contracts']),2)
  self.server.reject=True
  failed=subprocess.run(base,capture_output=True,text=True,timeout=15)
  self.assertNotEqual(failed.returncode,0)
  self.assertEqual(failed.stdout,'')
  self.assertIn('mock option entitlement denied',failed.stderr)
if __name__=='__main__': unittest.main()
