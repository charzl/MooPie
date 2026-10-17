import json
import os
from pathlib import Path
import socket
import tempfile
import time
import unittest

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PySide6.QtCore import QDate, QProcess, QSettings, QTimer
from PySide6.QtGui import QFont, QRawFont
from PySide6.QtWidgets import QApplication
from moopython.research import load_rules
from moopython.research_ui import ResearchWindow
from moopython.research_controls import FilterSortDialog

ROOT = Path(__file__).resolve().parents[4]


class ResearchUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.window = ResearchWindow(QSettings(self.temp.name+'/settings.ini', QSettings.Format.IniFormat))
        self.dataset = json.loads((ROOT/'modules/put-screener/example.json').read_text())

    def tearDown(self):
        self.window.close(); self.app.processEvents(); self.temp.cleanup()

    def result(self):
        return dict(action='put', symbol=self.dataset['contracts'][0]['symbol'],
                    collected_at=self.dataset['collected_at'], report=load_rules().recommend(self.dataset))

    def test_packaged_font_has_both_chinese_and_latin_glyphs(self):
        font = QRawFont.fromFont(QFont('Noto Sans SC', 14))
        self.assertTrue(font.isValid())
        for character in '股票走势Put123': self.assertTrue(font.supportsCharacter(ord(character)), character)

    def test_new_profile_preserves_old_settings_and_reloads_explicit_boundaries(self):
        settings = self.window.settings
        old = json.dumps(load_rules().default_configuration())
        settings.setValue('filter_sort_configuration', old)
        self.window.close()
        self.window = ResearchWindow(settings)
        self.assertFalse(self.window.configuration['filters']['underlying-trend']['enabled'])
        chosen = load_rules().recommendation_configuration(dict(filters={'max-delta': dict(threshold=.12)}))
        settings.setValue('put_recommendation_configuration_v1', json.dumps(chosen))
        self.window.close()
        self.window = ResearchWindow(settings)
        self.assertEqual(self.window.configuration, chosen)
        self.assertEqual(settings.value('filter_sort_configuration'), old)

    def test_filter_editor_and_sort_editor_are_independent(self):
        dialog = FilterSortDialog(self.window.configuration, parent=self.window)
        try:
            metric, direction = dialog.sort_controls[0]
            metric.setCurrentIndex(metric.findData('cash_collateral')); direction.setCurrentIndex(direction.findData('asc'))
            original_sort = dialog.configuration()['sort_order']
            dialog.disable_optional()
            disabled = dialog.configuration()
            self.assertTrue(disabled['filters']['standard-contract']['enabled'])
            self.assertFalse(disabled['filters']['underlying-trend']['enabled'])
            self.assertEqual(disabled['sort_order'], original_sort)
            dialog.restore_filters()
            self.assertEqual(dialog.configuration()['sort_order'], original_sort)
            self.assertFalse(dialog.configuration()['filters']['underlying-trend']['enabled'])
            self.assertTrue(dialog.configuration()['filters']['max-delta']['enabled'])
        finally: dialog.close()

    def test_applying_filters_reuses_data_offline_and_persists_choices(self):
        self.window.port.setValue(1); self.window.symbol.setText('TEST')
        self.dataset['contracts'][0]['earnings'] = None
        result = self.result(); result['input_dataset'] = self.dataset
        self.window.display(result)
        errors = []
        def choose():
            dialog = self.app.activeModalWidget()
            try:
                self.assertIsInstance(dialog, FilterSortDialog)
                for rid in ('earnings-checked', 'earnings-buffer'):
                    dialog.controls[('filters', rid)][0].setChecked(False)
                metric, direction = dialog.sort_controls[0]
                metric.setCurrentIndex(metric.findData('cash_collateral')); direction.setCurrentIndex(direction.findData('asc'))
                dialog.configuration()
                dialog.apply()
            except Exception as error:
                errors.append(error)
                if dialog: dialog.reject()
        QTimer.singleShot(0, choose)
        self.window.show_rules()
        self.assertFalse(errors, errors)
        deadline = time.monotonic() + 15
        while self.window.process is not None and time.monotonic() < deadline:
            self.app.processEvents(); time.sleep(.01)
        self.assertIsNone(self.window.process)
        report = self.window.results['put']['report']
        self.assertEqual(report['qualified_count'], 1)
        self.assertEqual(report['collected_at'], self.dataset['collected_at'])
        self.assertIn('财报日期或日历完整性未验证', self.window.put_result.toPlainText())
        saved = json.loads(self.window.settings.value('put_recommendation_configuration_v1'))
        self.assertFalse(saved['filters']['earnings-checked']['enabled'])
        self.assertEqual(saved['sort_order'][0], ['cash_collateral', 'asc'])

    def test_ranking_modes_reuse_data_and_keep_filter_membership(self):
        self.window.port.setValue(1); self.window.symbol.setText('TEST')
        self.dataset['contracts'].append(dict(self.dataset['contracts'][0], code='US.TEST-SECOND',
                                             bid=1.6, ask=1.7, delta=-.29))
        result = self.result(); result['input_dataset'] = self.dataset
        self.window.display(result)
        members = set(result['report']['ranked_codes'])
        for mode in ('risk', 'duration', 'cost', 'return', 'balanced'):
            with self.subTest(mode=mode):
                self.window.ranking_mode.setCurrentIndex(self.window.ranking_mode.findData(mode))
                deadline = time.monotonic()+15
                while self.window.process is not None and time.monotonic() < deadline:
                    self.app.processEvents(); time.sleep(.01)
                self.assertIsNone(self.window.process)
                report = self.window.results['put']['report']
                self.assertEqual(set(report['ranked_codes']), members)
                self.assertEqual(report['collected_at'], self.dataset['collected_at'])
                expected = [list(item) for item in load_rules().RANKING_SORT_ORDERS[mode]]
                self.assertEqual(report['sort_order'], expected)
        self.assertIn('风险分↓', self.window.put_result.toPlainText())
        self.assertIn('Top 10', self.window.put_result.toPlainText())
        self.assertIn('到期 / 天数', self.window.put_result.toPlainText())
        self.assertIn('行权价 / 成本', self.window.put_result.toPlainText())

    def test_score_editor_changes_scoring_without_touching_filters_or_sort(self):
        dialog = FilterSortDialog(self.window.configuration, parent=self.window)
        try:
            before = dialog.configuration()
            dialog.score_controls[('parameters', 'return_weight')].setValue(.3)
            changed = dialog.configuration()
            self.assertEqual(changed['filters'], before['filters'])
            self.assertEqual(changed['sort_order'], before['sort_order'])
            self.assertEqual(changed['scoring']['parameters']['return_weight'], .3)
            dialog.restore_scoring()
            self.assertEqual(dialog.configuration()['scoring'], before['scoring'])
        finally: dialog.close()

    def test_top_five_ten_twenty_reuses_the_entire_dataset_without_refetch(self):
        self.window.port.setValue(1); self.window.symbol.setText('TEST')
        for index in range(1, 25):
            self.dataset['contracts'].append(dict(self.dataset['contracts'][0], code=f'US.TEST-{index}',
                strike=90-index*.5, snapshot_strike=90-index*.5))
        result = self.result(); result['input_dataset'] = self.dataset
        self.window.display(result)
        for count in (5, 20, 10):
            with self.subTest(count=count):
                self.window.top_count.setCurrentIndex(self.window.top_count.findData(count))
                deadline = time.monotonic()+15
                while self.window.process is not None and time.monotonic() < deadline:
                    self.app.processEvents(); time.sleep(.01)
                self.assertIsNone(self.window.process)
                report = self.window.results['put']['report']
                self.assertEqual(len(report['recommendations']), count)
                self.assertEqual(report['qualified_count'], 25)
                self.assertEqual([r['code'] for r in report['recommendations']], report['ranked_codes'][:count])
                self.assertEqual(self.window.put_dataset, self.dataset)
                self.assertIn(f'Top {count}', self.window.put_result.toPlainText())
                self.assertEqual(int(self.window.settings.value('put_top_n')), count)

    def test_combined_cost_return_risk_date_filters_then_top_ten_offline(self):
        self.window.port.setValue(1); self.window.symbol.setText('TEST')
        for index in range(1, 25):
            self.dataset['contracts'].append(dict(self.dataset['contracts'][0], code=f'US.TEST-BOUNDS-{index}',
                strike=90-index*.5, snapshot_strike=90-index*.5))
        result = self.result(); result['input_dataset'] = self.dataset
        self.window.display(result)
        dialog = FilterSortDialog(self.window.configuration, parent=self.window)
        try:
            for rid, value in [('min-cost', 8000), ('max-cost', 8800), ('min-daily-return', .01), ('max-risk', 90)]:
                check, field = dialog.controls[('filters', rid)]; check.setChecked(True); field.setValue(value)
            check, field = dialog.controls[('filters', 'expiry-before')]
            check.setChecked(True); field.setDate(QDate(2026, 11, 21))
            configuration = dialog.configuration()
            self.assertEqual(configuration['filters']['expiry-before']['threshold'], '2026-11-21')
            dialog.restore_filters()
            self.assertIsNone(dialog.configuration()['filters']['expiry-before']['threshold'])
        finally: dialog.close()
        self.window.apply_configuration(configuration)
        deadline = time.monotonic()+15
        while self.window.process is not None and time.monotonic() < deadline:
            self.app.processEvents(); time.sleep(.01)
        self.assertIsNone(self.window.process)
        report = self.window.results['put']['report']
        self.assertEqual(report['qualified_count'], 15)
        self.assertEqual(len(report['recommendations']), 10)
        for row in report['recommendations']:
            self.assertTrue(8000 < row['cash_collateral'] < 8800)
            self.assertGreater(row['daily_gross_return_pct'], .01)
            self.assertLess(row['risk_score'], 90)
            self.assertLess(row['expiration'], '2026-11-21')

    def test_single_best_put_risks_and_symbol_change_clears_both_results(self):
        result = self.result(); self.window.display(result)
        text = self.window.put_result.toPlainText()
        self.assertIn(result['report']['best_research_code'], text)
        for phrase in ('现金担保要求', '最大亏损', '简单年化', '未校验个人资金预算', '日均毛收益率', '规则引擎的到期日', '不是实际每天到账'): self.assertIn(phrase, text)
        self.assertTrue(self.window.export_button.isEnabled())
        self.window.symbol.setText('NVDA')
        self.assertFalse(self.window.results)
        self.assertNotIn('最大亏损', self.window.put_result.toPlainText())
        self.assertFalse(self.window.export_button.isEnabled())

    def test_no_eligible_put_explains_failed_checks_without_picking_a_contract(self):
        self.dataset['contracts'][0]['delta'] = -.9
        result = self.result(); self.window.display(result)
        self.assertIn('没有符合', self.window.put_result.toPlainText())
        self.assertIn('|Delta|', self.window.put_result.toPlainText())
        self.assertNotIn('现金担保要求', self.window.put_result.toPlainText())
        self.assertIn('趋势条件', self.window.put_result.toPlainText())
        self.assertIn('实际值', self.window.put_result.toPlainText())
        self.assertIn('RSI14', self.window.put_result.toPlainText())
        self.assertIn('合约条件逐项检查', self.window.put_result.toPlainText())

    def test_closed_port_runs_async_and_displays_error_instead_of_fake_results(self):
        with socket.socket() as reserved:
            reserved.bind(('127.0.0.1', 0))
            self.window.port.setValue(reserved.getsockname()[1])
            self.window.start('trend')
            self.assertFalse(self.window.trend_button.isEnabled())
            deadline = time.monotonic() + 15
            while self.window.process is not None and time.monotonic() < deadline:
                self.app.processEvents(); time.sleep(.01)
        self.assertIsNone(self.window.process)
        self.assertTrue(self.window.trend_button.isEnabled())
        self.assertIn('分析未完成', self.window.trend_result.toPlainText())
        self.assertFalse(self.window.results)

    def test_closing_stops_running_child_process(self):
        import sys
        process = QProcess(self.window); self.window.process = process; self.window.action = 'trend'
        process.start(sys.executable, ['-c', 'import time; time.sleep(60)'])
        self.assertTrue(process.waitForStarted(3000))
        self.window.close()
        self.assertEqual(process.state(), QProcess.ProcessState.NotRunning)

    def test_cancel_returns_to_idle_without_reporting_a_data_error(self):
        import sys
        process = QProcess(self.window); self.window.process = process; self.window.action = 'trend'
        process.finished.connect(self.window.finished)
        process.start(sys.executable, ['-c', 'import time; time.sleep(60)'])
        self.assertTrue(process.waitForStarted(3000))
        self.window.busy(True); self.window.cancel()
        deadline = time.monotonic() + 5
        while self.window.process is not None and time.monotonic() < deadline:
            self.app.processEvents(); time.sleep(.01)
        self.assertIsNone(self.window.process)
        self.assertIn('已取消', self.window.trend_result.toPlainText())
        self.assertNotIn('检查 OpenD', self.window.trend_result.toPlainText())
        self.assertTrue(self.window.trend_button.isEnabled())
