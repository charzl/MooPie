"""UI-independent market models; demonstration data is explicitly synthetic."""
from dataclasses import dataclass
from datetime import datetime, timedelta
import math
import random
import re
import json
import os
from pathlib import Path
from functools import lru_cache

@lru_cache(maxsize=1)
def shared_fixture():
    candidates=[Path(os.environ["MOOMOO_BENCHMARK_FIXTURE"])] if os.environ.get("MOOMOO_BENCHMARK_FIXTURE") else [Path(__file__).parent.parent/"fixtures/market.json",Path(__file__).parents[3]/"fixtures/market.json"]
    for path in candidates:
        if path.is_file():
            return json.loads(path.read_text())
    return None

PERIODS = {"日K": "K_DAY", "周K": "K_WEEK", "月K": "K_MON", "1分": "K_1M", "5分": "K_5M", "15分": "K_15M", "1小时": "K_60M"}
NAMES = {"US.PLTR": "Palantir", "US.INTC": "英特尔", "US.AVGO": "博通", "US.TEM": "Tempus AI", "US.NVDA": "英伟达", "US.AAPL": "苹果", "US.AMZN": "亚马逊", "US.MSFT": "微软", "US.TSLA": "特斯拉", "HK.00700": "腾讯控股", "HK.00981": "中芯国际", "HK.09988": "阿里巴巴-W", "HK.01810": "小米集团-W"}
DEFAULT_SYMBOLS = list(NAMES)

def symbol(value, allow_short=True):
    value = value.strip().upper()
    if allow_short and re.fullmatch(r"[A-Z][A-Z0-9_-]*(?:\.[A-Z0-9_-]+)*", value) and not value.startswith(('US.','HK.','SH.','SZ.')):
        value = 'US.' + value
    if not re.fullmatch(r"(US|HK|SH|SZ)\.[A-Z0-9][A-Z0-9._-]{0,31}", value):
        raise ValueError("请输入 PLTR、AAPL、HK.00700、SH.600519 或 SZ.000001")
    return value

def display_symbol(value):
    return value[3:] if isinstance(value, str) and value.startswith('US.') else value

def number(value, default=0.0):
    try:
        result = float(value)
        return result if math.isfinite(result) else default
    except (TypeError, ValueError):
        return default

@dataclass(frozen=True)
class Candle:
    time: str
    open: float
    high: float
    low: float
    close: float
    volume: float

    @classmethod
    def from_row(cls, row):
        if not row.get("time_key") or not all(math.isfinite(number(row.get(key), float("nan"))) for key in ("open", "high", "low", "close")):
            raise ValueError("K 线字段缺失或无效")
        return cls(str(row["time_key"]), *(number(row[k]) for k in ("open", "high", "low", "close", "volume")))

@dataclass(frozen=True)
class Quote:
    code: str
    name: str
    price: float
    previous: float
    open: float
    high: float
    low: float
    volume: float
    turnover: float
    updated: str
    after: float | None = None

    @property
    def change(self):
        return self.price - self.previous

    @property
    def percent(self):
        return self.change / self.previous * 100 if self.previous else 0

    @classmethod
    def from_row(cls, row):
        code = symbol(str(row["code"]),allow_short=False)
        name = row.get("name")
        if not isinstance(name, str) or not name:
            name = NAMES.get(code, code.split(".", 1)[1])
        after = number(row.get("after_price"), float("nan"))
        return cls(code, name, *(number(row.get(k)) for k in ("last_price", "prev_close_price", "open_price", "high_price", "low_price", "volume", "turnover")),
                   updated=f"{row.get('data_date', '')} {row.get('data_time', '')}".strip(),
                   after=after if math.isfinite(after) else None)

def parse_candles(rows):
    result = {}
    for row in rows:
        try:
            bar = Candle.from_row(row)
            result[bar.time] = bar
        except (ValueError, KeyError):
            pass
    return sorted(result.values(), key=lambda bar: bar.time)

def merge_candles(existing, incoming, limit=200):
    result = {bar.time: bar for bar in existing}
    result.update({bar.time: bar for bar in incoming})
    return sorted(result.values(), key=lambda bar: bar.time)[-limit:]

def averages(bars, period):
    total = 0.0
    result = []
    for i, bar in enumerate(bars):
        total += bar.close
        if i >= period:
            total -= bars[i-period].close
        result.append(total / period if i + 1 >= period else None)
    return result

def demo_candles(code, period="日K"):
    fixture=shared_fixture()
    if fixture and code in fixture["candles"]:
        return [Candle(b["time"],b["openPrice"],b["highPrice"],b["lowPrice"],b["closePrice"],b["volume"]) for b in fixture["candles"][code][period]]
    rng = random.Random(f"MooPython:{code}:{period}")
    price = rng.uniform(80, 250)
    step = {"日K": 1440, "周K": 10080, "月K": 43200, "1分": 1, "5分": 5, "15分": 15, "1小时": 60}[period]
    start = datetime(2025, 1, 1)
    bars = []
    for i in range(180):
        opening = price
        price = max(5, opening * (1 + (rng.random() - .46) * .035))
        bars.append(Candle((start + timedelta(minutes=i * step)).strftime("%Y-%m-%d %H:%M:%S"), opening,
                           max(opening, price) * (1 + rng.random()*.018), min(opening, price) * (1 - rng.random()*.018), price,
                           rng.uniform(500_000, 12_500_000)))
    return bars

def demo_quote(code):
    fixture=shared_fixture()
    if fixture and code in fixture["quotes"]:
        q=fixture["quotes"][code]
        return Quote(code,q["name"],q["curPrice"],q["lastClosePrice"],q["openPrice"],q["highPrice"],q["lowPrice"],q["volume"],q["turnover"],q["updateTime"])
    bars = demo_candles(code)
    last = bars[-1]
    return Quote(code, NAMES.get(code, code.split(".", 1)[1]), last.close, bars[-2].close,
                 last.open, last.high, last.low, last.volume, last.volume * last.close, "演示数据")

def compact(value):
    if value >= 100_000_000:
        return f"{value/100_000_000:.2f}亿"
    if value >= 10_000:
        return f"{value/10_000:.2f}万"
    return f"{value:.0f}"
