import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from datetime import date, timedelta

from moomoo_rules import evaluate, load_rules, scan
from moomoo_rules.engine import canonical_hash


def series(slope=0.1, count=250):
    bars = []
    day = date(2025, 1, 2)
    while len(bars) < count:
        if day.weekday() < 5:
            close = 100 + slope * len(bars)
            bars.append(dict(date=day.isoformat(), open=close, high=close+1, low=close-1,
                             close=close, volume=1500 if len(bars) == count-1 else 1000,
                             complete=True))
        day += timedelta(days=1)
    return dict(symbol='US.TEST', interval='1d', adjustment='qfq', session='regular',
                source='synthetic-unit-test-not-market-data', bars=bars)


class EngineTests(unittest.TestCase):
    def setUp(self):
        self.data = series()
        self.day = self.data['bars'][-1]['date']
        self.rules = load_rules()

    def evaluate(self):
        return evaluate(self.data, self.rules, self.day)

    def test_known_sma_slope_and_volume(self):
        result = self.evaluate()
        metrics = result['metrics']
        self.assertAlmostEqual(metrics['ma50'], 122.45)
        self.assertAlmostEqual(metrics['ma20'], 123.95)
        self.assertAlmostEqual(metrics['ma200'], 114.95)
        self.assertAlmostEqual(metrics['ma50_slope_5_pct'], 100*(122.45/121.95-1))
        self.assertAlmostEqual(metrics['volume_ratio_20'], 1.5)
        self.assertTrue(result['eligible'])
        self.assertEqual(result['score'], 100)

    def test_wilder_rsi_and_atr_known_series(self):
        self.assertAlmostEqual(self.evaluate()['metrics']['rsi14'], 100)
        self.assertAlmostEqual(self.evaluate()['metrics']['atr14'], 2)
        for slope, expected in ((0, 50), (-0.1, 0)):
            data = series(slope)
            result = evaluate(data, self.rules, data['bars'][-1]['date'])
            self.assertAlmostEqual(result['metrics']['rsi14'], expected)
            self.assertAlmostEqual(result['metrics']['atr14'], 2)

    def test_required_failure_prevents_ranking_even_with_other_points(self):
        self.rules['rules'][0]['value'] = 50
        result = self.evaluate()
        self.assertFalse(result['eligible'])
        self.assertEqual(result['score'], 75)
        report = scan(dict(schema=1, as_of=self.day, series=[self.data]), self.rules)
        self.assertEqual(report['ranked_symbols'], [])
        self.assertFalse(result['rules'][0]['passed'])

    def test_wilder_mixed_changes_and_gap_true_range(self):
        self.data = series(0)
        # Most history is flat. Last two moves: +10, -5. Last two TRs: 11, 6.
        for index, close in ((-2, 110), (-1, 105)):
            self.data['bars'][index].update(open=close, high=close+1, low=close-1, close=close)
        metrics = self.evaluate()['metrics']
        gain = (10/14) * 13/14
        loss = 5/14
        self.assertAlmostEqual(metrics['rsi14'], 100 - 100/(1+gain/loss))
        self.assertAlmostEqual(metrics['atr14'], (((2*13+11)/14)*13+6)/14)

    def test_weight_scale_does_not_change_score(self):
        expected = self.evaluate()['score']
        for rule in self.rules['rules']: rule['weight'] *= 1e300
        self.assertEqual(self.evaluate()['score'], expected)

    def test_boundary_operators(self):
        for op, passed in (('>', False), ('>=', True), ('<', False), ('<=', True), ('==', True)):
            with self.subTest(op=op):
                self.rules['rules'][0].update(metric='close', op=op, value=124.9)
                self.assertEqual(self.evaluate()['rules'][0]['passed'], passed)

    def test_rule_changes_are_external_and_fingerprinted(self):
        original = self.evaluate()
        with tempfile.TemporaryDirectory() as work:
            path = Path(work)/'rules.json'
            self.rules['version'] = '1.1.0'
            self.rules['rules'][-1]['value'] = 2
            path.write_text(json.dumps(self.rules))
            result = evaluate(self.data, load_rules(path), self.day)
        self.assertNotEqual(result['ruleset_sha256'], original['ruleset_sha256'])
        self.assertEqual(result['ruleset_version'], '1.1.0')
        self.assertEqual(result['score'], 90)

    def test_unsafe_or_incompatible_rules_rejected(self):
        cases = []
        for key, value in (('schema', 2), ('engine_major', 9), ('version', 'latest')):
            config = copy.deepcopy(self.rules); config[key] = value; cases.append(config)
        for key, value in (('metric', '__import__'), ('op', 'eval'), ('weight', -1), ('value', float('nan')), ('required', 'yes')):
            config = copy.deepcopy(self.rules); config['rules'][0][key] = value; cases.append(config)
        config = copy.deepcopy(self.rules); config['rules'].append(config['rules'][0]); cases.append(config)
        for config in cases:
            with self.subTest(config=config):
                with self.assertRaises(ValueError):
                    evaluate(self.data, config, self.day)

    def test_bad_bars_rejected(self):
        original = copy.deepcopy(self.data)
        for field, value in (('complete', False), ('close', float('nan')), ('volume', -1), ('low', 999), ('close', True)):
            with self.subTest(field=field, value=value):
                self.data = copy.deepcopy(original)
                self.data['bars'][-1][field] = value
                with self.assertRaises(ValueError): self.evaluate()

    def test_insufficient_stale_future_duplicate_and_unordered_dates(self):
        original = copy.deepcopy(self.data)
        self.data['bars'] = self.data['bars'][-199:]
        with self.assertRaisesRegex(ValueError, '200'): self.evaluate()
        for day in ('2026-12-31', '2025-01-01'):
            self.data = copy.deepcopy(original)
            with self.assertRaises(ValueError): evaluate(self.data, self.rules, day)
        for index in (0, -2):
            self.data = copy.deepcopy(original)
            self.data['bars'][-1]['date'] = self.data['bars'][index]['date']
            with self.assertRaises(ValueError): self.evaluate()

    def test_unadjusted_extended_and_zero_volume_rejected(self):
        for field, value in (('adjustment', 'none'), ('session', 'all'), ('interval', '1m')):
            data = copy.deepcopy(self.data); data[field] = value
            with self.assertRaises(ValueError): evaluate(data, self.rules, self.day)
        for bar in self.data['bars']: bar['volume'] = 0
        with self.assertRaisesRegex(ValueError, 'volume history'): self.evaluate()

    def test_invalid_stock_is_not_a_candidate_and_ties_are_stable(self):
        other = copy.deepcopy(self.data); other['symbol'] = 'US.AAA'
        invalid = copy.deepcopy(self.data); invalid['symbol'] = 'US.BAD'; invalid['bars'][-1]['complete'] = False
        report = scan(dict(schema=1, as_of=self.day, series=[self.data, other, invalid]), self.rules)
        self.assertEqual(report['ranked_symbols'], ['US.AAA', 'US.TEST'])
        self.assertEqual(report['results'][-1]['status'], 'invalid_data')
        self.assertIsNone(report['results'][-1]['score'])
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            scan(dict(schema=1, as_of=self.day, series=[self.data, self.data]), self.rules)

    def test_reproducible_and_inputs_not_mutated(self):
        before = canonical_hash(dict(data=self.data, rules=self.rules))
        first = self.evaluate()
        self.assertEqual(first, self.evaluate())
        self.assertEqual(canonical_hash(dict(data=self.data, rules=self.rules)), before)
        self.data['bars'][0]['volume'] += 1
        self.assertNotEqual(self.evaluate()['data_sha256'], first['data_sha256'])

    def test_json_cli_contract(self):
        with tempfile.TemporaryDirectory() as work:
            root = Path(work); source = root/'input.json'; output = root/'output.json'
            source.write_text(json.dumps(dict(schema=1, as_of=self.day, series=[self.data])))
            subprocess.run([sys.executable, '-m', 'moomoo_rules.cli', str(source), '--output', str(output)], check=True, env=os.environ.copy())
            result = json.loads(output.read_text())
            self.assertEqual(result['ranked_symbols'], ['US.TEST'])
            self.assertEqual(result['results'][0]['metrics']['ma50'], self.evaluate()['metrics']['ma50'])
            source.write_text('{}'); output.unlink()
            failed = subprocess.run([sys.executable, '-m', 'moomoo_rules.cli', str(source), '--output', str(output)], capture_output=True)
            self.assertEqual(failed.returncode, 2)
            self.assertFalse(output.exists())


if __name__ == '__main__': unittest.main()
