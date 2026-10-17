"""Known-answer ledger paths: timing, funding, actions, durability and replay."""
import copy
from datetime import date,datetime,timedelta,time
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from moopython.paper_engine import NY,configuration,initialize,advance,summarize
from moopython.paper_store import PaperStore
from moopython.market_store import SnapshotStore
from moopython.paper_strategies import adjusted_history,decide,STRATEGIES


def fixture(count=380):
    end=date(2026,10,16); days=[]; current=end
    while len(days)<count:
        if current.weekday()<5: days.append(current.isoformat())
        current-=timedelta(days=1)
    days.reverse()
    bars=[dict(date=day,open=100+i,close=100+i,low=99+i,high=101+i,volume=1000,complete=True) for i,day in enumerate(days)]
    result=dict(fetched_at='2026-10-17T17:00:00+00:00',daily_series=[dict(symbol='US.TEST',interval='1d',adjustment='none',
        session='regular',as_of=days[-1],calendar_dates=days,available_at=days[-1]+'T16:05:00-04:00',
        trade_date_type='WHOLE',bars=bars)],actions=[dict(symbol='US.TEST',rows=[])])
    for symbol in ('US.QQQ','US.SPY'):
        row=copy.deepcopy(result['daily_series'][0]); row['symbol']=symbol
        result['daily_series'].append(row); result['actions'].append(dict(symbol=symbol,rows=[]))
    return result


def clipped(payload,count):
    result=copy.deepcopy(payload); row=result['daily_series'][0]
    row['bars']=row['bars'][:count]; row['calendar_dates']=row['calendar_dates'][:count]
    row['as_of']=row['calendar_dates'][-1]; row['available_at']=row['as_of']+'T16:05:00-04:00'
    return result


OBSERVED='2026-10-17T17:00:00+00:00'


class PaperTradingTests(unittest.TestCase):
    def test_replay_executes_only_after_signal_and_is_deterministic(self):
        data=fixture(); config=configuration(['US.TEST'],slippage_bps=0,fee_bps=0)
        start=data['daily_series'][0]['bars'][254]['date']
        initial=initialize(data,config,OBSERVED,'backtest',start)
        before=copy.deepcopy((initial,data))
        state,rows,fills=advance(initial,data,OBSERVED)
        self.assertEqual((initial,data),before)
        self.assertEqual((state,rows,fills),advance(initial,data,OBSERVED))
        self.assertTrue(fills)
        for fill in fills:
            self.assertLess(fill['signal_as_of'],fill['date'])
            self.assertLess(datetime.fromisoformat(fill['signal_generated_at']),datetime.combine(date.fromisoformat(fill['date']),time(9,30),NY))
        baseline=next(c for c in state['clients'] if c['strategy']=='buy_hold')
        first=data['daily_series'][0]['bars'][254]['open']; last=data['daily_series'][0]['bars'][-1]['close']
        self.assertAlmostEqual((baseline['index']-1)*100,(last/first-1)*100,places=5)

    def test_forward_initialization_does_not_backdate_any_fill_or_future_result(self):
        data=fixture(); state=initialize(data,configuration(['US.TEST']),OBSERVED)
        after,rows,fills=advance(state,data,OBSERVED)
        self.assertEqual(rows,[]); self.assertEqual(fills,[])
        self.assertTrue(all(not c['positions'] for c in state['clients']))
        report=summarize(after,rows)
        self.assertTrue(all(p['status']=='pending' for c in report['clients'] for p in c['periods']))

    def test_costs_reduce_return_and_cash_injections_are_not_profit(self):
        data=fixture(); start=data['daily_series'][0]['bars'][254]['date']
        config=configuration(['US.TEST'],slippage_bps=5,fee_bps=1); config['initial_capital']=100
        initial=initialize(data,config,OBSERVED,'backtest',start)
        state,rows,fills=advance(initial,data,OBSERVED)
        client=next(c for c in state['clients'] if c['strategy']=='buy_hold')
        baseline=[r for r in rows if r['client_id']==client['id']]
        self.assertGreater(baseline[0]['deposit'],9000)
        self.assertAlmostEqual(baseline[0]['net_pnl'],-client['fees']-client['slippage'],places=5)
        self.assertLess(baseline[0]['return_pct'],0)
        self.assertAlmostEqual(client['nav']-client['contributions'],baseline[-1]['net_pnl'])

    def test_splits_and_dividends_preserve_nav_and_do_not_make_future_signals_leak(self):
        data=fixture(260); start=data['daily_series'][0]['bars'][254]['date']
        day=data['daily_series'][0]['bars'][255]['date']
        action=dict(ex_div_date=day,split_ratio=.5,per_cash_div=2,forward_adj_factorA=.5,forward_adj_factorB=-1)
        data['actions'][0]['rows']=[action]
        original=copy.deepcopy(data['daily_series'][0]['bars'])
        for bar in data['daily_series'][0]['bars'][255:]:
            for field in ('open','close','low','high'): bar[field]=(bar[field]-2)/2
        config=configuration(['US.TEST'],slippage_bps=0,fee_bps=0)
        state,rows,_=advance(initialize(data,config,OBSERVED,'backtest',start),data,OBSERVED)
        baseline=next(c for c in state['clients'] if c['strategy']=='buy_hold')
        value=[r for r in rows if r['client_id']==baseline['id'] and r['date']==day][0]
        quantity=10000/original[254]['open']
        self.assertAlmostEqual(value['positions']['US.TEST']['quantity'],2*quantity,places=5)
        self.assertAlmostEqual(value['nav'],quantity*original[255]['close'],places=4)
        before=original[254]['date']
        adjusted=adjusted_history(data['daily_series'][0]['bars'],[action],before)
        self.assertEqual(adjusted[-1]['close'],original[254]['close'])

    def test_forward_gap_marks_missed_decisions_without_inventing_old_signals(self):
        data=fixture(260); start=data['daily_series'][0]['bars'][254]['date']
        state=initialize(data,configuration(['US.TEST']),OBSERVED,'backtest',start)
        state['mode']='forward'
        state['clients'][0]['pending']['generated_at']=OBSERVED
        after,rows,fills=advance(state,data,OBSERVED)
        self.assertTrue(after['skipped_decision_dates'])
        self.assertFalse(any(f['client_id']=='client-001' for f in fills))
        decisions=[r['decision'] for r in rows if r['decision']]
        self.assertTrue(all(d['as_of']==data['daily_series'][0]['as_of'] and d['generated_at']==OBSERVED for d in decisions))

    def test_invalid_partial_future_and_adjusted_execution_data_are_rejected(self):
        data=fixture(); config=configuration(['US.TEST'])
        for mutate in (lambda d:d['daily_series'][0].update(adjustment='qfq'),
                       lambda d:d['daily_series'][0]['bars'][-1].update(complete=False),
                       lambda d:d.update(actions=[]),
                       lambda d:d['daily_series'][0].update(available_at='2027-01-01T16:05:00-05:00')):
            bad=copy.deepcopy(data); mutate(bad)
            with self.assertRaises(ValueError): initialize(bad,config,OBSERVED)

    def test_store_idempotency_audit_and_market_cleanup_preserve_paper_records(self):
        data=fixture(); start=data['daily_series'][0]['bars'][254]['date']
        with tempfile.TemporaryDirectory() as root:
            market=SnapshotStore(Path(root)/'market.sqlite3'); store=PaperStore(market)
            created=store.create('Synthetic replay',data,configuration(['US.TEST']),OBSERVED,'backtest',start)
            updated=store.update(created['id'],data,OBSERVED)
            self.assertGreater(updated['new_fills'],0)
            again=store.update(created['id'],data,OBSERVED)
            self.assertEqual(again['new_fills'],0); self.assertEqual(again['new_valuations'],0)
            self.assertEqual(again['fills'],updated['fills'])
            self.assertEqual(store.audit_input(1),data)
            market.cleanup(1,now=datetime(2026,10,20,tzinfo=NY))
            self.assertEqual(store.report(created['id'])['fills'],updated['fills'])
            self.assertEqual(store.audit_input(1),data)

    def test_duplicate_clients_reproduce_results_and_unknown_parameters_fail_early(self):
        data=fixture(); config=configuration(['US.TEST'],12)
        start=data['daily_series'][0]['bars'][254]['date']
        state,rows,_=advance(initialize(data,config,OBSERVED,'backtest',start),data,OBSERVED)
        self.assertEqual(state['clients'][0]['nav'],state['clients'][6]['nav'])
        self.assertEqual(state['clients'][0]['positions'],state['clients'][6]['positions'])
        with self.assertRaises(ValueError): configuration(['US.TEST'],5)

    def test_periods_require_an_observed_session_and_future_prices_cannot_change_a_decision(self):
        data=fixture(); config=configuration(['US.TEST'])
        start=data['daily_series'][0]['bars'][254]['date']
        initial=initialize(data,config,OBSERVED,'backtest',start)
        changed=copy.deepcopy(data)
        for bar in changed['daily_series'][0]['bars'][254:]:
            for key in ('open','high','low','close'): bar[key]*=2
        self.assertEqual(initial,initialize(changed,config,OBSERVED,'backtest',start))
        state,rows,fills=advance(initial,data,OBSERVED)
        report=summarize(state,rows,fills)
        for client in report['clients']:
            self.assertEqual([p['status'] for p in client['periods']],['complete','complete','pending'])
            self.assertIsNone(client['periods'][2]['return_pct'])
        baseline=next(c for c in report['clients'] if c['strategy']=='buy_hold')
        self.assertEqual(baseline['fill_count'],1)
        self.assertGreater(baseline['turnover_pct'],0)

    def test_failure_rolls_back_all_experiment_records(self):
        data=fixture()
        with tempfile.TemporaryDirectory() as root:
            store=PaperStore(SnapshotStore(Path(root)/'market.sqlite3'))
            with patch.object(store,'_records',side_effect=RuntimeError('Injected ledger failure')):
                with self.assertRaisesRegex(RuntimeError,'Injected'):
                    store.create('Must roll back',data,configuration(['US.TEST']),OBSERVED)
            self.assertEqual(store.list(),[])
            with store.store.connect() as db:
                for table in ('paper_clients','paper_inputs','paper_valuations','paper_fills'):
                    self.assertEqual(db.execute('SELECT COUNT(*) FROM '+table).fetchone()[0],0)

    def test_reversal_holding_limit_counts_the_entry_session(self):
        bars=fixture(260)['daily_series'][0]['bars']
        for i,bar in enumerate(bars): bar['close']=100 if i<255 else 100-(i-255)
        histories={'US.TEST':bars}; day=bars[-1]['date']
        client={'positions':{'US.TEST':{'entry_date':bars[-4]['date']}}}
        parameters=STRATEGIES['reversal_5d']['parameters']
        self.assertEqual(decide('reversal_5d',histories,client,day,parameters)['targets'],['US.TEST'])
        client['positions']['US.TEST']['entry_date']=bars[-5]['date']
        self.assertEqual(decide('reversal_5d',histories,client,day,parameters)['targets'],[])

    def test_etf_benchmarks_are_mandatory_fully_funded_and_outside_stock_selection(self):
        data=fixture()
        # Two-stock strategy pool; ETF prices deliberately fall as stocks rise.
        stock=copy.deepcopy(data['daily_series'][0]); stock['symbol']='US.OTHER'
        data['daily_series'].append(stock); data['actions'].append(dict(symbol='US.OTHER',rows=[]))
        for row in data['daily_series']:
            if row['symbol'] not in ('US.QQQ','US.SPY'): continue
            for i,bar in enumerate(row['bars']):
                price=1000-i
                bar.update(open=price,close=price,low=price-1,high=price+1)
        config=configuration(['US.TEST','US.OTHER'],slippage_bps=0,fee_bps=0)
        self.assertEqual(len(config['clients']),6)
        self.assertEqual(config['symbols'],['US.TEST','US.OTHER'])
        self.assertEqual(set(config['market_symbols']),{'US.TEST','US.OTHER','US.QQQ','US.SPY'})
        start=data['daily_series'][0]['bars'][254]['date']
        state,rows,fills=advance(initialize(data,config,OBSERVED,'backtest',start),data,OBSERVED)
        for strategy,symbol in [('buy_qqq','US.QQQ'),('buy_spy','US.SPY')]:
            client=next(c for c in state['clients'] if c['strategy']==strategy)
            self.assertEqual(set(client['positions']),{symbol})
            self.assertLess(client['cash'],.001)
            trade=next(f for f in fills if f['client_id']==client['id'])
            self.assertAlmostEqual(trade['quantity']*trade['price'],20000,places=3)
        for client in state['clients'][:4]: self.assertFalse({'US.QQQ','US.SPY'} & set(client['positions']))
        report=summarize(state,rows,fills)
        for client in report['clients']:
            self.assertAlmostEqual(client['excess_vs_qqq_pct'],client['return_pct']-report['benchmark_returns']['qqq'])
            self.assertAlmostEqual(client['excess_vs_spy_pct'],client['return_pct']-report['benchmark_returns']['spy'])

    def test_missing_benchmark_prices_stop_the_entire_experiment(self):
        data=fixture(); data['daily_series']=[r for r in data['daily_series'] if r['symbol']!='US.SPY']
        with self.assertRaisesRegex(ValueError,'frozen universe'):
            initialize(data,configuration(['US.TEST']),OBSERVED)


if __name__=='__main__': unittest.main()
