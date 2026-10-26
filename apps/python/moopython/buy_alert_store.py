"""Persist the frozen support zone and state of each user-armed buy alert."""
from datetime import datetime, timezone

from .buy_plan import advance_alert, advance_close_alert, nearest_levels
from .market_store import SnapshotStore


class BuyAlertStore:
    COLUMNS = ('symbol', 'support_low', 'support_high', 'signal_as_of', 'status',
               'last_quote_time', 'last_price', 'triggered_at', 'updated_at',
               'confirmation_mode', 'entered_at', 'last_bar_date')

    def __init__(self, store=None):
        self.store = store or SnapshotStore()

    def get(self, symbol):
        with self.store.connect() as db:
            row = db.execute('SELECT '+', '.join(self.COLUMNS)+' FROM buy_alerts WHERE symbol=?', (symbol,)).fetchone()
        return dict(zip(self.COLUMNS, row)) if row else None

    def active_symbols(self):
        with self.store.connect() as db:
            return [row[0] for row in db.execute(
                "SELECT symbol FROM buy_alerts WHERE status IN ('watching', 'inside') ORDER BY symbol")]

    def arm(self, signal, quote=None, mode='quote'):
        if mode not in ('quote', 'daily_close'):
            raise ValueError('不支持的提醒确认方式')
        levels = nearest_levels(signal)
        if levels is None:
            raise ValueError('暂无已确认的下方支撑区，无法设置提醒')
        symbol = signal['symbol']
        now = datetime.now(timezone.utc).isoformat()
        # The arming quote establishes a baseline, not a two-step confirmation.
        price = quote.get('last_price') if quote else None
        quote_time = quote.get('update_time') if quote else None
        status = ('invalidated' if quote_time and price is not None and price < levels['low'] else
                  'inside' if quote_time and price is not None and levels['low'] <= price <= levels['high'] else 'watching')
        with self.store.connect() as db:
            db.execute('''INSERT INTO buy_alerts
                (symbol, support_low, support_high, signal_as_of, status, last_quote_time,
                 last_price, triggered_at, updated_at, confirmation_mode, entered_at, last_bar_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(symbol) DO UPDATE SET support_low=excluded.support_low,
                support_high=excluded.support_high, signal_as_of=excluded.signal_as_of,
                status=excluded.status, last_quote_time=excluded.last_quote_time,
                last_price=excluded.last_price, triggered_at=NULL, updated_at=excluded.updated_at,
                confirmation_mode=excluded.confirmation_mode, entered_at=excluded.entered_at,
                last_bar_date=excluded.last_bar_date''',
                (symbol, levels['low'], levels['high'], levels['as_of'], status,
                 quote_time or '', price, None, now, mode,
                 quote_time if status == 'inside' else '', ''))
        return self.get(symbol)

    def pause(self, symbol):
        with self.store.connect() as db:
            db.execute("UPDATE buy_alerts SET status='paused', updated_at=? WHERE symbol=?",
                       (datetime.now(timezone.utc).isoformat(), symbol))
        return self.get(symbol)

    def observe(self, symbol, quote, *, with_event=False):
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT '+', '.join(self.COLUMNS)+' FROM buy_alerts WHERE symbol=?', (symbol,)).fetchone()
            if row is None: return (None, False) if with_event else None
            before = dict(zip(self.COLUMNS, row))
            after = advance_alert(before, quote.get('last_price'), quote.get('update_time'))
            event = before['status'] != after['status'] and after['status'] in ('confirmed', 'invalidated')
            if after != before:
                after['updated_at'] = datetime.now(timezone.utc).isoformat()
                db.execute('''UPDATE buy_alerts SET status=?, last_quote_time=?, last_price=?, triggered_at=?, updated_at=?, entered_at=?
                    WHERE symbol=?''', (after['status'], after['last_quote_time'], after['last_price'],
                                       after['triggered_at'], after['updated_at'], after['entered_at'], symbol))
        return (after, event) if with_event else after

    def observe_close(self, symbol, close, as_of, *, with_event=False):
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT '+', '.join(self.COLUMNS)+' FROM buy_alerts WHERE symbol=?', (symbol,)).fetchone()
            if row is None: return (None, False) if with_event else None
            before = dict(zip(self.COLUMNS, row))
            after = advance_close_alert(before, close, as_of)
            event = before['status'] != after['status'] and after['status'] in ('confirmed', 'invalidated')
            if after != before:
                after['updated_at'] = datetime.now(timezone.utc).isoformat()
                db.execute('''UPDATE buy_alerts SET status=?, last_bar_date=?, triggered_at=?, updated_at=?
                    WHERE symbol=?''', (after['status'], after['last_bar_date'], after['triggered_at'],
                                       after['updated_at'], symbol))
        return (after, event) if with_event else after
