import copy
import json
from pathlib import Path
import unittest

from moopython.research import load_rules, run_research

ROOT = Path(__file__).resolve().parents[4]


class ResearchTests(unittest.TestCase):
    def setUp(self):
        self.dataset = json.loads((ROOT/'modules/put-screener/example.json').read_text())

    def service(self):
        dataset = self.dataset
        class Service:
            def collect_put_dataset(self, symbols, months):
                self.query = (symbols, months)
                return copy.deepcopy(dataset)
            def daily_bars(self, symbols):
                return dict(daily_series=dataset['daily_series'], decision_cutoff=dataset['collected_at'],
                            fetched_at=dataset['collected_at'])
        return Service()

    def test_put_reuses_independent_ranking_without_relaxing_rules(self):
        service = self.service(); code = self.dataset['contracts'][0]['symbol']
        result = run_research(service, code, 'put')
        self.assertEqual(service.query, ([code], 3))
        self.assertEqual(result['report']['ranked'], load_rules().scan(self.dataset)['ranked'])
        self.dataset['contracts'][0]['bid'] = 0
        self.assertFalse(run_research(self.service(), code, 'put')['report']['ranked'])

    def test_trend_has_indicators_levels_and_conditional_outlook(self):
        code = self.dataset['daily_series'][0]['symbol']
        result = run_research(self.service(), code, 'trend')['trend']
        self.assertEqual(result['status'], 'ok')
        self.assertIn('rsi14', result['metrics'])
        self.assertEqual(len(result['outlook']['levels']), 4)
        self.assertIn('MA50', result['outlook']['change_condition'])

    def test_missing_history_does_not_create_outlook(self):
        code = self.dataset['daily_series'][0]['symbol']
        self.dataset['daily_series'][0]['error'] = 'permission denied'
        with self.assertRaisesRegex(ValueError, 'permission denied'):
            run_research(self.service(), code, 'trend')

    def test_partial_and_invalid_data_stay_excluded(self):
        code = self.dataset['contracts'][0]['symbol']
        self.dataset['daily_series'][0]['bars'].pop()
        result = run_research(self.service(), code, 'put')
        self.assertFalse(result['report']['ranked'])
        with self.assertRaises(ValueError): run_research(self.service(), 'HK.00700', 'trend')
