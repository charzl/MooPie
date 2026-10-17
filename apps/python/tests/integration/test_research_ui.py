import json
import os
from pathlib import Path
import socket
import tempfile
import time
import unittest

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PySide6.QtCore import QProcess, QSettings, QTimer
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
