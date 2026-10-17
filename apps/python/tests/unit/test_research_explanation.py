import json
from html import unescape
from pathlib import Path
import unittest

from moopython.research import load_rules
from moopython.research_explanation import condition_text, explanation_html, rules_html

ROOT = Path(__file__).resolve().parents[4]


class ResearchExplanationTests(unittest.TestCase):
    def test_conditions_use_report_thresholds_including_changed_rules(self):
        report = dict(trend_rules=[], rules=[('min-days', 'days_to_expiry', '>=', 28)],
                      sort_order=[('annualized_gross_return_pct', 'desc')])
        text = rules_html(report)
        self.assertIn('28', text)
        self.assertNotIn('21', text)
        self.assertIn('从高到低', text)

    def test_evidence_includes_actual_trend_values_every_rule_and_data_errors(self):
        dataset = json.loads((ROOT/'modules/put-screener/example.json').read_text())
        dataset['contracts'][0]['earnings'] = None
        report = load_rules().scan(dataset)
        trend = next(iter(report['underlyings'].values()))
        trend['allowed'] = False
        rsi = next(rule for rule in trend['rules'] if rule['id'] == 'rsi-floor')
        rsi.update(actual=37.2, passed=False)
        text = unescape(explanation_html(report))
        for rule in report['rules']: self.assertIn(condition_text(rule), text)
        self.assertIn('37.2', text)
        self.assertIn('RSI14 >= 40', text)
        self.assertIn('未通过', text)
        self.assertIn('1 / 1', text)
        self.assertIn('不能将各项数量相加', text)
        dataset['contracts'][0]['bid'] = 0
        text = explanation_html(load_rules().scan(dataset))
        self.assertIn('缺少有效双边报价', text)
        self.assertIn('0 / 0', text)
