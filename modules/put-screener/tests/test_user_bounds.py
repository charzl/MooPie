import copy
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('user_bound_rules', ROOT/'put_rules.py')
rules = importlib.util.module_from_spec(spec); spec.loader.exec_module(rules)


class UserBoundsTests(unittest.TestCase):
    def setUp(self): self.dataset = json.loads((ROOT/'example.json').read_text())

    def filtered(self, bounds):
        return rules.recommend(self.dataset, configuration=dict(filters={
            key: dict(enabled=True, threshold=value) for key, value in bounds.items()}))

    def test_cost_bounds_are_strict_dollar_amounts_and_optional(self):
        self.assertEqual(self.filtered({'min-cost': 8999, 'max-cost': 9001})['qualified_count'], 1)
        self.assertEqual(self.filtered({'min-cost': 9000})['qualified_count'], 0)
        self.assertEqual(self.filtered({'max-cost': 9000})['qualified_count'], 0)
        self.assertEqual(rules.recommend(self.dataset)['qualified_count'], 1)
        with self.assertRaises(ValueError): self.filtered({'min-cost': 9000, 'max-cost': 9000})
        with self.assertRaises(ValueError): self.filtered({'min-cost': 10000, 'max-cost': 9000})

    def test_return_and_risk_boundaries_use_unrounded_metrics(self):
        best = rules.recommend(self.dataset)['best_recommendation']
        self.assertEqual(self.filtered({'min-daily-return': best['daily_gross_return_pct']})['qualified_count'], 0)
        self.assertEqual(self.filtered({'max-risk': best['risk_score']})['qualified_count'], 0)
        report = self.filtered({'min-daily-return': best['daily_gross_return_pct']-.00001,
                                'max-risk': best['risk_score']+.00001})
        self.assertEqual(report['qualified_count'], 1)
        self.assertEqual(best['risk_score'], report['best_recommendation']['risk_score'])
        with self.assertRaises(ValueError): self.filtered({'max-risk': 101})

    def test_expiry_before_excludes_the_cutoff_day_and_validates_real_dates(self):
        self.assertEqual(self.filtered({'expiry-before': '2026-11-21'})['qualified_count'], 1)
        report = self.filtered({'expiry-before': '2026-11-20'})
        self.assertEqual(report['qualified_count'], 0)
        self.assertIn('expiry-before', report['results'][0]['failed_rules'])
        evidence = next(r for r in report['results'][0]['rules'] if r['id'] == 'expiry-before')
        self.assertEqual(evidence['actual'], '2026-11-20')
        for invalid in (None, 42, '2026/11/21', '2026-02-30'):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError): self.filtered({'expiry-before': invalid})

    def test_combined_filters_apply_to_all_contracts_before_top_ten(self):
        base = self.dataset['contracts'][0]
        for index in range(12):
            self.dataset['contracts'].append(dict(base, code=f'US.EXPENSIVE-{index}',
                strike=95, snapshot_strike=95, bid=4, ask=4.1))
            self.dataset['contracts'].append(dict(base, code=f'US.AFFORDABLE-{index}',
                strike=85, snapshot_strike=85, bid=1+index*.01, ask=1.1+index*.01))
        before = copy.deepcopy(self.dataset)
        unfiltered = rules.recommend(self.dataset)
        self.assertTrue(all(r['code'].startswith('US.EXPENSIVE') for r in unfiltered['recommendations']))
        report = self.filtered({'min-cost': 8000, 'max-cost': 9000, 'min-daily-return': .02,
                                'max-risk': 90, 'expiry-before': '2026-11-21'})
        self.assertEqual(report['qualified_count'], 12)
        self.assertEqual(len(report['recommendations']), 10)
        self.assertTrue(all(r['code'].startswith('US.AFFORDABLE') for r in report['recommendations']))
        self.assertEqual([r['code'] for r in report['recommendations']], report['ranked_codes'][:10])
        self.assertEqual(self.dataset, before)

    def test_changed_risk_model_is_rechecked_against_the_same_user_limit(self):
        baseline = rules.recommend(self.dataset)['best_recommendation']['risk_score']
        config = dict(filters={'max-risk': dict(enabled=True, threshold=baseline+1)})
        first = rules.recommend(self.dataset, configuration=config)
        self.assertEqual(first['qualified_count'], 1)
        config['scoring'] = dict(weights={key: 100 if key == 'stress_loss' else 0 for key in rules.RISK_WEIGHTS})
        second = rules.recommend(self.dataset, configuration=config)
        self.assertEqual(second['qualified_count'], 0)
        self.assertEqual(first['configuration']['filters'], second['configuration']['filters'])


if __name__ == '__main__': unittest.main()
