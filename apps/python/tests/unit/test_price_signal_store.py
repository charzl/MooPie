import tempfile
import json
import os
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
import unittest
from unittest.mock import patch

from moopython.market_store import SnapshotStore
from moopython.price_signal_store import PriceSignalStore


class PriceSignalStoreTests(unittest.TestCase):
    def test_persists_zones_and_evidence_by_quote_time(self):
        with tempfile.TemporaryDirectory() as directory:
            market = SnapshotStore(Path(directory) / 'market.sqlite3')
            store = PriceSignalStore(market)
            signal = dict(symbol='US.TEST', status='ok', version='1.0.0', as_of='2026-10-22',
                          reference=dict(price=100, time='2026-10-23 10:00:00', basis='underlying_snapshot'),
                          support_zones=[dict(low=90, high=92, evidence=[dict(date='2026-10-01')])],
                          resistance_zones=[dict(low=108, high=110, evidence=[dict(date='2026-10-02')])])
            saved_at = store.save(signal)
            self.assertEqual(store.latest('US.TEST'), dict(signal=signal, calculated_at=saved_at))
            self.assertIsNone(store.save(dict(symbol='US.TEST', status='unavailable')))
            self.assertEqual(store.latest('US.TEST')['signal'], signal)
            newer = dict(signal, reference=dict(price=102, time='2026-10-23 10:05:00', basis='underlying_snapshot'))
            store.save(newer)
            with market.connect() as db:
                self.assertEqual(db.execute('SELECT count(*) FROM price_signals').fetchone()[0], 2)
            self.assertEqual(store.latest('US.TEST')['signal'], newer)
            self.assertEqual([row['signal']['reference']['price'] for row in store.history('US.TEST')], [102, 100])
            from moopython.database_cli import main
            output = StringIO()
            with patch.dict(os.environ, {'MOOMOO_DB_PATH': str(market.path)}), redirect_stdout(output):
                self.assertEqual(main(['price-signals', 'TEST', '--limit', '1']), 0)
            self.assertEqual(json.loads(output.getvalue())['history'][0]['signal'], newer)


if __name__ == '__main__': unittest.main()
