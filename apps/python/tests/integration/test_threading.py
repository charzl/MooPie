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
if __name__=='__main__': unittest.main()
