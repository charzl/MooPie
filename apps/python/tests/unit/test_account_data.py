import unittest
from types import SimpleNamespace
from moopython.account_data import query_accounts
ID = 9007199254740993
class Rows:
 def __init__(self, rows): self.rows=rows
 def to_dict(self, orient): return self.rows
class AccountTests(unittest.TestCase):
 def setUp(self):
  self.closed=[]; self.calls=[]; owner=self
  class Context:
   def __init__(self, **kwargs): owner.calls.append(('context',kwargs))
   def get_acc_list(self): return 0,Rows([dict(acc_id=ID,trd_env='REAL')])
   def accinfo_query(self, **kwargs): owner.calls.append(('funds',kwargs)); return 0,Rows([dict(cash=100)])
   def position_list_query(self, **kwargs): owner.calls.append(('positions',kwargs)); return 0,Rows([])
   def close(self): owner.closed.append(True)
  self.sdk=SimpleNamespace(RET_OK=0,OpenSecTradeContext=Context,TrdMarket=SimpleNamespace(US='US'),SecurityFirm=SimpleNamespace(FUTUINC='FUTUINC'),Currency=SimpleNamespace(USD='USD'))
  self.command=dict(op='account_details',market='US',firm='FUTUINC',currency='USD',acc_id=str(ID))
 def test_selected_account_id_and_environment_remain_exact(self):
  result=query_accounts(self.sdk,'127.0.0.1',11111,self.command)
  self.assertEqual(result['acc_id'],str(ID)); self.assertEqual(result['positions'],[])
  for name,parameters in self.calls[1:]:
   self.assertEqual(parameters['acc_id'],ID); self.assertEqual(parameters['trd_env'],'REAL'); self.assertFalse(parameters['refresh_cache'])
  self.assertEqual(self.closed,[True])
 def test_unknown_account_does_not_query_assets_and_context_closes(self):
  self.command['acc_id']='99'
  with self.assertRaises(ValueError): query_accounts(self.sdk,'127.0.0.1',11111,self.command)
  self.assertEqual(len(self.calls),1); self.assertEqual(self.closed,[True])
 def test_account_list_returns_string_id_without_precision_loss(self):
  self.command['op']='accounts'
  result=query_accounts(self.sdk,'127.0.0.1',11111,self.command)
  self.assertEqual(result['accounts'][0]['acc_id'],str(ID))
 def test_position_failure_preserves_cash_and_reports_error(self):
  self.sdk.OpenSecTradeContext.position_list_query=lambda *_args,**_kwargs:(-1,'position permission denied')
  result=query_accounts(self.sdk,'127.0.0.1',11111,self.command)
  self.assertEqual(result['funds'][0]['cash'],100); self.assertEqual(result['positions'],[])
  self.assertIn('permission denied',result['errors'][0]); self.assertEqual(self.closed,[True])
 def test_history_and_cashflow_use_selected_account_and_explicit_dates(self):
  calls=[]
  self.sdk.OpenSecTradeContext.history_deal_list_query=lambda *_args,**kwargs:(calls.append(kwargs) or (0,Rows([])))
  self.sdk.OpenSecTradeContext.get_acc_cash_flow=lambda *_args,**kwargs:(calls.append(kwargs) or (0,Rows([])))
  for kind in ('history','cashflow'):
   command=dict(self.command,op='account_activity',kind=kind,start='2026-10-01',end='2026-10-10',date='2026-10-10')
   result=query_accounts(self.sdk,'127.0.0.1',11111,command)
   self.assertEqual(result['rows'],[]); self.assertEqual(calls[-1]['acc_id'],ID); self.assertEqual(calls[-1]['trd_env'],'REAL')
  self.assertEqual(calls[0]['start'],'2026-10-01'); self.assertEqual(calls[1]['clearing_date'],'2026-10-10')
 def test_crypto_category_selects_crypto_context(self):
  self.sdk.OpenCryptoTradeContext=self.sdk.OpenSecTradeContext
  result=query_accounts(self.sdk,'127.0.0.1',11111,dict(self.command,category='CRYPTO'))
  self.assertEqual(result['funds'][0]['cash'],100)
  self.assertNotIn('filter_trdmarket',self.calls[0][1])
 def test_sdk_error_closes_context(self):
  self.sdk.OpenSecTradeContext.accinfo_query=lambda *_args,**_kwargs:(-1,'test permission denied')
  with self.assertRaisesRegex(RuntimeError,'permission denied'): query_accounts(self.sdk,'127.0.0.1',11111,self.command)
  self.assertEqual(self.closed,[True])
