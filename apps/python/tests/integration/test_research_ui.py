import json
import os
from pathlib import Path
import socket
import tempfile
import time
import unittest

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PySide6.QtCore import QProcess, QSettings
from PySide6.QtGui import QFont, QRawFont
from PySide6.QtWidgets import QApplication
from moopython.research import load_rules
from moopython.research_ui import ResearchWindow

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
                    collected_at=self.dataset['collected_at'], report=load_rules().scan(self.dataset))

    def test_packaged_font_has_both_chinese_and_latin_glyphs(self):
        font = QRawFont.fromFont(QFont('Noto Sans SC', 14))
        self.assertTrue(font.isValid())
        for character in '股票走势Put123': self.assertTrue(font.supportsCharacter(ord(character)), character)

    def test_single_best_put_risks_and_symbol_change_clears_both_results(self):
        result = self.result(); self.window.display(result)
        text = self.window.put_result.toPlainText()
        self.assertIn(result['report']['best_research_code'], text)
        for phrase in ('现金担保要求', '最大亏损', '简单年化', '未校验个人资金预算'): self.assertIn(phrase, text)
        self.assertTrue(self.window.export_button.isEnabled())
        self.window.symbol.setText('NVDA')
        self.assertFalse(self.window.results)
        self.assertNotIn('最大亏损', self.window.put_result.toPlainText())
        self.assertFalse(self.window.export_button.isEnabled())

    def test_no_eligible_put_explains_failed_checks_without_picking_a_contract(self):
        self.dataset['contracts'][0]['earnings'] = None
        result = self.result(); self.window.display(result)
        self.assertIn('没有符合', self.window.put_result.toPlainText())
        self.assertIn('财报日期尚未验证', self.window.put_result.toPlainText())
        self.assertNotIn('现金担保要求', self.window.put_result.toPlainText())

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
