import copy
from datetime import date, timedelta
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('recommendation_rules', ROOT/'put_rules.py')
rules = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rules)


class RecommendationTests(unittest.TestCase):
    def setUp(self):
        self.dataset = json.loads((ROOT/'example.json').read_text())

    def add(self, dte, strike, bid, delta=-.2):
        row = copy.deepcopy(self.dataset['contracts'][0])
        expiry = (date.fromisoformat(self.dataset['session_date']) + timedelta(days=dte)).isoformat()
        row.update(code=f'US.TEST-{expiry}-{strike}', expiration=expiry, snapshot_expiration=expiry,
                   strike=strike, snapshot_strike=strike, bid=bid, ask=bid*1.05, delta=delta)
        self.dataset['contracts'].append(row)
        return row

    def test_daily_return_uses_full_strike_cash_and_calendar_days(self):
        best = rules.recommend(self.dataset)['best_recommendation']
        self.assertAlmostEqual(best['daily_gross_return_pct'], 100*150/9000/35)
        self.assertAlmostEqual(best['daily_gross_return_pct']*365, best['annualized_gross_return_pct'])
        self.assertEqual(best['scenarios'][0]['pnl_before_costs'], 150)
        self.assertEqual(best['scenarios'][2]['pnl_before_costs'], -850)
        self.assertEqual(best['scenarios'][-1]['pnl_before_costs'], -best['max_loss_before_costs'])
        self.assertTrue(best['reasons'])
        self.assertTrue(best['tradeoffs'])

    def test_rank_normalizes_premium_for_both_capital_and_time(self):
        short = self.add(14, 80, 1)
        self.add(60, 90, 3)  # More credit, lower daily yield.
        report = rules.recommend(self.dataset)
        self.assertEqual(report['best_recommendation']['code'], short['code'])
        yields = [r['metrics']['daily_gross_return_pct'] for r in report['ranked']]
        self.assertEqual(yields, sorted(yields, reverse=True))

    def test_higher_yield_cannot_override_any_enabled_boundary(self):
        cases = [dict(delta=-.9), dict(bid_size=0), dict(suspension=True),
                 dict(snapshot_update_time='2026-10-15 15:59:00'), dict(ask=30),
                 dict(strike=110, snapshot_strike=110),
                 dict(expiration='2027-03-19', snapshot_expiration='2027-03-19')]
        for changes in cases:
            with self.subTest(changes=changes):
                dataset = copy.deepcopy(self.dataset)
                dataset['contracts'][0].update(dict(bid=20, ask=21) | changes)
                report = rules.recommend(dataset)
                self.assertEqual(report['decision'], 'no_candidates_within_boundaries')
                self.assertIsNone(report['best_recommendation'])
                self.assertEqual(report['recommendations'], [])
        self.assertFalse(rules.recommend(self.dataset, budget=8999)['recommendations'])

    def test_soft_evidence_does_not_veto_unless_explicitly_enabled(self):
        self.dataset['contracts'][0].update(earnings=None, open_interest=0, volume=0)
        self.dataset['daily_series'] = []
        report = rules.recommend(self.dataset)
        self.assertEqual(report['qualified_count'], 1)
        self.assertIn('财报日期或日历完整性未验证', report['best_recommendation']['risk_notes'])
        self.assertIn('历史日线无法验证', report['best_recommendation']['risk_notes'])
        self.assertFalse(report['ranked'][0]['live_review_ready'])
        self.assertFalse(rules.scan(self.dataset)['ranked'])  # Legacy strict API remains available.
        for rid in ('underlying-trend', 'earnings-checked', 'earnings-buffer', 'open-interest', 'volume'):
            with self.subTest(rid=rid):
                self.assertFalse(rules.recommend(self.dataset, configuration=dict(filters={rid: dict(enabled=True)}))['recommendations'])

    def test_top_ten_is_strict_order_without_forcing_distinct_dates(self):
        second = self.add(35, 85, 1.3)
        later = self.add(60, 80, .5)
        last = self.add(90, 70, .2)
        report = rules.recommend(self.dataset)
        self.assertEqual(report['ranked_codes'][1], second['code'])
        self.assertEqual([r['code'] for r in report['recommendations']], report['ranked_codes'])
        self.assertEqual(len(report['expiration_comparisons']), 3)
        self.assertEqual(len(rules.recommend(self.dataset, top_n=1)['recommendations']), 1)
        self.dataset['contracts'] = self.dataset['contracts'][:2]
        self.assertEqual(len(rules.recommend(self.dataset)['recommendations']), 2)
        for index in range(15): self.add(14+index, 80-index, .5+index*.01)
        report = rules.recommend(self.dataset)
        self.assertEqual(len(report['recommendations']), 10)
        self.assertEqual([r['code'] for r in report['recommendations']], report['ranked_codes'][:10])

    def test_partial_overrides_validate_against_new_profile_and_stay_immutable(self):
        config = dict(filters={'max-days': dict(threshold=14)})
        before = copy.deepcopy(self.dataset)
        defaults = rules.recommendation_configuration()
        self.assertEqual(rules.recommend(self.dataset, configuration=config)['qualified_count'], 0)
        self.assertEqual(rules.recommendation_configuration(), defaults)
        self.assertEqual(config, dict(filters={'max-days': dict(threshold=14)}))
        self.assertEqual(self.dataset, before)
        for bad in ({'extra': 1}, {'filters': {'fake': {}}}, {'filters': []}, {'filters': {'spread': 2}},
                    {'filters': {'spread': {'enabled': 'yes'}}}, {'schema': 2},
                    {'filters': {'standard-contract': {'enabled': False}}}):
            with self.subTest(bad=bad), self.assertRaises(ValueError): rules.recommend(self.dataset, configuration=bad)

    def test_custom_sort_remains_independent_of_filters_and_is_disclosed(self):
        self.add(14, 80, 1)
        normal = rules.recommend(self.dataset)
        custom = rules.recommend(self.dataset, configuration=dict(sort_order=[['cash_collateral', 'desc']]))
        self.assertEqual(set(normal['ranked_codes']), set(custom['ranked_codes']))
        self.assertNotEqual(normal['best_research_code'], custom['best_research_code'])
        self.assertEqual(custom['comparison_basis']['actual_sort_order'], [['cash_collateral', 'desc']])
        self.assertEqual(normal, rules.recommend(self.dataset))

    def test_duration_and_cost_presets_choose_distinct_correct_leaders(self):
        nearest = self.add(7, 85, .5)
        cheapest = self.add(60, 70, .2)
        base = rules.recommend(self.dataset)
        for mode, expected in [('duration', nearest), ('cost', cheapest)]:
            with self.subTest(mode=mode):
                report = rules.recommend(self.dataset, configuration=dict(sort_order=rules.RANKING_SORT_ORDERS[mode]))
                self.assertEqual(report['best_research_code'], expected['code'])
                self.assertEqual(set(base['ranked_codes']), set(report['ranked_codes']))
                self.assertEqual(report['ranking_views'][mode][0], expected['code'])
                self.assertEqual(report['best_recommendation'][mode+'_rank'], 1)
                for row in report['ranked']:
                    self.assertEqual(row['metrics']['cash_collateral'], row['metrics']['strike']*100)


if __name__ == '__main__': unittest.main()
