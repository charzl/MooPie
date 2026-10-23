"""Persist confirmed daily support and resistance with their calculation evidence."""
from datetime import datetime, timezone
import json

from .market_store import SnapshotStore


class PriceSignalStore:
    def __init__(self, store=None):
        self.store = store or SnapshotStore()

    def save(self, signal):
        if signal.get('status') != 'ok':
            return None
        symbol = signal['symbol']
        as_of = signal['as_of']
        reference = signal['reference']
        reference_time = reference.get('time') or ''
        version = signal['version']
        payload = json.dumps(signal, ensure_ascii=False, sort_keys=True, allow_nan=False)
        calculated_at = datetime.now(timezone.utc).isoformat()
        with self.store.connect() as db:
            db.execute('''INSERT INTO price_signals
                (symbol, as_of, reference_price, reference_time, signal_version, calculated_at, payload)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(symbol, as_of, reference_time, signal_version) DO UPDATE SET
                    reference_price=excluded.reference_price,
                    calculated_at=excluded.calculated_at,
                    payload=excluded.payload''',
                (symbol, as_of, reference['price'], reference_time, version, calculated_at, payload))
        return calculated_at

    def latest(self, symbol):
        records = self.history(symbol, limit=1)
        return records[0] if records else None

    def history(self, symbol, limit=20):
        if type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError('History limit must be 1–100')
        with self.store.connect() as db:
            rows = db.execute('''SELECT payload, calculated_at FROM price_signals
                WHERE symbol=? ORDER BY as_of DESC, calculated_at DESC LIMIT ?''', (symbol, limit)).fetchall()
        return [dict(signal=json.loads(payload), calculated_at=calculated_at)
                for payload, calculated_at in rows]
