"""Data timestamps and conservative freshness diagnostics for stock detail."""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from .order_book import quote_reference


def _parse(stamp, *, new_york=False):
    if not stamp:
        return None
    try:
        value = datetime.fromisoformat(str(stamp))
        if value.tzinfo is None:
            value = value.replace(tzinfo=ZoneInfo('America/New_York') if new_york else timezone.utc)
        return value.astimezone(timezone.utc)
    except ValueError:
        return None


def detail_data_status(quote, book, signal=None, *, now=None):
    now = now or datetime.now(timezone.utc)
    quote_time = _parse((quote or {}).get('update_time'), new_york=True)
    book_time = _parse((book or {}).get('collected_at'))
    bid_time = _parse((book or {}).get('bid_server_time'), new_york=True)
    ask_time = _parse((book or {}).get('ask_server_time'), new_york=True)
    daily_date = signal.get('as_of') if signal and signal.get('status') == 'ok' else None
    session = quote_reference(quote)['session'] if quote else None
    issues = []
    if not quote_time: issues.append('报价更新时间未知')
    if not book_time: issues.append('盘口采集时间未知')
    if book_time and (now-book_time).total_seconds() > 120: issues.append('盘口采集已超过 2 分钟')
    if quote_time and book_time and abs((book_time-quote_time).total_seconds()) > 120:
        issues.append('报价与盘口采集相差超过 2 分钟')
    if not bid_time or not ask_time:
        issues.append('盘口交易所更新时间未提供，时效无法验证')
    elif book_time and max(abs((book_time-stamp).total_seconds()) for stamp in (bid_time, ask_time)) > 120:
        issues.append('盘口交易所更新时间与采集相差超过 2 分钟')
    if not daily_date: issues.append('已验证日线日期未知')
    return dict(state='check' if issues else 'aligned', issues=issues,
                quote_time=(quote or {}).get('update_time'),
                book_time=(book or {}).get('collected_at'),
                bid_time=(book or {}).get('bid_server_time'),
                ask_time=(book or {}).get('ask_server_time'),
                daily_date=daily_date, session=session)
