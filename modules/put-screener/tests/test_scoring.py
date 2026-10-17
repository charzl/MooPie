import copy
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('scoring_rules', ROOT/'put_rules.py')
rules = importlib.util.module_from_spec(spec); spec.loader.exec_module(rules)


class ScoringTests(unittest.TestCase):
    def setUp(self):
        self.dataset = json.loads((ROOT/'example.json').read_text())
        self.row = self.dataset['contracts'][0]

    def result(self, config=None): return rules.recommend(self.dataset, configuration=config)['results'][0]

    def test_scores_reconcile_with_contributions_and_stress_payoff(self):
        result = self.result(); m, scoring = result['metrics'], result['scoring']
        self.assertAlmostEqual(m['stress_loss_pct'], 100*850/9000)
        self.assertEqual(scoring['stress_pnl_before_costs'], -850)
        self.assertAlmostEqual(m['risk_score'], sum(c['contribution'] for c in scoring['components']))
        self.assertAlmostEqual(m['composite_score'], scoring['return_contribution']+scoring['safety_contribution'])
        self.assertEqual(scoring['evidence_coverage_pct'], 100)
        for metric in ('risk_score', 'return_score', 'composite_score'):
            self.assertGreaterEqual(m[metric], 0); self.assertLessEqual(m[metric], 100)

    def test_risk_increases_with_delta_worse_spread_and_less_market_depth(self):
        before = self.result()['metrics']['risk_score']
        self.row['delta'] = -.29
        self.assertGreater(self.result()['metrics']['risk_score'], before)
        before = self.result()['metrics']['risk_score']
        self.row.update(ask=1.7, bid_size=1, open_interest=0)
        self.assertGreater(self.result()['metrics']['risk_score'], before)

    def test_stress_parameters_change_loss_and_score_but_never_filters(self):
        normal = self.result()
        worse = self.result(dict(scoring=dict(parameters=dict(stress_drop_pct=30))))
        self.assertGreater(worse['metrics']['stress_loss_pct'], normal['metrics']['stress_loss_pct'])
        self.assertGreater(worse['metrics']['risk_score'], normal['metrics']['risk_score'])
        self.assertEqual(worse['failed_rules'], normal['failed_rules'])
        self.row.update(strike=70, snapshot_strike=70)
        deep_otm = self.result()
        self.assertEqual(deep_otm['metrics']['stress_loss_pct'], 0)
        self.assertGreater(deep_otm['metrics']['max_loss_before_costs'], 0)

    def test_missing_evidence_is_penalized_and_flagged_not_treated_as_safe(self):
        known = self.result()
        self.row['earnings'] = None; self.dataset['daily_series'] = []
        unknown = self.result()
        self.assertGreater(unknown['metrics']['risk_score'], known['metrics']['risk_score'])
        self.assertEqual(set(unknown['scoring']['missing_components']), {'trend', 'earnings'})
        self.assertEqual(unknown['scoring']['evidence_coverage_pct'], 65)
        self.assertTrue(unknown['eligible'])
        parts = {c['id']: c for c in unknown['scoring']['components']}
        self.assertEqual(parts['trend']['score'], 100)
        self.assertFalse(parts['earnings']['known'])

    def test_known_earnings_conflict_is_risky_and_filter_independent(self):
        base = self.result()
        self.row['earnings']['date'] = self.dataset['session_date']
        crossed = self.result()
        self.assertGreater(crossed['metrics']['risk_score'], base['metrics']['risk_score'])
        strict = self.result(dict(filters={'earnings-buffer': dict(enabled=True)}))
        self.assertFalse(strict['eligible'])
        self.assertEqual(strict['metrics']['risk_score'], crossed['metrics']['risk_score'])

    def test_weights_are_normalized_and_no_candidate_or_filter_can_change_scores(self):
        before = copy.deepcopy(self.dataset)
        config = dict(scoring=dict(weights={key: value/2 for key, value in rules.RISK_WEIGHTS.items()}))
        normal = self.result(); scaled = self.result(config)
        self.assertEqual(normal['metrics']['risk_score'], scaled['metrics']['risk_score'])
        self.assertEqual(self.dataset, before)
        self.dataset['contracts'].append(dict(self.row, code='US.OTHER', bid=5, ask=5.1))
        self.assertEqual(normal['metrics']['return_score'], self.result()['metrics']['return_score'])
        self.assertEqual(normal['scoring'], self.result(dict(filters={'volume': dict(enabled=True, threshold=99999)}))['scoring'])

    def test_return_scale_has_explicit_pct_units_and_cap(self):
        m = self.result()['metrics']
        config = dict(scoring=dict(parameters=dict(daily_return_target_pct=m['daily_gross_return_pct'])))
        self.assertAlmostEqual(self.result(config)['metrics']['return_score'], 100)
        self.row.update(bid=10, ask=10.1)
        self.assertEqual(self.result(config)['metrics']['return_score'], 100)

    def test_three_views_and_extreme_preferences_produce_reproducible_top_ten(self):
        other = dict(self.row, code='US.TEST-HIGH-RETURN', bid=2, ask=2.1, delta=-.29)
        self.row['delta'] = -.05
        self.dataset['contracts'].append(other)
        config = dict(scoring=dict(weights={key: int(key == 'delta') for key in rules.RISK_WEIGHTS}),
                      sort_order=rules.RANKING_SORT_ORDERS['balanced'])
        config['scoring']['parameters'] = dict(return_weight=1)
        returns = rules.recommend(self.dataset, configuration=config)
        self.assertEqual(returns['best_research_code'], other['code'])
        config['scoring']['parameters']['return_weight'] = 0
        safety = rules.recommend(self.dataset, configuration=config)
        self.assertEqual(safety['best_research_code'], self.row['code'])
        self.assertEqual(set(returns['ranked_codes']), set(safety['ranked_codes']))
        self.assertEqual(returns['ranking_views']['return'][0], other['code'])
        self.assertEqual(returns['ranking_views']['risk'][0], self.row['code'])
        self.row['delta'] = -.9
        self.assertNotIn(self.row['code'], rules.recommend(self.dataset, configuration=config)['ranked_codes'])

    def test_invalid_scoring_configuration_is_rejected_before_evaluating_data(self):
        for bad in (None, [], {'extra': 2}, {'weights': {'typo': 10}}, {'parameters': {'typo': 1}},
                    {'weights': {key: 0 for key in rules.RISK_WEIGHTS}},
                    {'weights': {'delta': -1}}, {'parameters': {'return_weight': 1.1}},
                    {'parameters': {'stress_drop_pct': 0}}, {'parameters': {'delta_high': float('nan')}},
                    {'parameters': {'daily_return_target_pct': True}}):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                rules.recommend({}, configuration=dict(scoring=bad))

    def test_cli_rank_by_preserves_scores_and_csv_component_evidence(self):
        import csv, subprocess, sys, tempfile
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); output=root/'out.json'; csv_path=root/'out.csv'
            process = subprocess.run([sys.executable, '-X', 'utf8', str(ROOT/'put_rules.py'), str(ROOT/'example.json'),
                '--rank-by', 'risk', '--top', '10', '--output', str(output), '--csv-output', str(csv_path)], capture_output=True)
            self.assertEqual(process.returncode, 0, process.stderr)
            report = json.loads(output.read_text(encoding='utf-8'))
            self.assertEqual(report['sort_order'][0], ['risk_score', 'asc'])
            with csv_path.open(encoding='utf-8', newline='') as stream: row = next(csv.DictReader(stream))
            self.assertEqual(float(row['risk_score']), report['best_recommendation']['risk_score'])
            self.assertEqual(float(row['delta_risk_score']), report['best_recommendation']['scoring']['components'][0]['score'])


if __name__ == '__main__': unittest.main()
