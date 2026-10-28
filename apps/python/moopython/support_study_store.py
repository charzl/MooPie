"""Versioned support studies preserve input bars and frozen lifecycle history."""
from datetime import datetime, timezone
import json

from .market_store import SnapshotStore
from .support_study import support_study


class SupportStudyStore:
    def __init__(self, store=None):
        self.store = store or SnapshotStore()

    def evaluate(self, series, trend):
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            previous = db.execute('''SELECT payload FROM support_studies WHERE symbol=? AND as_of<=?
                ORDER BY as_of DESC, calculated_at DESC, id DESC LIMIT 1''',
                (series['symbol'], series['as_of'])).fetchone()
            study = support_study(series, trend, previous=json.loads(previous[0]) if previous else None)
            return dict(study=study, calculated_at=self._save(db, study))

    def save(self, study):
        if study.get('status') != 'ok': return None
        with self.store.connect() as db:
            return self._save(db, study)

    @staticmethod
    def _save(db, study):
        if study.get('status') != 'ok': return None
        calculated_at = datetime.now(timezone.utc).isoformat()
        payload = json.dumps(study, ensure_ascii=False, sort_keys=True, allow_nan=False)
        db.execute('''INSERT INTO support_studies
                (symbol, as_of, study_version, definition_key, input_hash, calculated_at, payload)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(symbol, as_of, definition_key, input_hash) DO UPDATE SET
                    calculated_at=excluded.calculated_at, payload=excluded.payload''',
            (study['symbol'], study['as_of'], study['version'], study['definition_key'],
             study['input_hash'], calculated_at, payload))
        return calculated_at

    def latest(self, symbol, *, as_of=None):
        rows = self.history(symbol, limit=1, as_of=as_of)
        return rows[0] if rows else None

    def history(self, symbol, limit=20, *, as_of=None):
        if type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError('History limit must be 1–100')
        with self.store.connect() as db:
            rows = db.execute('''SELECT payload, calculated_at FROM support_studies
                WHERE symbol=? AND (? IS NULL OR as_of<=?)
                ORDER BY as_of DESC, calculated_at DESC, id DESC LIMIT ?''',
                (symbol, as_of, as_of, limit)).fetchall()
        return [dict(study=json.loads(payload), calculated_at=stamp) for payload, stamp in rows]
