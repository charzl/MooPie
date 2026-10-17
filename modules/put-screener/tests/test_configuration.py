import copy
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('configurable_rules', ROOT/'put_rules.py')
rules = importlib.util.module_from_spec(spec); spec.loader.exec_module(rules)


class ConfigurationTests(unittest.TestCase):
    def setUp(self):
        self.dataset = json.loads((ROOT/'example.json').read_text())
        self.row = self.dataset['contracts'][0]

    def test_filter_thresholds_are_explicit_and_do_not_mutate_defaults(self):
        before = rules.default_configuration()
        tight = dict(filters={'open-interest': dict(threshold=999999)})
        self.assertFalse(rules.scan(self.dataset, configuration=tight)['ranked'])
        relaxed = dict(filters={'open-interest': dict(threshold=0)})
        report = rules.scan(self.dataset, configuration=relaxed)
        self.assertEqual(report['qualified_count'], 1)
        self.assertEqual(rules.default_configuration(), before)
        self.assertNotEqual(report['rules_sha256'], rules.scan(self.dataset)['rules_sha256'])

    def test_sort_changes_order_without_changing_filtered_membership(self):
        other = dict(self.row, code='US.TEST261120P89000', strike=89, snapshot_strike=89,
                     bid=1.49, ask=1.59, delta=-.25)
        self.dataset['contracts'].append(other)
        default = rules.scan(self.dataset)
        changed = rules.scan(self.dataset, configuration=dict(sort_order=[['abs_delta', 'asc']]))
        self.assertEqual(default['ranked_codes'][0], other['code'])
        self.assertEqual(changed['ranked_codes'][0], self.row['code'])
        self.assertEqual(set(default['ranked_codes']), set(changed['ranked_codes']))
        self.assertEqual([r['failed_rules'] for r in default['results']], [r['failed_rules'] for r in changed['results']])

    def test_explicitly_disabled_earnings_filters_keep_unknown_warning(self):
        self.row['earnings'] = None
        self.assertFalse(rules.scan(self.dataset)['ranked'])
        config = dict(filters={rid: dict(enabled=False) for rid in rules.EARNINGS_RULES})
        report = rules.scan(self.dataset, configuration=config)
        self.assertEqual(report['qualified_count'], 1)
        best = report['ranked'][0]
        self.assertIn('财报日期或日历完整性未验证', best['warnings'])
        self.assertFalse(best['live_review_ready'])
        self.assertFalse(report['earnings_unverified_watchlist'])

    def test_disabled_trend_filter_can_keep_candidate_when_history_is_missing(self):
        self.dataset['daily_series'] = []
        self.assertFalse(rules.scan(self.dataset)['ranked'])
        report = rules.scan(self.dataset, configuration=dict(filters={'underlying-trend': dict(enabled=False)}))
        self.assertEqual(report['qualified_count'], 1)
        self.assertIn('历史日线无法验证', report['ranked'][0]['warnings'])

    def test_individual_trend_filter_can_be_changed_without_changing_trend_description(self):
        config = dict(trend_filters={'rsi-floor': dict(threshold=100)})
        self.assertEqual(rules.scan(self.dataset, configuration=config)['qualified_count'], 1)
        self.dataset['daily_series'][0]['bars'][-1]['close'] -= .2
        default = rules.scan(self.dataset)
        selected = rules.scan(self.dataset, configuration=dict(trend_filters={'momentum-not-deteriorating': dict(enabled=False)}))
        self.assertEqual(default['underlyings']['US.TEST']['state'], selected['underlyings']['US.TEST']['state'])
        self.assertNotIn('momentum-not-deteriorating', selected['underlyings']['US.TEST']['failed_rules'])

    def test_all_optional_filters_off_still_cannot_admit_bad_quotes_or_nonstandard_contracts(self):
        config = rules.default_configuration()
        for rid, options in config['filters'].items():
            if rid not in rules.REQUIRED_FILTERS: options['enabled'] = False
        self.row['bid'] = 0
        self.assertEqual(rules.scan(self.dataset, configuration=config)['results'][0]['status'], 'invalid_data')
        self.row['bid'] = 1.5; self.row['standard_type'] = 'NON_STANDARD'
        self.assertFalse(rules.scan(self.dataset, configuration=config)['ranked'])
        with self.assertRaisesRegex(ValueError, 'cannot be disabled'):
            rules.scan(self.dataset, configuration=dict(filters={'standard-contract': dict(enabled=False)}))

    def test_relaxation_previews_match_explicit_rescans_and_never_change_input(self):
        self.row['earnings'] = None
        self.dataset['daily_series'] = []
        before = copy.deepcopy(self.dataset)
        report = rules.scan(self.dataset)
        for preview in report['relaxation_preview']:
            config = dict(filters={rid: dict(enabled=False) for rid in preview['disabled_filters']})
            self.assertEqual(preview['qualified_count'], rules.scan(self.dataset, configuration=config)['qualified_count'])
        self.assertEqual(self.dataset, before)
        self.assertFalse(report['ranked'])

    def test_invalid_configuration_is_rejected_before_processing_contracts(self):
        for config in ({'schema': True}, {'unknown': 1}, {'filters': {'typo': {}}},
                       {'filters': {'volume': {'enabled': 'false'}}},
                       {'filters': {'volume': {'threshold': float('nan')}}},
                       {'filters': {'min-days': {'threshold': 100}}},
                       {'filters': {'max-delta': {'threshold': 2}}},
                       {'sort_order': []}, {'sort_order': [['iv_pct', 'desc']]},
                       {'sort_order': [['bid', 'desc'], ['bid', 'asc']]},
                       {'trend_filters': {'rsi-floor': {'threshold': 101}}}):
            with self.subTest(config=config), self.assertRaises(ValueError): rules.scan(self.dataset, configuration=config)
