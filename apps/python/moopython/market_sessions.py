"""Bounded US exchange calendar and conservative query windows, independent of OpenD.

Calendar: https://www.nyse.com/trade/hours-calendars (2026–2028).
Extended options: https://www.cboe.com/notices/content/?id=62044
16:15 is a conservative query boundary for options; not every class trades that late.
Eligibility is versioned and must be reviewed as exchanges publish changes.
"""
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

NY = ZoneInfo('America/New_York')
HOLIDAYS = {
    2025: '01-01 01-09 01-20 02-17 04-18 05-26 06-19 07-04 09-01 11-27 12-25',
    2026: '01-01 01-19 02-16 04-03 05-25 06-19 07-03 09-07 11-26 12-25',
    2027: '01-01 01-18 02-15 03-26 05-31 06-18 07-05 09-06 11-25 12-24',
    2028: '01-17 02-21 04-14 05-29 06-19 07-04 09-04 11-23 12-25',
}
EARLY = set('2025-07-03 2025-11-28 2025-12-24 2026-11-27 2026-12-24 '
            '2027-11-26 2028-07-03 2028-11-24'.split())
EXTENDED = set('AAPL AMD AMZN AVGO BABA BAC F GOOG GOOGL HOOD INTC META MRVL '
               'MSFT MU NFLX NOK NVDA ORCL PFE PLTR SNDK SPCX TSLA TSM '
               'SPY QQQ IWM GLD XLF'.split())


def trading_day(day):
    if day.year not in HOLIDAYS:
        raise ValueError('本地交易日历仅覆盖 2025–2028 年，请先更新日历；没有猜测盘中/盘后。')
    return day.weekday() < 5 and day.strftime('%m-%d') not in HOLIDAYS[day.year].split()


def previous_session(day):
    while not trading_day(day):
        day -= timedelta(days=1)
    return day


def market_session(now, kind='options', symbols=()):
    if now.tzinfo is None:
        raise ValueError('Market clock must include a timezone')
    local = now.astimezone(NY)
    day, clock = local.date(), local.time().replace(tzinfo=None)
    today_open = trading_day(day)
    early = day.isoformat() in EARLY
    close = time(13, 15) if early else time(16, 15)
    roots = [s.removeprefix('US.') for s in symbols]
    extended = day >= date(2026, 10, 19) and any(s in EXTENDED for s in roots)
    start = time(7, 30) if extended and kind == 'options' else time(9, 30)
    if kind == 'daily':
        # The collector waits five minutes before accepting a completed daily bar.
        close = time(13, 5) if early else time(16, 5)
    if kind == 'stocks':
        # Conservative envelope includes stock overnight trading. A non-tradable
        # symbol still goes to OpenD; its actual timestamp/state remains authoritative.
        live = ((today_open and (day.weekday() != 4 or clock < time(20)))
                or (day.weekday() in (0, 1, 2, 3, 6) and clock >= time(20)
                    and trading_day(day + timedelta(days=1))))
        start = time(0)
    else:
        live = today_open and start <= clock < close
        if extended and kind == 'options' and time(9, 25) <= clock < time(9, 30):
            live = False
    session = previous_session(day if today_open and clock >= start else day - timedelta(days=1))
    return dict(is_open=live, phase='盘中' if live else '盘后 / 休市',
                session_date=session.isoformat(), checked_at=now.isoformat(),
                timezone='America/New_York', calendar_version='NYSE-2025-2028-CBOE-20261019',
                window_note='保守查询时段；报价更新时间与 OpenD market_state 为准',
                close_at=datetime.combine(day, close, NY).isoformat())
