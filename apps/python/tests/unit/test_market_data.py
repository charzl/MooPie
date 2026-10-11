import unittest
from types import SimpleNamespace
from moopython.market_data import query_market_snapshots

class Rows:
    def __init__(self,rows):self.rows=rows
    def to_dict(self,orient):return self.rows

class MarketDataTests(unittest.TestCase):
    def test_cn_index_permission_denial_keeps_us_and_hk_quotes(self):
        calls=[]
        class Context:
            def get_market_snapshot(self,codes):
                calls.append(codes)
                if codes[0].startswith(('SH.','SZ.')):return -1,'CN MarketIndixes permission denied'
                return 0,Rows([dict(code=code,last_price=100) for code in codes])
        result=query_market_snapshots(SimpleNamespace(RET_OK=0),Context(),['US.SPY','HK.800000','SH.000001','US.QQQ','SZ.399001','US.SPY'])
        self.assertEqual({row['code'] for row in result['rows']},{'US.SPY','US.QQQ','HK.800000'})
        self.assertEqual(calls,[['US.SPY','US.QQQ'],['HK.800000'],['SH.000001'],['SZ.399001']])
        self.assertEqual({error['market'] for error in result['errors']},{'SH','SZ'})
    def test_index_denial_does_not_hide_equities_in_the_same_market(self):
        class Context:
            def get_market_snapshot(self,codes):
                if 'SH.000001' in codes:return -1,'index permission denied'
                return 0,Rows([dict(code=code,last_price=100) for code in codes])
        result=query_market_snapshots(SimpleNamespace(RET_OK=0),Context(),['SH.000001','SH.600519'])
        self.assertEqual([row['code'] for row in result['rows']],['SH.600519'])
        self.assertEqual(result['errors'][0]['codes'],['SH.000001'])
    def test_empty_response_and_connection_error_are_explicit(self):
        class Context:
            def get_market_snapshot(self,codes):
                if codes[0].startswith('US.'):raise RuntimeError('connection lost')
                return 0,Rows([])
        result=query_market_snapshots(SimpleNamespace(RET_OK=0),Context(),['US.SPY','HK.800000'])
        self.assertEqual(result['rows'],[]);self.assertEqual(len(result['errors']),2)
        self.assertIn('connection lost',result['errors'][0]['error'])
        self.assertEqual(result['errors'][1]['codes'],['HK.800000'])
