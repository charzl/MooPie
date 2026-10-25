import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
import os
from contextlib import contextmanager

from moopython.buy_plan import advance_alert, calculate_plan
from moopython.buy_alert_store import BuyAlertStore
from moopython.market_store import SnapshotStore


def signal():
    return dict(symbol='US.TEST', status='ok', as_of='2026-10-23',
                support_zones=[dict(low=90.0, high=94.0)],
                resistance_zones=[dict(low=105.0, high=107.0)])


class BuyPlanTests(unittest.TestCase):
    def test_plan_uses_whole_shares_and_shows_loss_and_nearest_target(self):
        plan = calculate_plan(signal(), 3000)
        self.assertEqual([row['price'] for row in plan['tranches']], [94, 92, 91])
        self.assertEqual([row['shares'] for row in plan['tranches']], [12, 9, 9])
        self.assertEqual(plan['cost'], 2775)
        self.assertEqual(plan['max_loss_to_stop'], 75)
        self.assertEqual(plan['target_gain'], 375)
        self.assertEqual(plan['unused'], 225)
        with self.assertRaises(ValueError): calculate_plan(dict(signal(), support_zones=[]), 3000)
        with self.assertRaises(ValueError): calculate_plan(signal(), 1)

    def test_alert_requires_new_quote_after_entry_and_invalidates_below_low(self):
        with tempfile.TemporaryDirectory() as root:
            alerts = BuyAlertStore(SnapshotStore(Path(root)/'market.sqlite3'))
            quote = dict(last_price=99, update_time='2026-10-26 09:30:00')
            record = alerts.arm(signal(), quote)
            self.assertEqual(record['status'], 'watching')
            self.assertEqual(alerts.active_symbols(), ['US.TEST'])
            self.assertEqual(alerts.observe('US.TEST', quote), record)
            entered = alerts.observe('US.TEST', dict(last_price=93, update_time='2026-10-26 09:31:00'))
            self.assertEqual(entered['status'], 'inside')
            self.assertEqual(alerts.observe('US.TEST', dict(last_price=95, update_time='2026-10-26 09:31:00'))['status'], 'inside')
            confirmed = alerts.observe('US.TEST', dict(last_price=95, update_time='2026-10-26 09:32:00'))
            self.assertEqual(confirmed['status'], 'confirmed')
            self.assertEqual(alerts.active_symbols(), [])
            self.assertEqual(BuyAlertStore(SnapshotStore(Path(root)/'market.sqlite3')).get('US.TEST')['status'], 'confirmed')
            record = alerts.arm(signal(), dict(last_price=93, update_time='2026-10-26 09:33:00'))
            self.assertEqual(record['status'], 'inside')
            invalid = alerts.observe('US.TEST', dict(last_price=89, update_time='2026-10-26 09:34:00'))
            self.assertEqual(invalid['status'], 'invalidated')
            self.assertEqual(alerts.observe('US.TEST', dict(last_price=100, update_time='2026-10-26 09:35:00')), invalid)
            self.assertEqual(alerts.observe('US.TEST', dict(last_price=89, update_time='2026-10-26 09:34:00'), with_event=True), (invalid, False))

    def test_older_or_missing_timestamp_never_changes_state(self):
        record = dict(status='inside', support_low=90, support_high=94,
                      last_quote_time='2026-10-26 09:32:00', last_price=93, triggered_at=None)
        self.assertIs(advance_alert(record, 100, ''), record)
        self.assertIs(advance_alert(record, 100, '2026-10-26 09:31:00'), record)

    def test_alert_cli_does_not_connect_when_no_alert_is_armed(self):
        from moopython.research_cli import main
        import json
        with tempfile.TemporaryDirectory() as root, patch.dict(os.environ, {'MOOMOO_DB_PATH': str(Path(root)/'market.sqlite3')}):
            output = Path(root)/'alerts.json'
            with patch('moopython.research_cli.market_data_connection', side_effect=AssertionError('OpenD must stay idle')):
                self.assertEqual(main(['alerts', '--output', str(output)]), 0)
            self.assertEqual(json.loads(output.read_text())['rows'], [])

    def test_alert_cli_reports_only_new_terminal_transition(self):
        from moopython.research_cli import main
        import json
        with tempfile.TemporaryDirectory() as root, patch.dict(os.environ, {'MOOMOO_DB_PATH': str(Path(root)/'market.sqlite3')}):
            alerts = BuyAlertStore()
            alerts.arm(signal(), dict(last_price=99, update_time='2026-10-26 09:30:00'))
            output = Path(root)/'alerts.json'
            current = [dict(code='US.TEST', last_price=93, update_time='2026-10-26 09:31:00')]

            @contextmanager
            def market(**_kwargs):
                class Service:
                    def snapshots(self, codes):
                        self_codes = [row['code'] for row in current]
                        if codes != self_codes: raise AssertionError(codes)
                        return dict(rows=current)
                yield Service()

            with patch('moopython.research_cli.market_data_connection', market):
                self.assertEqual(main(['alerts', '--output', str(output)]), 0)
                self.assertFalse(json.loads(output.read_text())['rows'][0]['event'])
                current[0] = dict(code='US.TEST', last_price=95, update_time='2026-10-26 09:32:00')
                self.assertEqual(main(['alerts', '--output', str(output)]), 0)
                self.assertTrue(json.loads(output.read_text())['rows'][0]['event'])
                self.assertEqual(main(['alerts', '--output', str(output)]), 0)
                self.assertEqual(json.loads(output.read_text())['rows'], [])


if __name__ == '__main__': unittest.main()
