"""Option-chain queries shared by the desktop page and command-line client."""
from calendar import monthrange
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
import math
import threading
import time
from zoneinfo import ZoneInfo

from .account_data import records
from .market import symbol


CONTRACT_FIELDS = (
    'code', 'name', 'stock_owner', 'strike_time', 'option_type', 'strike_price',
    'lot_size', 'option_standard_type', 'expiration_cycle', 'suspension',
)


class QueryCancelled(Exception):
    pass


def option_symbol(value):
    value = value.strip().upper()
    code = symbol(value if value.startswith(('US.', 'HK.', 'SH.', 'SZ.')) else 'US.' + value)
    if not code.startswith(('US.', 'HK.')):
        raise ValueError('期权查询支持 US / HK 标的，例如 NVDA、US.AAPL、HK.00700')
    return code


def market_timezone(code):
    return 'America/New_York' if code.startswith('US.') else 'Asia/Hong_Kong'


def add_months(day, months):
    year, month = divmod(day.year * 12 + day.month - 1 + months, 12)
    return date(year, month + 1, min(day.day, monthrange(year, month + 1)[1]))


@dataclass(frozen=True)
class OptionQuery:
    code: str
    start: date
    end: date
    option_type: str = 'ALL'

    def __post_init__(self):
        object.__setattr__(self, 'code', option_symbol(self.code))
        object.__setattr__(self, 'option_type', self.option_type.upper())
        if self.option_type not in ('ALL', 'CALL', 'PUT'):
            raise ValueError('期权类型必须为 ALL、CALL 或 PUT')
        if self.end < self.start:
            raise ValueError('结束日期不能早于开始日期')
        if self.end > add_months(self.start, 24):
            raise ValueError('每次最多查询 24 个月')

    @classmethod
    def upcoming(cls, code, months=3, option_type='ALL', start=None, end=None):
        code = option_symbol(code)
        if not 1 <= months <= 24:
            raise ValueError('月份范围为 1–24')
        today = datetime.now(ZoneInfo(market_timezone(code))).date()
        first = date.fromisoformat(start) if start else today
        last = date.fromisoformat(end) if end else add_months(first, months)
        if first < today:
            raise ValueError('OpenD 不提供已过期期权链，请选择今天或未来的日期')
        return cls(code, first, last, option_type)


def chain_windows(expirations):
    """Group published expirations into inclusive windows of at most 30 days."""
    pending = sorted(set(expirations))
    while pending:
        first = date.fromisoformat(pending[0])
        boundary = (first + timedelta(days=29)).isoformat()
        selected = [day for day in pending if day <= boundary]
        yield selected[0], selected[-1]
        pending = [day for day in pending if day > boundary]


class OptionChainService:
    def __init__(self, sdk, context, min_interval=3.1):
        self.sdk = sdk
        self.context = context
        # This instance is reused by the GUI worker, including between queries.
        self.min_interval = min_interval
        self.last_chain_call = float('-inf')

    def query(self, query, cancel=None, progress=None):
        cancel = cancel if cancel is not None else threading.Event()

        def check_cancelled():
            if cancel.is_set():
                raise QueryCancelled('查询已取消')

        check_cancelled()
        dates = records(self.sdk, self.context.get_option_expiration_date(query.code))
        first, last = query.start.isoformat(), query.end.isoformat()
        expirations = sorted({row['strike_time'] for row in dates
                              if first <= row['strike_time'] <= last})
        windows = list(chain_windows(expirations))
        contracts = {}
        for index, (start, end) in enumerate(windows):
            check_cancelled()
            if progress:
                progress(dict(completed=index, total=len(windows), start=start, end=end))
            delay = max(0, self.min_interval - (time.monotonic() - self.last_chain_call))
            if cancel.wait(delay):
                raise QueryCancelled('查询已取消')
            self.last_chain_call = time.monotonic()
            rows = records(self.sdk, self.context.get_option_chain(
                query.code, start=start, end=end,
                option_type=getattr(self.sdk.OptionType, query.option_type)))
            check_cancelled()
            for row in rows:
                expiry = row['strike_time']
                if expiry not in expirations:
                    continue
                kind = row['option_type']
                if query.option_type != 'ALL' and kind != query.option_type:
                    continue
                if kind not in ('CALL', 'PUT') or row['stock_owner'] != query.code:
                    raise ValueError('OpenD 返回了不匹配的期权标的或类型')
                strike = float(row['strike_price'])
                if not math.isfinite(strike) or strike < 0:
                    raise ValueError('OpenD 返回了无效行权价')
                contract = {key: row.get(key) for key in CONTRACT_FIELDS}
                contract['strike_price'] = strike
                size = contract['lot_size']
                contract['lot_size'] = int(size) if size is not None and math.isfinite(float(size)) else None
                contracts[row['code']] = contract
        check_cancelled()
        rows = sorted(contracts.values(), key=lambda row: (
            row['strike_time'], row['strike_price'], row['option_type'], row['code']))
        return dict(source='moomoo OpenD', symbol=query.code, start=first, end=last,
                    option_type=query.option_type, timezone=market_timezone(query.code),
                    queried_at=datetime.now(timezone.utc).isoformat(),
                    expirations=expirations, contracts=rows)


def write_result(result, stream, format='json'):
    if format == 'csv':
        import csv
        writer = csv.DictWriter(stream, fieldnames=CONTRACT_FIELDS, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(result['contracts'])
    else:
        import json
        json.dump(result, stream, ensure_ascii=False, allow_nan=False, indent=2)
        stream.write('\n')
