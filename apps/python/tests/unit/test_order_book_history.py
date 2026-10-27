from datetime import datetime, timedelta, timezone
from contextlib import contextmanager
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from moopython.data_status import detail_data_status
from moopython.depth_timeline import bucket_timeline
from moopython.market_store import SnapshotStore
from moopython.order_book_history import OrderBookHistory


def book(stamp, bid=97, bid_volume=10):
    return dict(symbol='US.TEST', status='ok', collected_at=stamp.isoformat(), depth=60,
                bids=[dict(price=bid, volume=bid_volume)],
                asks=[dict(price=103, volume=10)])


class OrderBookHistoryTests(unittest.TestCase):
    def test_depth_cli_saves_snapshot_and_returns_recent_history(self):
        from moopython.research_cli import main
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {'MOOMOO_DB_PATH': str(Path(directory)/'market.sqlite3')}):
            output = Path(directory) / 'depth.json'
            @contextmanager
            def market(**_options):
                class Service:
                    def snapshots(self, symbols):
                        self.assertEqual(symbols, ['US.TEST'])
                        return dict(rows=[dict(code='US.TEST', last_price=100,
                                               update_time='2026-10-26 13:00:00')])
                service = Service()
                service.assertEqual = self.assertEqual
                yield service
            with patch('moopython.research_cli.market_data_connection', market), \
                 patch('moopython.order_book.read_order_book', return_value=book(datetime.now(timezone.utc))):
                self.assertEqual(main(['depth', 'TEST', '--output', str(output)]), 0)
            payload = json.loads(output.read_text())
            self.assertEqual(payload['action'], 'depth')
            self.assertEqual(payload['symbol'], 'US.TEST')
            self.assertEqual(len(payload['order_book_history']), 1)
            self.assertEqual(payload['order_book_history'][0]['book']['bids'][0]['price'], 97)

    def test_history_persists_actual_snapshots_and_deduplicates(self):
        now = datetime(2026, 10, 26, 17, 0, tzinfo=timezone.utc)
        with tempfile.TemporaryDirectory() as directory:
            history = OrderBookHistory(SnapshotStore(Path(directory) / 'market.sqlite3'))
            self.assertTrue(history.save(book(now-timedelta(minutes=2)), dict(update_time='2026-10-26 12:58:00')))
            self.assertTrue(history.save(book(now-timedelta(minutes=2)), dict(update_time='2026-10-26 12:58:00')))
            self.assertTrue(history.save(book(now, bid_volume=20)))
            self.assertFalse(history.save(dict(symbol='US.TEST', status='unavailable')))
            rows = history.recent('US.TEST', minutes=5, now=now)
            self.assertEqual(len(rows), 2)
            self.assertEqual([row['book']['bids'][0]['volume'] for row in rows], [10, 20])
            self.assertEqual(len(history.recent('US.TEST', minutes=1, now=now)), 1)

    def test_timeline_uses_same_current_bucket_for_past_samples(self):
        now = datetime(2026, 10, 26, 17, 0, tzinfo=timezone.utc)
        records = [dict(collected_at=(now-timedelta(minutes=5)).isoformat(),
                        book=book(now-timedelta(minutes=5), bid=94, bid_volume=100)),
                   dict(collected_at=(now-timedelta(minutes=1)).isoformat(),
                        book=book(now-timedelta(minutes=1), bid=97, bid_volume=10)),
                   dict(collected_at=now.isoformat(), book=book(now, bid=97, bid_volume=20))]
        result = bucket_timeline(records, book(now, bid=97, bid_volume=20),
                                 dict(last_price=100), now=now)
        bid = result['bids']
        self.assertEqual((bid['bucket']['low'], bid['bucket']['high']), (95, 100))
        self.assertEqual(bid['windows'][1]['samples'], 3)
        self.assertEqual(bid['windows'][1]['first'], 0)
        self.assertEqual(bid['windows'][1]['latest'], 1940)
        self.assertEqual(bid['windows'][2]['average'], 970)

    def test_status_flags_missing_exchange_time_and_misaligned_quote(self):
        now = datetime(2026, 10, 26, 21, 0, tzinfo=timezone.utc)
        quote = dict(update_time='2026-10-26 16:45:00', last_price=100, after_price=101)
        current = book(now)
        status = detail_data_status(quote, current, dict(status='ok', as_of='2026-10-26'), now=now)
        self.assertEqual(status['session'], 'after')
        self.assertIn('报价与盘口采集相差超过 2 分钟', status['issues'])
        self.assertIn('盘口交易所更新时间未提供，时效无法验证', status['issues'])


if __name__ == '__main__':
    unittest.main()
