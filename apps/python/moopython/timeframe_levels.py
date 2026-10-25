"""Conservative weekly/monthly zones derived from validated completed daily bars."""
from calendar import monthrange
from datetime import date, datetime, timedelta
from math import isfinite
from statistics import mean
from zoneinfo import ZoneInfo

from .price_signals import PARAMETERS, _zones


VERSION = '1.0.0'
PERIODS = {'week': 52, 'month': 18}
NY = ZoneInfo('America/New_York')


def _key(day, period):
    if period == 'week':
        year, week, _ = day.isocalendar()
        return (year, week)
    return (day.year, day.month)


def _period_end(day, period):
    if period == 'week': return day + timedelta(days=6-day.weekday())
    return date(day.year, day.month, monthrange(day.year, day.month)[1])


def _aggregate(bars, period, cutoff):
    groups = []
    for bar in bars:
        day = date.fromisoformat(bar['date'])
        key = _key(day, period)
        if not groups or groups[-1][0] != key: groups.append((key, []))
        groups[-1][1].append(bar)
    completed = []
    for index, (_key_value, group) in enumerate(groups):
        last = date.fromisoformat(group[-1]['date'])
        end = _period_end(last, period)
        # Earlier groups are complete because a later daily bar exists. For the
        # last group, require an ended period and a plausible final trading day.
        if index == len(groups)-1 and (end > cutoff or (end-last).days > 2):
            continue
        completed.append(dict(date=group[-1]['date'], open=group[0]['open'],
                              high=max(row['high'] for row in group),
                              low=min(row['low'] for row in group), close=group[-1]['close'],
                              volume=sum(row['volume'] for row in group)))
    return completed


def _atr(bars):
    if len(bars) < 15: return None
    ranges = []
    for index in range(len(bars)-14, len(bars)):
        bar, previous = bars[index], bars[index-1]
        ranges.append(max(bar['high']-bar['low'], abs(bar['high']-previous['close']),
                          abs(bar['low']-previous['close'])))
    return mean(ranges)


def _period_zones(bars, period, price):
    bars = bars[-PERIODS[period]:]
    atr = _atr(bars)
    if atr is None or not isfinite(atr) or atr <= 0:
        return dict(status='unavailable', reason=f'已结束周期只有 {len(bars)} 根，至少需要 15 根以计算 ATR',
                    bars=len(bars), support_zones=[], resistance_zones=[])
    tolerance = max(atr*PARAMETERS['zone_atr_fraction'], price*PARAMETERS['zone_price_fraction'])
    supports = [zone for zone in _zones(bars, 'support', tolerance) if zone['center'] < price]
    resistances = [zone for zone in _zones(bars, 'resistance', tolerance) if zone['center'] > price]
    for side, zones in (('support', supports), ('resistance', resistances)):
        for zone in zones:
            distance = max(0, price-zone['high']) if side == 'support' else max(0, zone['low']-price)
            zone.update(distance_pct=distance/price*100, distance_atr=distance/atr)
        zones.sort(key=lambda item: (item['distance_pct'], -item['independent_touches']))
        del zones[PARAMETERS['maximum_zones']:]
    return dict(status='ok', as_of=bars[-1]['date'], lookback_start=bars[0]['date'],
                bars=len(bars), atr14=atr, zone_tolerance=tolerance,
                support_zones=supports, resistance_zones=resistances)


def timeframe_levels(series, signal, decision_cutoff):
    """Use the exact daily history accepted for the displayed price signal."""
    if not signal or signal.get('status') != 'ok':
        return dict(version=VERSION, status='unavailable', reason='日线信号不可用')
    try:
        bars = series['bars']
        if (series['symbol'] != signal['symbol'] or series['as_of'] != signal['as_of'] or
                not bars or bars[-1]['date'] != signal['as_of'] or
                any(not row.get('complete') for row in bars)):
            raise ValueError('日线与价格信号不一致')
        cutoff = datetime.fromisoformat(decision_cutoff)
        if cutoff.tzinfo is None: raise ValueError('决策时间缺少时区')
        cutoff = cutoff.astimezone(NY).date()
        price = signal['reference']['price']
        if isinstance(price, bool) or not isinstance(price, (float, int)) or not isfinite(price) or price <= 0:
            raise ValueError('参考价格无效')
        result = {period: _period_zones(_aggregate(bars, period, cutoff), period, price)
                  for period in PERIODS}
        return dict(version=VERSION, status='ok', source='completed_qfq_daily_bars_aggregated',
                    daily_as_of=signal['as_of'], decision_cutoff=decision_cutoff, periods=result,
                    note='周线和月线由已验证日线汇总；最后一个周期仅在已结束且最后交易日可确认时纳入。区间重合不代表更高胜率。')
    except (KeyError, TypeError, ValueError, IndexError) as error:
        return dict(version=VERSION, status='unavailable', reason=str(error))
