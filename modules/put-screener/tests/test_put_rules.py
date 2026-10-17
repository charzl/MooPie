import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('put_rules', ROOT / 'put_rules.py')
rules = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rules)


class PutRuleTests(unittest.TestCase):
    def setUp(self):
        self.dataset = json.loads((ROOT / 'example.json').read_text())
        self.row = self.dataset['contracts'][0]
        self.original_rules = copy.deepcopy(rules.RULES)
        self.original_sort = copy.deepcopy(rules.SORT_ORDER)

    def tearDown(self):
        rules.RULES = self.original_rules
        rules.SORT_ORDER = self.original_sort

    def test_cash_secured_payoff_and_bid_based_yield(self):
        self.row['last_price'] = 999  # A stale last trade must not affect credit.
        report = rules.scan(self.dataset)
        self.assertEqual(report['ranked_codes'], [self.row['code']])
        m = report['ranked'][0]['metrics']
        self.assertEqual(m['days_to_expiry'], 35)
        self.assertEqual(m['premium_per_contract_before_costs'], 150)
        self.assertEqual(m['cash_collateral'], 9000)
        self.assertEqual(m['breakeven_before_costs'], 88.5)
        self.assertEqual(m['max_loss_before_costs'], 8850)
        self.assertEqual(m['pnl_at_spot_minus_20_pct'], -850)
        self.assertAlmostEqual(m['annualized_gross_return_pct'], 100 * 1.5 / 90 * 365 / 35)
        self.assertAlmostEqual(m['spread_pct_of_mid'], 100 * .1 / 1.55)

    def test_closed_or_stale_market_is_never_live_review_ready(self):
        result = rules.scan(self.dataset)['ranked'][0]
        self.assertFalse(result['live_review_ready'])
        self.row['market_state'] = 'AFTERNOON'
        self.assertFalse(rules.scan(self.dataset)['ranked'][0]['live_review_ready'])
        self.dataset['collected_at'] = '2026-10-16T20:06:00+00:00'
        self.assertTrue(rules.scan(self.dataset)['ranked'][0]['live_review_ready'])

    def test_optional_zero_iv_is_unknown_without_bypassing_required_delta(self):
        self.row['iv_pct'] = 0
        result = rules.scan(self.dataset)['ranked'][0]
        self.assertIsNone(result['metrics']['iv_pct'])
        self.row['delta'] = 0
        report = rules.scan(self.dataset)
        self.assertFalse(report['ranked'])
        self.assertIn('min-delta', report['results'][0]['failed_rules'])
        self.row['iv_pct'] = -1
        self.assertEqual(rules.scan(self.dataset)['results'][0]['status'], 'invalid_data')

    def test_missing_earnings_remain_blocked_in_separate_watchlist(self):
        self.row['earnings'] = None
        report = rules.scan(self.dataset)
        self.assertIsNone(report['best_research_code'])
        self.assertFalse(report['earnings_unverified_watchlist'][0]['eligible'])
        self.assertEqual(report['best_watchlist_code'], self.row['code'])
        self.assertEqual(set(report['earnings_unverified_watchlist'][0]['failed_rules']), {'earnings-checked', 'earnings-buffer'})

    def test_known_earnings_crossing_is_not_on_watchlist(self):
        for event_day in ('2026-11-02', '2026-11-20', '2026-11-22'):
            self.row['earnings']['date'] = event_day
            report = rules.scan(self.dataset)
            self.assertEqual(report['ranked'], [])
            self.assertEqual(report['earnings_unverified_watchlist'], [])
        self.row['earnings']['date'] = '2026-11-23'
        self.assertEqual(rules.scan(self.dataset)['qualified_count'], 1)

    def test_calendar_failure_does_not_establish_earnings_clearance(self):
        self.row['earnings_calendar_complete'] = False
        report = rules.scan(self.dataset)
        self.assertEqual(report['ranked'], [])
        self.assertEqual(len(report['earnings_unverified_watchlist']), 1)

    def test_budget_boundary_and_no_budget_assumption(self):
        self.assertFalse(rules.scan(self.dataset)['budget_checked'])
        self.assertEqual(rules.scan(self.dataset, 9000)['qualified_count'], 1)
        report = rules.scan(self.dataset, 8999)
        self.assertEqual(report['ranked'], [])
        self.assertIn('cash-budget', report['results'][0]['failed_rules'])
        self.row['earnings'] = None
        self.assertEqual(rules.scan(self.dataset, 8999)['earnings_unverified_watchlist'], [])
        for value in (-1, 0, True):
            with self.assertRaises(ValueError): rules.scan(self.dataset, value)

    def test_sort_maximizes_gross_bid_yield_and_ties_are_stable(self):
        other = copy.deepcopy(self.row)
        other.update(code='US.TEST261120P89000', strike=89, snapshot_strike=89)
        self.dataset['contracts'].append(other)
        self.assertEqual(rules.scan(self.dataset)['ranked_codes'][0], other['code'])
        other.update(strike=90, snapshot_strike=90)
        self.assertEqual(rules.scan(self.dataset)['ranked_codes'], sorted([self.row['code'], other['code']]))

    def test_hard_filters_cannot_be_offset_by_high_yield(self):
        self.row.update(bid=10, ask=10.1, delta=-.8)
        report = rules.scan(self.dataset)
        self.assertEqual(report['ranked'], [])
        self.assertIn('max-delta', report['results'][0]['failed_rules'])

    def test_bad_quotes_and_identity_mismatch_exclude_contract(self):
        original = copy.deepcopy(self.row)
        for changes in ({'bid': 0}, {'ask': 1.4}, {'bid': None}, {'bid': True},
                        {'snapshot_symbol': 'US.OTHER'}, {'snapshot_shares': 50},
                        {'snapshot_strike': 95}, {'snapshot_option_type': 'CALL'}, {'delta': .2}):
            self.dataset['contracts'] = [dict(original, **changes)]
            result = rules.scan(self.dataset)
            self.assertEqual(result['qualified_count'], 0, changes)
            self.assertEqual(result['results'][0]['status'], 'invalid_data', changes)

    def test_previous_session_and_nonstandard_contracts_fail(self):
        self.row['snapshot_update_time'] = '2026-10-15 15:59:00'
        self.assertIn('same-session-snapshot', rules.scan(self.dataset)['results'][0]['failed_rules'])
        self.row['snapshot_update_time'] = '2026-10-16 15:59:00'
        self.row['standard_type'] = 'NON_STANDARD'
        self.assertIn('standard-contract', rules.scan(self.dataset)['results'][0]['failed_rules'])

    def test_rules_fingerprints_change_and_typo_fails_fast(self):
        original = rules.scan(self.dataset)
        rules.RULES[5] = ('otm-buffer', 'otm_pct', '>=', 15)
        changed = rules.scan(self.dataset)
        self.assertNotEqual(original['rules_sha256'], changed['rules_sha256'])
        self.assertEqual(changed['qualified_count'], 0)
        rules.RULES[5] = ('otm-buffer', 'unknown_metric', '>=', 15)
        with self.assertRaisesRegex(ValueError, 'Unknown rule metric'): rules.scan(self.dataset)
        rules.RULES = copy.deepcopy(self.original_rules)
        rules.SORT_ORDER = [('unknown_metric', 'desc')]
        with self.assertRaisesRegex(ValueError, 'Unknown sort metric'): rules.scan(self.dataset)

    def test_input_is_not_mutated_and_duplicate_or_bad_asof_rejected(self):
        before = copy.deepcopy(self.dataset)
        self.assertEqual(rules.scan(self.dataset), rules.scan(self.dataset))
        self.assertEqual(self.dataset, before)
        self.dataset['contracts'].append(copy.deepcopy(self.row))
        with self.assertRaisesRegex(ValueError, 'duplicate'): rules.scan(self.dataset)
        self.dataset = copy.deepcopy(before)
        self.dataset['session_date'] = '2026-10-17'
        with self.assertRaises(ValueError): rules.scan(self.dataset)

    def test_zero_dte_and_future_snapshot_are_excluded(self):
        self.row.update(expiration='2026-10-16', snapshot_expiration='2026-10-16')
        self.assertEqual(rules.scan(self.dataset)['results'][0]['status'], 'invalid_data')
        self.row.update(expiration='2026-11-20', snapshot_expiration='2026-11-20', snapshot_update_time='2026-10-19 15:59:00')
        self.assertEqual(rules.scan(self.dataset)['results'][0]['status'], 'invalid_data')

    def test_cli_runs_from_standalone_file_without_sdk(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / 'input.json'; output = Path(temp) / 'out.json'; csv = Path(temp) / 'out.csv'
            source.write_text(json.dumps(self.dataset))
            command = [sys.executable, '-I', str(ROOT / 'put_rules.py'), str(source), '--output', str(output), '--csv-output', str(csv)]
            result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8')
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(output.read_text(encoding='utf-8'))
            self.assertEqual(report['qualified_count'], 1)
            self.assertEqual(report['best_recommendation']['strike'], 90)
            self.assertIn('daily_gross_return_pct', csv.read_text(encoding='utf-8'))
            self.assertIn('qualified,1,US.TEST', csv.read_text())
            source.write_text('{}'); output.unlink()
            self.assertNotEqual(subprocess.run(command, capture_output=True).returncode, 0)
            self.assertFalse(output.exists())


if __name__ == '__main__': unittest.main()
