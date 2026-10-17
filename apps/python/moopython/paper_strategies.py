"""Research-inspired, long-only equity strategies; independent of Put scoring."""
VERSION='1.1.0'
STRATEGIES={
    'trend_200d':dict(name='200日趋势',parameters=dict(period=200),
                    source='https://doi.org/10.3905/jwm.2007.674809'),
    'momentum_12_1':dict(name='12–1个月动量',parameters=dict(lookback=252,skip=21,top=2),
                       source='https://doi.org/10.1111/j.1540-6261.1993.tb04702.x'),
    'reversal_5d':dict(name='趋势中短期反转',parameters=dict(trend_period=200,lookback=5,minimum_drop=.03,holding_days=5),
                     source='https://www.nber.org/papers/w2533'),
    'buy_hold':dict(name='等额买入持有基线',parameters={},source=None),
    'buy_qqq':dict(name='QQQ 买入持有基线',parameters=dict(symbol='US.QQQ'),
                   source='https://www.invesco.com/qqq-etf/en/home.html'),
    'buy_spy':dict(name='SPY 大盘买入持有基线',parameters=dict(symbol='US.SPY'),
                   source='https://www.ssga.com/us/en/individual/etfs/state-street-spdr-sp-500-etf-trust-spy'),
}


def adjusted_history(bars,actions,day):
    """Apply only actions effective by this decision date, never future events."""
    applicable=sorted((a for a in actions if a['ex_div_date']<=day),key=lambda a:a['ex_div_date'])
    result=[]
    for bar in bars:
        if bar['date']>day: break
        value=bar['close']
        for action in applicable:
            if bar['date']<action['ex_div_date']:
                value=value*action['forward_adj_factorA']+action['forward_adj_factorB']
        if value<=0: raise ValueError('Corporate-action adjustment produced a nonpositive historical price')
        result.append(dict(date=bar['date'],close=value))
    return result


def decide(strategy,histories,client,day,parameters):
    """Return a target set and evidence; the engine decides when it can execute."""
    evidence={}; eligible=[]
    for symbol,history in histories.items():
        prices=[row['close'] for row in history]
        last=prices[-1]
        if strategy=='trend_200d':
            period=parameters['period']; average=sum(prices[-period:])/period
            evidence[symbol]=dict(close=last,ma=average,buy_above=average,exit_at_or_below=average)
            if last>average: eligible.append((symbol,last/average-1))
        elif strategy=='momentum_12_1':
            momentum=prices[-1-parameters['skip']]/prices[-1-parameters['lookback']]-1
            evidence[symbol]=dict(momentum_12_1=momentum,close=last,
                                 entry_condition='Positive momentum and top rank; exit when no longer selected')
            if momentum>0: eligible.append((symbol,momentum))
        elif strategy=='reversal_5d':
            period=parameters['trend_period']; lookback=parameters['lookback']
            long_average=sum(prices[-period:])/period; mean=sum(prices[-lookback:])/lookback
            change=last/prices[-1-lookback]-1
            evidence[symbol]=dict(close=last,ma200=long_average,return_5d=change,
                                 recovery_reference=mean,maximum_holding_sessions=parameters['holding_days'])
            if last>long_average and change<=-parameters['minimum_drop']: eligible.append((symbol,-change))
        elif strategy in ('buy_hold','buy_qqq','buy_spy'):
            evidence[symbol]=dict(close=last,entry_condition='Buy once, then hold')
            eligible.append((symbol,0))
        else: raise ValueError('Unknown paper strategy: '+str(strategy))
    ordered=[symbol for symbol,_ in sorted(eligible,key=lambda row:(-row[1],row[0]))]
    if strategy=='momentum_12_1':
        # Rebalance on the first observed completed session of each new month.
        targets=client['selection'] if client.get('selection_month')==day[:7] else ordered[:parameters['top']]
    elif strategy=='reversal_5d':
        targets=[]
        for symbol,position in client['positions'].items():
            age=sum(row['date']>=position['entry_date'] for row in histories[symbol])
            if age<parameters['holding_days'] and evidence[symbol]['close']<evidence[symbol]['recovery_reference']:
                targets.append(symbol)
        if not client['positions']: targets=ordered[:1]
    else: targets=ordered
    return dict(strategy=strategy,version=VERSION,as_of=day,targets=sorted(targets),evidence=evidence,
                execution='Next regular-session open after the recorded decision time')
