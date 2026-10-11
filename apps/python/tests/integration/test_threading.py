import os, socket, tempfile, time, unittest
from types import SimpleNamespace
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
from moopython.gateway import Gateway, GatewayWorker
class ThreadingTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls): cls.app=QApplication.instance() or QApplication([])
 def wait(self,predicate):
  deadline=time.monotonic()+3
  while not predicate() and time.monotonic()<deadline: self.app.processEvents(); time.sleep(.005)
  self.assertTrue(predicate())
 def test_slow_sdk_does_not_block_ui_and_shutdown_closes_context(self):
  order=[]; closed=[]
  class Context:
   def __init__(self,**kwargs): time.sleep(.2)
   def set_handler(self,handler): pass
   def get_global_state(self): return 0,{}
   def close(self): closed.append(True)
  sdk=SimpleNamespace(OpenQuoteContext=Context,RET_OK=0,StockQuoteHandlerBase=object,CurKlineHandlerBase=object)
  gateway=Gateway(sdk_factory=lambda:sdk)
  gateway.event.connect(lambda token,kind,data:order.append(kind))
  try:
   QTimer.singleShot(20,lambda:order.append('ui-heartbeat'))
   gateway.send('connect','test',host='127.0.0.1',port=11111,symbols=[])
   self.wait(lambda:'connected' in order)
   self.assertLess(order.index('ui-heartbeat'),order.index('connected'))
  finally:
   gateway.shutdown(); self.wait(lambda:not gateway.thread.isRunning())
  self.assertEqual(closed,[True])
 def test_closed_port_reports_connection_failure_without_context(self):
  socket_probe=socket.socket(); socket_probe.bind(('127.0.0.1',0)); port=socket_probe.getsockname()[1]; socket_probe.close()
  worker=GatewayWorker(); events=[]
  worker.event.connect(lambda token,kind,data:events.append(kind))
  worker.execute(dict(op='connect',token='test',host='127.0.0.1',port=port,symbols=[]))
  self.assertIn('connection_error',events); self.assertIsNone(worker.ctx)
 def test_large_watchlist_bounds_subscriptions_and_keeps_selected_quote(self):
  active=set()
  class Rows:
   def to_dict(self,orient): return []
  class Context:
   def subscribe(self,codes,types,**kwargs): active.update(codes); return 0,None
   def unsubscribe(self,codes,types): active.difference_update(codes); return 0,None
   def get_stock_quote(self,codes): return 0,Rows()
  worker=GatewayWorker(); worker.ctx=Context()
  worker.sdk=SimpleNamespace(RET_OK=0,SubType=SimpleNamespace(QUOTE='QUOTE'))
  worker.refresh([f'US.TEST{i}' for i in range(45)])
  self.assertEqual(len(active),30); self.assertIn('US.TEST44',active)
  worker.refresh(['US.TEST0'])
  self.assertEqual(len(active),30); self.assertIn('US.TEST0',active)
 def test_unsubscribe_failure_does_not_exceed_quote_limit(self):
  subscriptions=[]
  class Context:
   def unsubscribe(self,*args): return -1,'test subscription error'
   def subscribe(self,*args,**kwargs): subscriptions.append(True); return 0,None
  worker=GatewayWorker(); worker.ctx=Context(); worker.quote_subscriptions=[f'US.TEST{i}' for i in range(30)]
  worker.sdk=SimpleNamespace(RET_OK=0,SubType=SimpleNamespace(QUOTE='QUOTE'))
  worker.refresh(['US.NEW'])
  self.assertEqual(subscriptions,[]); self.assertEqual(len(worker.quote_subscriptions),30)
if __name__=='__main__': unittest.main()
