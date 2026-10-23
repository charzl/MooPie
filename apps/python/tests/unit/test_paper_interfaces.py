"""Raw-data collection, cache reuse and packaged/headless CLI dispatch."""
from contextlib import contextmanager
import copy
from datetime import datetime
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from moopython.market_collection import MarketDataService
from moopython.market_repository import market_data_connection
from moopython.market_store import SnapshotStore
from test_paper_trading import fixture,OBSERVED

ROOT=Path(__file__).resolve().parents[4]


class Rows:
    def __init__(self,rows): self.rows=rows
    def to_dict(self,orient): return self.rows


class PaperInterfaceTests(unittest.TestCase):
    def test_collection_requests_unadjusted_prices_and_corporate_actions(self):
        calls=[]
        sdk=SimpleNamespace(RET_OK=0,Market=SimpleNamespace(US='US'),KLType=SimpleNamespace(K_DAY='DAY'),
                            AuType=SimpleNamespace(NONE='NONE',QFQ='QFQ'),Session=SimpleNamespace(RTH='RTH'))
        def history(code,**kwargs):
            calls.append((code,kwargs))
            return 0,Rows([dict(time_key='2026-10-16 00:00:00',open=100,high=101,low=99,close=100,volume=1)]),None
        context=SimpleNamespace(request_trading_days=lambda *a,**kw:(0,[dict(time='2026-10-16',trade_date_type='WHOLE')]),
                                request_history_kline=history,get_rehab=lambda code:(0,Rows([dict(ex_div_date='2026-09-01',split_ratio=float('nan'))])))
        with patch('moopython.paper_data.datetime') as clock:
            clock.now.return_value=datetime.fromisoformat(OBSERVED)
            result=MarketDataService(sdk,context).paper_inputs(['TEST'])
        self.assertEqual(calls[0][1]['autype'],'NONE')
        self.assertEqual(calls[0][1]['session'],'RTH')
        self.assertIsNone(result['actions'][0]['rows'][0]['split_ratio'])
        self.assertEqual(result['daily_series'][0]['adjustment'],'none')

    def test_raw_paper_batches_reuse_individual_members_offline(self):
        data=fixture(); data['symbols']=['US.TEST','US.OTHER']
        for key in ('daily_series','actions'):
            data[key]=[r for r in data[key] if r['symbol']=='US.TEST']
            other=copy.deepcopy(data[key][0]); other['symbol']='US.OTHER'; data[key].append(other)
        calls=[]
        @contextmanager
        def connection(**kwargs):
            calls.append(kwargs)
            yield SimpleNamespace(paper_inputs=lambda **kw:data)
        with tempfile.TemporaryDirectory() as root:
            store=SnapshotStore(Path(root)/'market.sqlite3')
            options=dict(store=store,connection=connection,clock=lambda:datetime.fromisoformat(OBSERVED))
            with market_data_connection(**options,refresh=True) as api: api.paper_inputs(['TEST','OTHER'])
            with market_data_connection(**options,update=True) as api: result=api.paper_inputs(['OTHER'])
            self.assertEqual(len(calls),1)
            self.assertEqual(result['data_access']['source'],'database')
            self.assertEqual([r['symbol'] for r in result['actions']],['US.OTHER'])
            self.assertEqual([r['symbol'] for r in result['daily_series']],['US.OTHER'])

    def test_main_dispatch_runs_offline_without_gui_and_cannot_update_a_backtest(self):
        with tempfile.TemporaryDirectory(prefix='paper CLI ') as root:
            path=Path(root); data=fixture(); file=path/'input.json'; file.write_text(json.dumps(data))
            output=path/'result.json'; env=dict(os.environ,MOOMOO_DB_PATH=str(path/'ledger.sqlite3'),PYTHONPATH=str(ROOT/'apps/python'))
            command=[sys.executable,str(ROOT/'apps/python/main.py'),'paper']
            capitals=path/'capitals.json'; capitals.write_text(json.dumps({'client-005':750000}))
            run=subprocess.run(command+['backtest','--symbols','TEST','--input',str(file),'--start',data['daily_series'][0]['bars'][254]['date'],
                '--initial-capital','500000','--client-capitals',str(capitals),'--output',str(output)],env=env,capture_output=True,timeout=30)
            self.assertEqual(run.returncode,0,run.stderr.decode())
            report=json.loads(output.read_text()); self.assertTrue(report['fills'])
            self.assertEqual(report['config']['funding_mode'],'fixed')
            self.assertEqual(report['clients'][0]['initial_capital'],500000)
            self.assertEqual(report['clients'][4]['initial_capital'],750000)
            self.assertTrue(all(r['deposit']==0 for r in report['history'][6:]))
            run=subprocess.run(command+['update',str(report['id']),'--input',str(file),'--output',str(output)],env=env,capture_output=True,timeout=30)
            self.assertEqual(run.returncode,1)
            self.assertIn('Historical experiments are fixed',json.loads(output.read_text())['error'])


if __name__=='__main__': unittest.main()
