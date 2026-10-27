"""Bounded local history of observed visible depth snapshots."""
from datetime import datetime, timedelta, timezone
import json

from .market_store import SnapshotStore


class OrderBookHistory:
    def __init__(self, store=None):
        self.store = store or SnapshotStore()

    def save(self, book, quote=None):
        if not book or book.get('status') != 'ok':
            return False
        stamp = datetime.fromisoformat(book['collected_at'])
        if stamp.tzinfo is None:
            raise ValueError('Order-book collection time must have a timezone')
        collected_at = stamp.astimezone(timezone.utc).isoformat()
        symbol = book['symbol']
        payload = json.dumps(book, ensure_ascii=False, sort_keys=True, allow_nan=False)
        with self.store.connect() as db:
            db.execute('''INSERT OR IGNORE INTO order_book_history
                (symbol, collected_at, quote_time, payload) VALUES (?, ?, ?, ?)''',
                (symbol, collected_at, (quote or {}).get('update_time'), payload))
            # Keep a bounded sample history for each stock; this is observation data,
            # not a complete order-by-order event stream.
            db.execute('''DELETE FROM order_book_history WHERE symbol=? AND id NOT IN
                (SELECT id FROM order_book_history WHERE symbol=?
                 ORDER BY collected_at DESC LIMIT 1440)''', (symbol, symbol))
        return True

    def recent(self, symbol, *, minutes=30, now=None):
        if type(minutes) is not int or not 1 <= minutes <= 1440:
            raise ValueError('History window must be 1–1440 minutes')
        now = now or datetime.now(timezone.utc)
        cutoff = (now.astimezone(timezone.utc) - timedelta(minutes=minutes)).isoformat()
        with self.store.connect() as db:
            rows = db.execute('''SELECT collected_at, quote_time, payload
                FROM order_book_history WHERE symbol=? AND collected_at>=?
                ORDER BY collected_at DESC LIMIT 1440''', (symbol, cutoff)).fetchall()
        return [dict(collected_at=stamp, quote_time=quote_time, book=json.loads(payload))
                for stamp, quote_time, payload in reversed(rows)]
