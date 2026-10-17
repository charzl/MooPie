import copy
import json
from pathlib import Path
import unittest

from moopython.research import analyze_put_dataset, load_rules, run_research

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
        self.assertEqual(result['report'], load_rules().recommend(self.dataset, per_symbol_limit=20))
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

    def test_missing_history_is_flagged_and_can_be_explicitly_made_a_veto(self):
        code = self.dataset['contracts'][0]['symbol']
        self.dataset['daily_series'][0]['bars'].pop()
        result = run_research(self.service(), code, 'put')
        self.assertTrue(result['report']['ranked'])
        self.assertIn('历史日线无法验证', result['report']['best_recommendation']['risk_notes'])
        config = dict(filters={'underlying-trend': dict(enabled=True)})
        self.assertFalse(run_research(self.service(), code, 'put', config)['report']['ranked'])
        with self.assertRaises(ValueError): run_research(self.service(), 'HK.00700', 'trend')

    def test_cached_data_can_be_refiltered_offline_and_keeps_original_time(self):
        import subprocess, sys, tempfile
        self.dataset['contracts'][0]['earnings'] = None
        code = self.dataset['contracts'][0]['symbol']
        config = dict(filters={rid: dict(enabled=False) for rid in ('earnings-checked', 'earnings-buffer')})
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); source = root/'input data.json'; settings = root/'filters.json'; output = root/'result.json'
            source.write_text(json.dumps(self.dataset), encoding='utf-8'); settings.write_text(json.dumps(config))
            process = subprocess.run([sys.executable, '-m', 'moopython.research_cli', 'put', code,
                '--input', str(source), '--config', str(settings), '--top', '20', '--port', '1', '--output', str(output)], capture_output=True)
            self.assertEqual(process.returncode, 0, process.stderr)
            result = json.loads(output.read_text(encoding='utf-8'))
            self.assertEqual(result['report']['qualified_count'], 1)
            self.assertEqual(result['report']['top_n_requested'], 20)
            self.assertEqual(result['collected_at'], self.dataset['collected_at'])
            self.assertEqual(result['input_dataset'], self.dataset)
        with self.assertRaisesRegex(ValueError, 'does not match'):
            analyze_put_dataset(self.dataset, 'NVDA', config)
