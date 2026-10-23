"""Profit-taking indicator for a standard cash-secured short put.

Prices are per share; capital is strike * 100 for one contract. Calendar days,
constant collateral, zero fees/interest and zero risk adjustment are explicit
assumptions. This compares maximum remaining return with the entry benchmark,
not expected return or an optimal trading decision.
"""
from datetime import date
import math

VERSION = '1.1.0'


def _number(value, name, *, zero=False):
    if isinstance(value,bool): raise ValueError(name+' must be a finite number')
    try: result=float(value)
    except (TypeError,ValueError,OverflowError) as error:
        raise ValueError(name+' must be a finite number') from error
    if not math.isfinite(result) or (result<0 if zero else result<=0):
        raise ValueError(name+' must be '+('nonnegative' if zero else 'positive')+' and finite')
    return result


def _day(value):
    if type(value) is date: return value
    if not isinstance(value,str): raise ValueError('Dates must use YYYY-MM-DD')
    try: result=date.fromisoformat(value)
    except ValueError as error: raise ValueError('Dates must use YYYY-MM-DD') from error
    if result.isoformat()!=value: raise ValueError('Dates must use YYYY-MM-DD')
    return result


def put_efficiency(*, opening_premium, buyback_price, strike, opened_on, expires_on, as_of,
                   exit_threshold_pct=None):
    opening=_number(opening_premium,'opening_premium')
    buyback=_number(buyback_price,'buyback_price',zero=True)
    strike=_number(strike,'strike')
    threshold=(_number(exit_threshold_pct,'exit_threshold_pct')
               if exit_threshold_pct is not None else None)
    opened,expiry,today=map(_day,(opened_on,expires_on,as_of))
    original=(expiry-opened).days
    if original<=0: raise ValueError('Expiration must be after opening')
    if today<opened: raise ValueError('Assessment date must not precede opening')
    remaining=max(0,(expiry-today).days)
    elapsed=(today-opened).days
    entry_rate=opening/strike/original*100
    remaining_rate=buyback/strike/remaining*100 if remaining else None
    retention=(buyback/opening)*(original/remaining)*100 if remaining else None
    if remaining==0: signal='expired'
    elif elapsed==0: signal='same_day'
    elif buyback>=opening: signal='not_profitable'
    elif threshold is None: signal='observe'
    elif retention<threshold and not math.isclose(retention,threshold,rel_tol=1e-12): signal='review_close'
    else: signal='hold'
    triggered=(signal=='review_close') if signal in ('review_close','hold') else None
    values=dict(opening_daily_return_pct=entry_rate,remaining_daily_return_pct=remaining_rate,
                retention_pct=retention,profit_capture_pct=(opening-buyback)/opening*100,
                time_elapsed_pct=elapsed/original*100)
    if any(value is not None and not math.isfinite(value) for value in values.values()):
        raise ValueError('Inputs exceed supported calculation range')
    return dict(schema=1,indicator='short_put_efficiency',version=VERSION,signal=signal,
        configuration=dict(exit_threshold_pct=threshold),exit_triggered=triggered,
        suggested_action='buy_to_close' if triggered else None,
        benchmark_pct=100,original_days=original,remaining_days=remaining,elapsed_days=elapsed,
        dates=dict(opened_on=opened.isoformat(),expires_on=expiry.isoformat(),as_of=today.isoformat()),
        inputs=dict(opening_premium=opening,buyback_price=buyback,strike=strike),
        assumptions=dict(capital_basis='strike_times_100',contract_multiplier=100,
                         day_basis='calendar',risk_included=False,fees_included=False,interest_included=False),
        **values)
