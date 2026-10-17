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
from moopython.research_controls import FilterDialog

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
                    collected_at=self.dataset['collected_at'], report=load_rules().recommend(self.dataset,
                        configuration=self.window.configuration, top_n=self.window.top_count.currentData()))

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

    def test_filter_editor_has_no_sort_tab_and_preserves_header_sort(self):
        self.window.sort_candidates('strike', 'desc')
        dialog = FilterDialog(self.window.configuration, parent=self.window)
        try:
            self.assertEqual([dialog.tabs.tabText(i) for i in range(dialog.tabs.count())],
                             ['Filter 过滤', '收益 / 风险评分'])
            original_sort = dialog.configuration()['sort_order']
            self.assertEqual(original_sort[0], ['strike', 'desc'])
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
        self.window.sort_candidates('cash_collateral', 'asc')
        self.dataset['contracts'][0]['earnings'] = None
        result = self.result(); result['input_dataset'] = self.dataset
        self.window.display(result)
        errors = []
        def choose():
            dialog = self.app.activeModalWidget()
            try:
                self.assertIsInstance(dialog, FilterDialog)
                for rid in ('earnings-checked', 'earnings-buffer'):
                    dialog.controls[('filters', rid)][0].setChecked(False)
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
                self.assertEqual(self.window.candidate_table.rowCount(), len(report['recommendations']))
                self.assertEqual([self.window.candidate_table.item(i, 1).toolTip()
                                  for i in range(self.window.candidate_table.rowCount())],
                                 [c['code'] for c in report['recommendations']])
        self.assertIn('风险分', self.window.candidate_table.horizontalHeaderItem(12).text())
        self.assertIn('Top 10', self.window.ranking_title.text())
        self.assertEqual(self.window.candidate_table.horizontalHeaderItem(2).text(), '到期日')
        self.assertEqual(self.window.candidate_table.horizontalHeaderItem(4).text(), '行权价 / 担保')

    def test_score_editor_changes_scoring_without_touching_filters_or_sort(self):
        dialog = FilterDialog(self.window.configuration, parent=self.window)
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
                self.assertIn(f'Top {count}', self.window.ranking_title.text())
                self.assertEqual(self.window.candidate_table.rowCount(), count)
                self.assertEqual(int(self.window.settings.value('put_top_n')), count)

    def test_combined_cost_return_risk_date_filters_then_top_ten_offline(self):
        self.window.port.setValue(1); self.window.symbol.setText('TEST')
        for index in range(1, 25):
            self.dataset['contracts'].append(dict(self.dataset['contracts'][0], code=f'US.TEST-BOUNDS-{index}',
                strike=90-index*.5, snapshot_strike=90-index*.5))
        result = self.result(); result['input_dataset'] = self.dataset
        self.window.display(result)
        dialog = FilterDialog(self.window.configuration, parent=self.window)
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
        for phrase in ('现金担保要求', '最大亏损', '简单年化', '未校验个人资金预算', '日均毛收益率', '不是实际每天到账'): self.assertIn(phrase, text)
        self.assertEqual(self.window.candidate_table.rowCount(), 1)
        self.assertEqual(self.window.tabs.currentIndex(), 0)
        self.assertTrue(self.window.export_button.isEnabled())
        self.window.symbol.setText('NVDA')
        self.assertFalse(self.window.results)
        self.assertEqual(self.window.candidate_table.rowCount(), 0)
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
        self.assertEqual(self.window.candidate_table.rowCount(), 0)
        self.assertFalse(self.window.details_button.isEnabled())
        self.assertIn('没有符合', self.window.ranking_message.text())

    def test_selecting_a_candidate_shows_its_own_values_and_evidence(self):
        self.dataset['contracts'].append(dict(self.dataset['contracts'][0], code='US.TEST-SECOND',
                                             bid=1.6, ask=1.7, delta=-.29))
        result = self.result(); self.window.display(result)
        choice = result['report']['recommendations'][1]
        self.window.candidate_table.selectRow(1)
        self.app.processEvents()
        text = self.window.put_result.toPlainText()
        self.assertIn(choice['code'], text)
        self.assertIn(f'${choice["max_loss_before_costs"]:,.2f}', text)
        self.assertIn(f'风险分 {choice["risk_score"]:.2f}', text)
        self.assertIn('所选合约的评分依据', text)
        self.assertIn(choice['code'], self.window.selection_hint.text())
        self.window.details_button.click()
        self.assertEqual(self.window.tabs.currentIndex(), 1)

    def test_header_sort_reranks_full_dataset_before_taking_top_five(self):
        self.window.port.setValue(1); self.window.symbol.setText('TEST')
        for index in range(1, 25):
            self.dataset['contracts'].append(dict(self.dataset['contracts'][0], code=f'US.TEST-HEADER-{index}',
                strike=90-index*.5, snapshot_strike=90-index*.5))
        result = self.result(); result['input_dataset'] = self.dataset
        self.window.display(result)
        self.window.top_count.setCurrentIndex(self.window.top_count.findData(5))
        deadline = time.monotonic()+15
        while self.window.process is not None and time.monotonic() < deadline:
            self.app.processEvents(); time.sleep(.01)
        before = self.window.results['put']['report']
        original_top = {c['code'] for c in before['recommendations']}
        for direction in ('asc', 'desc'):
            self.window.candidate_table.horizontalHeader().sectionClicked.emit(4)
            deadline = time.monotonic()+15
            while self.window.process is not None and time.monotonic() < deadline:
                self.app.processEvents(); time.sleep(.01)
            self.assertIsNone(self.window.process)
            report = self.window.results['put']['report']
            self.assertEqual(report['sort_order'][0], ['strike', direction])
            self.assertEqual(report['qualified_count'], 25)
            self.assertEqual(report['collected_at'], self.dataset['collected_at'])
            self.assertEqual(len(report['recommendations']), 5)
        highest_cost = max(report['ranked'], key=lambda r:r['metrics']['cash_collateral'])
        self.assertNotIn(highest_cost['code'], original_top)
        self.assertEqual(report['recommendations'][0]['code'], highest_cost['code'])
        self.assertIn('$9,000', self.window.candidate_table.item(0, 4).text())
        self.assertFalse(self.window.candidate_table.isSortingEnabled())

    def test_all_data_headers_sort_the_complete_cache_in_both_directions(self):
        self.window.port.setValue(1); self.window.symbol.setText('TEST')
        for index in range(1, 25):
            self.dataset['contracts'].append(dict(self.dataset['contracts'][0], code=f'US.TEST-ALL-{index}',
                strike=90-index*.5, snapshot_strike=90-index*.5))
        self.window.top_count.setCurrentIndex(self.window.top_count.findData(5))
        result = self.result(); result['input_dataset'] = self.dataset
        self.window.display(result)
        expected = [(1, 'symbol', 'asc'), (2, 'expiration', 'asc'), (3, 'days_to_expiry', 'asc'),
                    (4, 'strike', 'asc'), (5, 'bid', 'desc'), (6, 'premium_per_contract_before_costs', 'desc'),
                    (7, 'breakeven_before_costs', 'desc'), (8, 'daily_gross_return_pct', 'desc'),
                    (9, 'annualized_gross_return_pct', 'desc'), (10, 'breakeven_buffer_pct', 'desc'),
                    (11, 'earnings_date', 'asc'), (12, 'risk_score', 'asc'), (13, 'composite_score', 'desc')]
        for column, metric, first_direction in expected:
            for direction in (first_direction, 'desc' if first_direction == 'asc' else 'asc'):
                with self.subTest(metric=metric, direction=direction):
                    self.window.candidate_table.horizontalHeader().sectionClicked.emit(column)
                    deadline = time.monotonic()+15
                    while self.window.process is not None and time.monotonic() < deadline:
                        self.app.processEvents(); time.sleep(.01)
                    self.assertIsNone(self.window.process)
                    report = self.window.results['put']['report']
                    self.assertEqual(report['sort_order'][0], [metric, direction])
                    self.assertEqual(report['qualified_count'], 25)
                    self.assertEqual(report['collected_at'], self.dataset['collected_at'])
                    self.assertEqual([c['code'] for c in report['recommendations']], report['ranked_codes'][:5])
                    self.assertIn('↑' if direction == 'asc' else '↓',
                                  self.window.candidate_table.horizontalHeaderItem(column).text())

    def test_top_twenty_keeps_two_digit_rank_numbers_visible(self):
        for index in range(1, 25):
            self.dataset['contracts'].append(dict(self.dataset['contracts'][0], code=f'US.TEST-NUMBER-{index}',
                strike=90-index*.5, snapshot_strike=90-index*.5))
        self.window.top_count.setCurrentIndex(self.window.top_count.findData(20))
        self.window.display(self.result())
        table = self.window.candidate_table
        self.window.show(); self.app.processEvents()
        self.assertEqual([table.item(i, 0).text() for i in range(20)], [str(i) for i in range(1, 21)])
        self.assertGreater(table.columnWidth(0), table.fontMetrics().horizontalAdvance('20')+24)
        table.scrollToItem(table.item(19, 0)); self.app.processEvents()
        self.assertTrue(table.viewport().rect().contains(table.visualItemRect(table.item(19, 0)).center()))

    def test_earnings_unknown_and_crossing_stay_visible_without_changing_scores(self):
        first = self.dataset['contracts'][0]
        first['earnings'] = None
        self.dataset['contracts'].append(dict(first, code='US.TEST-EVENT',
            earnings=dict(date=first['expiration']), earnings_calendar_complete=True))
        report = self.result()['report']
        self.window.display(dict(action='put', symbol=first['symbol'],
                                 collected_at=self.dataset['collected_at'], report=report))
        for i, choice in enumerate(report['recommendations']):
            event = self.window.candidate_table.item(i, 11).text()
            if choice['code'] == first['code']: self.assertIn('未验证', event)
            else: self.assertIn('到期前 / 同日', event)
            self.assertEqual(self.window.candidate_table.item(i, 12).text(), f'{choice["risk_score"]:.2f}')

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

    def test_failed_put_refresh_clears_the_previous_candidate_list(self):
        with socket.socket() as reserved:
            reserved.bind(('127.0.0.1', 0))
            self.window.port.setValue(reserved.getsockname()[1])
            self.window.display(self.result())
            self.assertEqual(self.window.candidate_table.rowCount(), 1)
            self.window.start('put')
            self.assertEqual(self.window.candidate_table.rowCount(), 0)
            self.assertFalse(self.window.details_button.isEnabled())
            deadline = time.monotonic()+15
            while self.window.process is not None and time.monotonic() < deadline:
                self.app.processEvents(); time.sleep(.01)
        self.assertIsNone(self.window.process)
        self.assertNotIn('put', self.window.results)
        self.assertEqual(self.window.candidate_table.rowCount(), 0)
        self.assertIn('分析未完成', self.window.put_result.toPlainText())
        self.assertEqual(self.window.data_state.text(), '本次查询失败')

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
