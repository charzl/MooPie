"""Deterministic local paper ledger. No broker execution or network access."""
import copy
from datetime import date,datetime,time,timedelta,timezone
from math import isfinite,floor
from zoneinfo import ZoneInfo
from .paper_strategies import STRATEGIES,VERSION,decide,adjusted_history
from .options import add_months

NY=ZoneInfo('America/New_York')
LIMITATIONS=[
    'Virtual long-only stock trades; not actual fills or fund replication.',
    'Fixed per-ticker trade budget; fractional shares; cash interest and taxes excluded.',
    'Slippage and fees are model assumptions, not broker charges.',
    'Cash dividends accrue on ex-date, not payment date; no withholding tax.',
    'A short observation window and a selected Watchlist do not establish statistical superiority.',
    'Vendor history can be revised; this is not a point-in-time corporate-fundamentals dataset.',
]


def number(value,name,minimum=0,strict=False):
    if isinstance(value,bool) or not isinstance(value,(int,float)) or not isfinite(value) or (value<=minimum if strict else value<minimum):
        raise ValueError('Invalid '+name)
    return float(value)


def configuration(symbols,num_clients=6,trade_notional=10000,slippage_bps=5,fee_bps=1,
                  initial_capital=500000,client_capitals=None,funding_mode='fixed'):
    if type(num_clients) is not int or not 6<=num_clients<=100: raise ValueError('Use 6–100 virtual clients, including QQQ and SPY benchmarks')
    if not symbols or len(set(symbols))!=len(symbols): raise ValueError('A nonempty unique universe is required')
    notional=number(trade_notional,'trade notional',strict=True)
    capital=number(initial_capital,'initial capital',strict=True)
    if funding_mode not in ('fixed','auto_deposit'): raise ValueError('Invalid paper funding mode')
    overrides={} if client_capitals is None else client_capitals
    ids={f'client-{i+1:03}' for i in range(num_clients)}
    if not isinstance(overrides,dict) or set(overrides)-ids: raise ValueError('Client capitals must map existing client IDs to amounts')
    overrides={key:number(value,'client initial capital',strict=True) for key,value in overrides.items()}
    slippage=number(slippage_bps,'slippage'); fee=number(fee_bps,'fee')
    if max(slippage,fee)>100: raise ValueError('Paper cost assumptions must be at most 100 bps per side')
    names=list(STRATEGIES)
    specs=[]
    for i in range(num_clients):
        strategy=names[i%len(names)]; parameters=copy.deepcopy(STRATEGIES[strategy]['parameters'])
        benchmark=strategy in ('buy_qqq','buy_spy')
        identifier=f'client-{i+1:03}'; amount=overrides.get(identifier,capital)
        specs.append(dict(id=identifier,strategy=strategy,name=STRATEGIES[strategy]['name'],parameters=parameters,
                          symbols=[parameters['symbol']] if benchmark else list(symbols),
                          initial_capital=amount,entry_notional=amount if benchmark else notional))
    return dict(version=VERSION,symbols=list(symbols),market_symbols=list(dict.fromkeys([*symbols,'US.QQQ','US.SPY'])),
                trade_notional=notional,slippage_bps=slippage,fee_bps=fee,
                initial_capital=capital,funding_mode=funding_mode,clients=specs)


def validate_inputs(payload,symbols,observed_at):
    observed=datetime.fromisoformat(observed_at)
    if observed.tzinfo is None: raise ValueError('Paper observation time requires a timezone')
    series={row['symbol']:row for row in payload['daily_series']}
    if len(series)!=len(payload['daily_series']) or set(series)!=set(symbols): raise ValueError('Paper input must cover exactly the frozen universe')
    actions={row['symbol']:row['rows'] for row in payload['actions']}
    if len(actions)!=len(payload['actions']) or set(actions)!=set(symbols): raise ValueError('Corporate-action coverage is incomplete')
    calendar=None
    for symbol,row in series.items():
        if row.get('error'): raise ValueError(symbol+': '+row['error'])
        if (row.get('interval'),row.get('adjustment'),row.get('session'))!=('1d','none','regular'):
            raise ValueError('Paper execution requires unadjusted regular-session daily bars')
        bars=row['bars']; dates=[bar['date'] for bar in bars]
        if len(bars)<253 or dates!=sorted(set(dates)) or dates!=row['calendar_dates'] or dates[-1]!=row['as_of']:
            raise ValueError(f'{symbol}: require 253+ ordered, complete and gap-free daily bars; received {len(bars)}. Choose a supported universe explicitly; no ticker was removed automatically.')
        if calendar is not None and dates!=calendar: raise ValueError('All virtual clients require identical ticker calendars')
        calendar=dates
        available=datetime.fromisoformat(row['available_at'])
        local=available.astimezone(NY)
        finalized=time(13,5) if row.get('trade_date_type')=='MORNING' else time(16,5)
        if (available.tzinfo is None or available>observed or local.date().isoformat()!=dates[-1] or local.time()<finalized):
            raise ValueError('A paper daily bar was not finalized at the observation cutoff')
        for bar in bars:
            date.fromisoformat(bar['date'])
            if bar.get('complete') is not True: raise ValueError('Incomplete paper daily bar')
            o,h,l,c=[number(bar[k],k,strict=True) for k in ('open','high','low','close')]
            number(bar['volume'],'volume')
            if not l<=min(o,c)<=max(o,c)<=h: raise ValueError('Invalid paper OHLC range')
        for action in actions[symbol]:
            date.fromisoformat(action['ex_div_date'])
            number(action['forward_adj_factorA'],'adjustment factor',strict=True)
            b=action['forward_adj_factorB']
            if isinstance(b,bool) or not isinstance(b,(int,float)) or not isfinite(b): raise ValueError('Invalid adjustment offset')
            if action.get('split_ratio') is not None: number(action['split_ratio'],'split ratio',strict=True)
            for key in ('per_cash_div','special_dividend'):
                if action.get(key) is not None: number(action[key],key)
            if any(action.get(key) not in (None,0) for key in ('per_share_div_ratio','per_share_trans_ratio','allotment_ratio','stk_spo_ratio','spin_off_ratio')):
                raise ValueError(symbol+': unsupported corporate action; paper ledger not advanced')
        if len({a['ex_div_date'] for a in actions[symbol]})!=len(actions[symbol]): raise ValueError('Duplicate corporate-action date')
    return series,actions,calendar


def _decision(client,series,actions,day,generated_at):
    universe=client.get('symbols',list(series))
    history={symbol:adjusted_history(series[symbol]['bars'],actions[symbol],day) for symbol in universe}
    plan=decide(client['strategy'],history,client,day,client['parameters'])
    plan['generated_at']=generated_at
    client['pending']=plan; client['selection']=plan['targets']; client['selection_month']=day[:7]
    return plan


def initialize(payload,config,observed_at,mode='forward',start=None):
    if mode not in ('forward','backtest'): raise ValueError('Invalid paper mode')
    series,actions,calendar=validate_inputs(payload,config.get('market_symbols',config['symbols']),observed_at)
    if config['version']!=VERSION: raise ValueError('Unsupported paper strategy version')
    if mode=='forward':
        from .market_sessions import market_session,previous_session
        session=market_session(datetime.fromisoformat(observed_at),'daily',config['symbols'])
        expected=session['session_date']
        if session['is_open']: expected=previous_session(date.fromisoformat(expected)-timedelta(days=1)).isoformat()
        if calendar[-1]!=expected: raise ValueError('Forward experiment requires the latest completed trading session')
        anchor=calendar[-1]; start_day=datetime.fromisoformat(observed_at).astimezone(NY).date().isoformat()
        generated=observed_at
    else:
        first=date.fromisoformat(start).isoformat()
        candidates=[d for d in calendar if d<first]
        if len(candidates)<253 or first>calendar[-1]: raise ValueError('Backtest start needs 253 prior sessions and a later execution session')
        anchor=candidates[-1]; start_day=first
        generated=datetime.combine(date.fromisoformat(anchor),time(16,5),NY).isoformat()
    clients=[]
    for spec in config['clients']:
        capital=number(spec['initial_capital'],'client initial capital',strict=True)
        client=dict(copy.deepcopy(spec),cash=capital,contributions=capital,
                    positions={},nav=capital,index=1.,peak=1.,max_drawdown=0.,
                    realized_pnl=0.,fees=0.,slippage=0.,closed_trades=0,wins=0,selection=[],pending=None)
        _decision(client,series,actions,anchor,generated)
        clients.append(client)
    return dict(version=VERSION,mode=mode,created_at=observed_at,start_date=start_day,last_date=anchor,
                config=copy.deepcopy(config),clients=clients,skipped_decision_dates=[],history=[])


def advance(original,payload,observed_at):
    state=copy.deepcopy(original); config=state['config']
    if state['version']!=VERSION: raise ValueError('Paper engine version changed; create a new experiment')
    series,actions,calendar=validate_inputs(payload,config.get('market_symbols',config['symbols']),observed_at)
    if calendar[-1]<state['last_date']: raise ValueError('Paper input is older than the recorded ledger')
    if state['last_date'] not in calendar: raise ValueError('History cannot bridge the recorded paper ledger')
    maps={s:{b['date']:b for b in row['bars']} for s,row in series.items()}
    dates=[d for d in calendar if d>state['last_date']]
    rows=[]; fills=[]
    for day in dates:
        open_at=datetime.combine(date.fromisoformat(day),time(9,30),NY)
        record_new=state['mode']=='backtest' or day==calendar[-1]
        if not record_new: state['skipped_decision_dates'].append(day)
        for client in state['clients']:
            previous_nav=client['nav']; deposited=0.; events=[]; execution_events=[]
            for symbol,position in client['positions'].items():
                for action in actions[symbol]:
                    if action['ex_div_date']!=day: continue
                    quantity=position['quantity']
                    dividend=quantity*((action.get('per_cash_div') or 0)+(action.get('special_dividend') or 0))
                    client['cash']+=dividend
                    position['income']=position.get('income',0)+dividend
                    ratio=action.get('split_ratio') or 1
                    position['quantity']/=ratio
                    events.append(dict(symbol=symbol,dividend=dividend,share_multiplier=1/ratio))
            open_nav=client['cash']+sum(p['quantity']*maps[s][day]['open'] for s,p in client['positions'].items())
            pending=client.get('pending')
            if pending and pending['as_of']<day and datetime.fromisoformat(pending['generated_at'])<open_at:
                targets=set(pending['targets'])
                for side,names in [('SELL',sorted(set(client['positions'])-targets)),('BUY',sorted(targets-set(client['positions'])))]:
                    for offset,symbol in enumerate(names):
                        base=maps[symbol][day]['open']; direction=1 if side=='BUY' else -1
                        price=base*(1+direction*config['slippage_bps']/10000)
                        budget=client.get('entry_notional',config['trade_notional'])
                        if side=='BUY' and config['funding_mode']=='fixed':
                            # Split scarce cash equally among new targets, including fees.
                            available=max(0,client['cash'])/(len(names)-offset)/(1+config['fee_bps']/10000)
                            if available<budget:
                                execution_events.append(dict(symbol=symbol,reason='cash_limited',
                                                             requested_notional=budget,allocated_notional=available))
                            budget=min(budget,available)
                        quantity=floor(budget/price*1e6)/1e6 if side=='BUY' else client['positions'][symbol]['quantity']
                        if side=='BUY' and quantity<=0 and config['funding_mode']=='fixed': continue
                        if quantity<=0: raise ValueError('Trade notional too small for fractional-share precision')
                        notional=quantity*price; fee=notional*config['fee_bps']/10000
                        if side=='BUY':
                            flow=max(0,notional+fee-client['cash']) if config['funding_mode']=='auto_deposit' else 0.
                            deposited+=flow
                            client['cash']+=flow-notional-fee; client['contributions']+=flow
                            client['positions'][symbol]=dict(quantity=quantity,cost=notional+fee,entry_date=day,income=0.)
                        else:
                            position=client['positions'].pop(symbol); profit=notional-fee-position['cost']+position.get('income',0)
                            client['cash']+=notional-fee; client['realized_pnl']+=profit
                            client['closed_trades']+=1; client['wins']+=profit>0
                        slippage=abs(price-base)*quantity
                        client['fees']+=fee; client['slippage']+=slippage
                        fills.append(dict(client_id=client['id'],date=day,symbol=symbol,side=side,quantity=quantity,
                                          price=price,reference_open=base,fee=fee,slippage=slippage,
                                          signal_as_of=pending['as_of'],signal_generated_at=pending['generated_at']))
                client['pending']=None
            market_value=sum(p['quantity']*maps[s][day]['close'] for s,p in client['positions'].items())
            nav=client['cash']+market_value
            client['index']*=open_nav/previous_nav * nav/(open_nav+deposited)
            client['nav']=nav; client['peak']=max(client['peak'],client['index'])
            client['max_drawdown']=min(client['max_drawdown'],client['index']/client['peak']-1)
            plan=None
            if record_new:
                generated=(datetime.combine(date.fromisoformat(day),time(16,5),NY).isoformat()
                           if state['mode']=='backtest' else observed_at)
                plan=_decision(client,series,actions,day,generated)
            rows.append(dict(client_id=client['id'],date=day,nav=nav,cash=client['cash'],contributions=client['contributions'],
                             net_pnl=nav-client['contributions'],return_pct=(client['index']-1)*100,
                             drawdown_pct=client['max_drawdown']*100,exposure_pct=market_value/nav*100,
                             deposit=deposited,fees=client['fees'],slippage=client['slippage'],
                             realized_pnl=client['realized_pnl'],closed_trades=client['closed_trades'],wins=client['wins'],
                             positions=copy.deepcopy(client['positions']),decision=plan,corporate_actions=events,
                             execution_events=execution_events))
        state['last_date']=day
    return state,rows,fills


def summarize(state,history,fills=()):
    by_client={c['id']:[] for c in state['clients']}
    for row in history: by_client[row['client_id']].append(row)
    output=[]
    for client in state['clients']:
        periods=[]
        for months in (1,3,6):
            target=add_months(date.fromisoformat(state['start_date']),months).isoformat()
            completed=[r for r in by_client[client['id']] if r['date']>=target]
            point=completed[0] if completed else None
            periods.append(dict(months=months,target_date=target,status='complete' if point else 'pending',
                                measured_date=point['date'] if point else None,
                                return_pct=point['return_pct'] if point else None,
                                drawdown_pct=point['drawdown_pct'] if point else None))
        last=by_client[client['id']][-1] if by_client[client['id']] else None
        trades=[f for f in fills if f['client_id']==client['id']]
        average_nav=sum(r['nav'] for r in by_client[client['id']])/len(by_client[client['id']]) if last else client['nav']
        output.append(dict(id=client['id'],strategy=client['strategy'],name=client.get('name',STRATEGIES[client['strategy']]['name']),
                           initial_capital=client.get('initial_capital',state['config']['initial_capital']),
                           nav=client['nav'],cash=client['cash'],contributions=client['contributions'],
                           net_pnl=client['nav']-client['contributions'],return_pct=(client['index']-1)*100,
                           drawdown_pct=client['max_drawdown']*100,closed_trades=client['closed_trades'],
                           win_rate_pct=100*client['wins']/client['closed_trades'] if client['closed_trades'] else None,
                           exposure_pct=last['exposure_pct'] if last else 0,fees=client['fees'],slippage=client['slippage'],
                           realized_pnl=client['realized_pnl'],unrealized_pnl=client['nav']-client['contributions']-client['realized_pnl'],
                           fill_count=len(trades),turnover_pct=100*sum(f['quantity']*f['price'] for f in trades)/average_nav,
                           periods=periods))
    baseline=next(c['return_pct'] for c in output if c['strategy']=='buy_hold')
    benchmarks={key:next((c['return_pct'] for c in output if c['strategy']==strategy),None)
                for key,strategy in [('qqq','buy_qqq'),('spy','buy_spy')]}
    for client in output:
        client['excess_vs_buy_hold_pct']=client['return_pct']-baseline
        for key,value in benchmarks.items(): client['excess_vs_'+key+'_pct']=client['return_pct']-value if value is not None else None
    return dict(version=state['version'],mode=state['mode'],start_date=state['start_date'],as_of=state['last_date'],
                benchmark_returns=benchmarks,
                config=state['config'],clients=output,skipped_decision_dates=state['skipped_decision_dates'],
                limitations=LIMITATIONS+(['Backtest using the currently selected universe; selection and survivorship bias are possible.']
                                         if state['mode']=='backtest' else ['Forward records only; future performance is pending.']))
