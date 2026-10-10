import importlib.util, os, pathlib, threading, unittest
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
if __name__=='__main__': unittest.main()
