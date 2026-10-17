import json
from contextlib import contextmanager
import os
from pathlib import Path
import socket
import tempfile
import time
import unittest
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PySide6.QtCore import QDate, QProcess, QSettings, QTimer, Qt
from PySide6.QtTest import QTest
from PySide6.QtGui import QFont, QRawFont
from PySide6.QtWidgets import QApplication
from moopython.research import load_rules
from moopython.research_ui import ResearchWindow
from moopython.research_controls import FilterDialog
from moopython.watchlist_dialog import WatchlistDialog

ROOT = Path(__file__).resolve().parents[4]


class ResearchUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.environment = patch.dict(os.environ, {'MOOMOO_DB_PATH': str(Path(self.temp.name)/'market.sqlite3')})
        self.environment.start()
        self.window = ResearchWindow(QSettings(self.temp.name+'/settings.ini', QSettings.Format.IniFormat))
        self.dataset = json.loads((ROOT/'modules/put-screener/example.json').read_text())

    def tearDown(self):
        self.window.close(); self.app.processEvents(); self.environment.stop(); self.temp.cleanup()

    def test_refresh_button_is_explicit_and_targets_current_action(self):
        with patch.object(self.window, 'start') as start:
            self.window.tabs.setCurrentIndex(0)
            self.window.refresh_button.click()
            start.assert_called_with('put', update=True)
            self.window.tabs.setCurrentIndex(2)
            self.window.refresh_button.click()
            start.assert_called_with('trend', update=True)
            self.window.force_refresh_action.trigger()
            start.assert_called_with('trend', refresh=True)

    def test_suggestion_heart_adds_once_without_selecting_searching_or_discarding_results(self):
        from moopython.symbol_favorites import favorite_rect
        self.seed_directory(); self.window.show(); self.window.symbol.setText('avg')
        QTest.qWait(220)
        suggestions=self.window.symbol_search; view=suggestions.view
        index=next(i for i in range(view.count()) if view.item(i).data(Qt.ItemDataRole.UserRole)['code']=='US.AVG')
        item=view.item(index); target=favorite_rect(view.visualItemRect(item)).center()
        self.window.results['marker']={'keep':True}
        with self.watchlist_worker(),patch.object(self.window,'start',side_effect=AssertionError('Heart must not research')):
            QTest.mouseClick(view.viewport(),Qt.MouseButton.LeftButton,pos=target)
            deadline=time.monotonic()+20
            while suggestions.adder.process is not None and time.monotonic()<deadline:
                self.app.processEvents(); time.sleep(.01)
            self.assertIsNone(suggestions.adder.process)
            self.assertIn('US.AVG',self.window.watchlist.symbols())
            self.assertIn('US.AVG',suggestions.members)
            self.assertEqual(self.window.symbol.text(),'avg')
            self.assertTrue(view.isVisible())
            self.assertEqual(self.window.results,{'marker':{'keep':True}})
            QTest.mouseClick(view.viewport(),Qt.MouseButton.LeftButton,pos=target)
            self.assertIsNone(suggestions.adder.process)
            self.assertEqual(self.window.watchlist.symbols().count('US.AVG'),1)
            self.assertFalse((Path(self.temp.name)/'requests.log').exists())

    def test_favorite_failure_does_not_show_filled_heart_or_change_query(self):
        from moopython.security_directory import SecurityDirectory
        from moopython.symbol_favorites import favorite_rect
        SecurityDirectory().ingest(dict(source='synthetic',collected_at='2026-10-17T15:00:00+00:00',
            rows=[dict(code='US.BAD',name='Rejected by provider',stock_type='STOCK',delisting=False)]))
        self.window.show(); self.window.symbol.setText('bad'); QTest.qWait(220)
        suggestions=self.window.symbol_search; view=suggestions.view
        with self.watchlist_worker():
            QTest.mouseClick(view.viewport(),Qt.MouseButton.LeftButton,
                pos=favorite_rect(view.visualItemRect(view.item(0))).center())
            deadline=time.monotonic()+20
            while suggestions.adder.process is not None and time.monotonic()<deadline:
                self.app.processEvents(); time.sleep(.01)
        self.assertIsNone(suggestions.adder.process)
        self.assertNotIn('US.BAD',self.window.watchlist.symbols())
        self.assertNotIn('US.BAD',suggestions.members)
        self.assertEqual(self.window.symbol.text(),'bad')
        self.assertIn('未加入',self.window.status.text())

    def test_startup_reads_saved_watchlist_with_saved_sort_and_top_and_refresh_outside_tabs(self):
        self.seed_watchlist()
        settings=self.window.settings
        settings.setValue('symbol','MSFT'); settings.setValue('put_top_n',20)
        config=load_rules().recommendation_configuration()
        config['sort_order']=[list(row) for row in load_rules().RANKING_SORT_ORDERS['cost']]
        settings.setValue('put_recommendation_configuration_v1',json.dumps(config))
        self.window.close()
        with self.watchlist_worker():
            self.window=ResearchWindow(settings,auto_load=True); self.window.show()
            self.app.processEvents(); self.wait_worker()
            first=self.window.results['put']
            self.assertEqual(self.window.symbol.text(),'')
            self.assertEqual(first['query_scope'],'watchlist')
            self.assertEqual(first['report']['top_n_requested'],20)
            self.assertEqual(first['report']['sort_order'],config['sort_order'])
            self.assertEqual(self.window.tabs.currentIndex(),0)
            self.assertFalse((Path(self.temp.name)/'requests.log').exists())
            self.assertGreater(self.window.refresh_button.geometry().top(),self.window.tabs.geometry().bottom())
            self.assertEqual(self.window.main_tabs.count(),2)
            self.assertEqual(self.window.main_tabs.tabText(0),'分析')
            self.assertEqual(self.window.tabs.count(),3)
            self.window.close(); self.window=ResearchWindow(settings,auto_load=True)
            self.app.processEvents(); self.wait_worker()
            self.assertTrue(self.window.results['put']['saved_view']['precomputed'])

    def test_paper_ledger_survives_language_theme_and_watchlist_changes_without_network(self):
        import runpy
        from moopython.paper_engine import configuration
        from moopython.paper_store import PaperStore
        fixture=runpy.run_path(str(ROOT/'apps/python/tests/unit/test_paper_trading.py'))['fixture']
        store=PaperStore(); payload=fixture()
        report=store.create('Keep my experiment name',payload,configuration(['US.TEST']),
                            '2026-10-17T17:00:00+00:00')
        panel=self.window.paper_panel
        with patch('socket.create_connection',side_effect=AssertionError('Must stay offline')),patch.object(self.window,'start') as research:
            panel.reload(report['id'])
            self.window.main_tabs.setCurrentIndex(1)
            self.assertEqual(panel.table.rowCount(),6)
            self.assertIn('QQQ',panel.table.item(4,0).text())
            self.assertIn('SPY',panel.table.item(5,0).text())
            self.assertIn('等待',panel.table.item(0,8).text())
            self.window.ui.set_language('en'); self.window.ui.set_theme('light')
            self.assertEqual(self.window.main_tabs.tabText(1),'Paper Trading')
            self.assertIn('Pending',panel.table.item(0,8).text())
            self.assertIn('Keep my experiment name',panel.experiments.currentText())
            panel.reload(report['id'])
            self.window.ui.set_language('zh')
            self.assertEqual(panel.table.horizontalHeaderItem(1).text(),'净收益率')
            self.window.watchlist.remove_items([r['id'] for r in self.window.watchlist.status()['items']])
            self.assertEqual(store.report(report['id'])['config']['symbols'],['US.TEST'])
            self.assertEqual(store.report(report['id'])['fills'],[])
            research.assert_not_called()

    def test_paper_view_reads_ledger_and_only_explicit_update_starts_worker(self):
        panel=self.window.paper_panel
        with patch.object(panel,'run') as worker:
            panel.reload(); self.app.processEvents(); worker.assert_not_called()
            panel.current_report={'mode':'forward'}; panel.busy(False)
            panel.update_button.click(); worker.assert_called_once_with('update')

    def test_price_signals_are_separate_from_rankings_and_clear_with_the_input(self):
        from moopython.research import analyze_put_dataset
        code=self.dataset['contracts'][0]['symbol']
        result=analyze_put_dataset(self.dataset,code)
        self.window.display(result)
        self.assertEqual(self.window.tabs.tabText(2),'技术面依据')
        text=self.window.price_signal_result.toPlainText()
        self.assertIn('暂不参与',text)
        self.assertIn(code,text)
        self.assertIn('买卖盘比例：未验证',text)
        self.assertEqual(self.window.results['put']['report'],load_rules().recommend(self.dataset,per_symbol_limit=20))
        self.window.symbol.setText('NVDA')
        self.assertNotIn(code,self.window.price_signal_result.toPlainText())

    def test_put_query_populates_trend_tab_and_short_history_explains_missing_analysis(self):
        from moopython.research import analyze_put_dataset
        code=self.dataset['contracts'][0]['symbol']
        with patch.object(self.window,'start',side_effect=AssertionError('Reuse existing trend')):
            self.window.display(analyze_put_dataset(self.dataset,code))
            self.assertIn('关键价位',self.window.trend_result.toPlainText())
            self.dataset['daily_series'][0]['bars']=self.dataset['daily_series'][0]['bars'][-108:]
            self.window.display(analyze_put_dataset(self.dataset,code))
            text=self.window.trend_result.toPlainText()
            self.assertIn('108',text); self.assertIn('205',text); self.assertIn('不足',text)
            self.window.ui.set_language('en')
            self.assertIn('Insufficient history',self.window.trend_result.toPlainText())

    def test_first_choice_uses_canonical_rank_one_and_opens_its_evidence(self):
        from moopython.research import analyze_put_dataset
        code=self.dataset['contracts'][0]['symbol']
        result=analyze_put_dataset(self.dataset,code)
        self.window.display(result)
        self.assertEqual(self.window.results['put']['report'],result['report'])
        first=result['report']['recommendations'][0]
        self.assertIn(first['expiration'],self.window.first_choice.text())
        self.window.first_details.click()
        self.assertEqual(self.window.tabs.currentIndex(),1)
        self.assertIn(first['code'],self.window.put_result.toPlainText())
        self.window.symbol.setText('NEW')
        self.assertFalse(self.window.first_details.isEnabled())
        self.assertNotIn(first['expiration'],self.window.first_choice.text())

    def test_sidebar_chooses_single_stock_or_entire_watchlist_without_changing_sort(self):
        config=json.dumps(self.window.configuration,sort_keys=True)
        with patch.object(self.window,'start') as start:
            self.window.choose_scope(self.window.scope_list.item(1))
            self.assertEqual(self.window.symbol.text(),'AVGO')
            start.assert_called_with('put')
            self.window.choose_scope(self.window.scope_list.item(0))
            self.assertEqual(self.window.symbol.text(),'')
            start.assert_called_with('put')
        self.assertEqual(json.dumps(self.window.configuration,sort_keys=True),config)

    def test_language_switch_is_instant_and_keeps_report_selection_and_saved_inputs(self):
        from moopython.research import analyze_put_dataset
        import copy,re
        result=analyze_put_dataset(self.dataset,self.dataset['contracts'][0]['symbol'])
        self.window.display(result)
        before=copy.deepcopy(self.window.results)
        code=self.window.candidate_table.item(0,1).text()
        with patch('socket.create_connection',side_effect=AssertionError('Presentation must stay offline')), \
                patch.object(self.window,'start',side_effect=AssertionError('Do not rerun analysis')):
            self.window.language_actions['en'].trigger()
            self.assertEqual(self.window.put_button.text(),'Screen Puts')
            self.assertEqual(self.window.tabs.tabText(2),'Technical Evidence')
            self.assertEqual(self.window.candidate_table.horizontalHeaderItem(1).text(),'Stock')
            self.assertFalse(re.search('[\u4e00-\u9fff]',self.window.price_signal_result.toPlainText()))
            self.assertFalse(re.search('[\u4e00-\u9fff]',self.window.put_result.toPlainText()))
            self.assertEqual(self.window.candidate_table.item(0,1).text(),code)
            self.assertEqual(self.window.results,before)
            self.window.language_actions['zh'].trigger()
            self.assertEqual(self.window.put_button.text(),'筛选卖出 Put')
            self.assertIn('筛选依据',self.window.put_result.toPlainText())
            self.assertEqual(self.window.results,before)

    def test_theme_preferences_persist_and_system_changes_only_affect_system_mode(self):
        from PySide6.QtGui import QPalette
        from moopython.desktop_preferences import QGuiApplication
        self.window.theme_actions['light'].trigger()
        self.assertEqual(self.window.property('effectiveTheme'),'light')
        self.assertEqual(self.window.palette().color(QPalette.ColorRole.WindowText).name(),'#202938')
        self.window.language_actions['en'].trigger()
        other=ResearchWindow(self.window.settings)
        self.assertEqual(other.ui.language,'en')
        self.assertEqual(other.ui.theme,'light')
        self.assertEqual(other.put_button.text(),'Screen Puts')
        other.close()
        self.window.theme_actions['system'].trigger()
        with patch.object(QGuiApplication,'styleHints') as hints:
            hints.return_value.colorScheme.return_value=Qt.ColorScheme.Dark
            self.window.ui.system_scheme_changed(Qt.ColorScheme.Dark)
            self.assertEqual(self.window.property('effectiveTheme'),'dark')
            hints.return_value.colorScheme.return_value=Qt.ColorScheme.Light
            self.window.ui.system_scheme_changed(Qt.ColorScheme.Light)
            self.assertEqual(self.window.property('effectiveTheme'),'light')
        self.window.theme_actions['dark'].trigger()
        with patch.object(self.window.ui,'apply_theme') as apply:
            self.window.ui.system_scheme_changed(Qt.ColorScheme.Light)
            apply.assert_not_called()

    def test_english_dialogs_and_light_table_colors_follow_preferences(self):
        from moopython.research import analyze_put_dataset
        result=analyze_put_dataset(self.dataset,self.dataset['contracts'][0]['symbol'])
        self.window.display(result)
        self.window.language_actions['en'].trigger(); self.window.theme_actions['light'].trigger()
        dialog=WatchlistDialog(self.window.watchlist,self.window)
        self.assertEqual(dialog.confirm_button.text(),'Confirm & Save')
        dialog.items.setCurrentRow(0); dialog.remove_button.click()
        self.assertIn('Pending Removal',dialog.message.text())
        self.assertIn('Confirm & Save',dialog.message.text())
        dialog.cancel_button.click()
        filters=FilterDialog(self.window.configuration,result['report'],True,self.window)
        self.assertEqual(filters.windowTitle(),'Filters / Scoring')
        self.assertEqual(filters.tabs.tabText(0),'Filters')
        self.assertEqual(self.window.candidate_table.item(0,13).foreground().color().name(),'#202938')
        filters.close()

    def wait_worker(self):
        deadline = time.monotonic()+20
        while self.window.process is not None and time.monotonic() < deadline:
            self.app.processEvents(); time.sleep(.01)
        self.assertIsNone(self.window.process)

    @contextmanager
    def watchlist_worker(self):
        # Run the actual desktop subprocess protocol with its existing clock and
        # provider seams; this stays deterministic on CI trading days, without SDK.
        script = Path(self.temp.name)/'clock_worker.py'
        script.with_name('source.json').write_text(json.dumps(self.dataset),encoding='utf-8')
        script.write_text('''
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
import json
import sys
from moopython import research_cli
from moopython import market_collection
from moopython.market_repository import market_data_connection
class Metadata:
    def collect_put_dataset(self, symbols, months=3):
        root=Path(__file__).parent
        with (root/'requests.log').open('a',encoding='utf-8') as log: log.write(','.join(symbols)+'\\n')
        data=json.loads((root/'source.json').read_text(encoding='utf-8').replace('TEST',symbols[0].removeprefix('US.')))
        data.update(collected_at='2026-10-17T15:00:00+00:00',fetched_at='2026-10-17T15:00:00+00:00',decision_cutoff='2026-10-17T15:00:00+00:00')
        return data
    def security_directory(self):
        return dict(source='synthetic test directory',collected_at='2026-10-17T15:00:00+00:00',
                    rows=[dict(code=c,name=n,stock_type='STOCK',delisting=False)
                          for c,n in [('US.AVGO','Broadcom'),('US.AVG','Another company')]])
    def basic_info(self, codes):
        return dict(collected_at='2026-10-16T22:00:00+00:00', codes=codes, missing_codes=[],
                    rows=[dict(code=c, name='Synthetic test '+c, stock_type='N/A' if c=='US.BAD' else 'STOCK',
                               delisting=c=='US.BAD') for c in codes])
@contextmanager
def provider(**options):
    yield Metadata()
market_collection.opend_connection=provider
def connection(**options):
    return market_data_connection(clock=lambda:datetime.fromisoformat('2026-10-17T15:00:00+00:00'),
                                  connection=provider, **options)
research_cli.market_data_connection=connection
raise SystemExit(research_cli.main(sys.argv[sys.argv.index('moopython.research_cli')+1:]))
''', encoding='utf-8')
        original = QProcess.start
        def start(process, program, arguments):
            return original(process, program, [str(script), *arguments] if 'moopython.research_cli' in arguments else arguments)
        with patch.object(QProcess, 'start', start): yield

    def seed_watchlist(self, count=25):
        from datetime import datetime
        from types import SimpleNamespace
        from moopython.market_repository import market_data_connection
        names = ['US.TEST', 'US.TESTB']
        self.window.watchlist._merge(names,'synthetic test',replace=True)
        self.window.update_watchlist_label()
        def dataset(symbols, months=3):
            code = symbols[0]
            result = json.loads(json.dumps(self.dataset).replace('TEST', code.removeprefix('US.')))
            result.update(symbols=[code], fetched_at=result['collected_at'], decision_cutoff=result['collected_at'])
            first = result['contracts'][0]
            result['contracts'] = []
            for index in range(count):
                strike = 90-index*.2
                bid = 2.5 if code == 'US.TESTB' else 1.5
                result['contracts'].append(dict(first, code=code+f'-{index}', strike=strike,
                    snapshot_strike=strike, bid=bid, ask=bid+.1))
            return result
        def metadata(codes):
            return dict(collected_at=self.dataset['collected_at'], codes=codes, missing_codes=[],
                        rows=[dict(code=code, name='Synthetic '+code, stock_type='STOCK', delisting=False) for code in codes])
        @contextmanager
        def connection(**options):
            yield SimpleNamespace(collect_put_dataset=dataset, basic_info=metadata)
        with market_data_connection(clock=lambda: datetime.fromisoformat('2026-10-17T15:00:00+00:00'),
                                    refresh=True, connection=connection) as service:
            service.basic_info(names)
            for name in names: service.collect_put_dataset([name])

    def seed_directory(self):
        from moopython.security_directory import SecurityDirectory
        return SecurityDirectory().ingest(dict(source='synthetic test directory',
            collected_at='2026-10-17T15:00:00+00:00',rows=[
                dict(code='US.AVGO',name='Broadcom',stock_type='STOCK',delisting=False),
                dict(code='US.AVG',name='Another company',stock_type='STOCK',delisting=False)]))

    def test_company_alias_suggestions_mouse_selection_stays_offline_and_does_not_start_research(self):
        self.seed_directory(); self.window.show(); self.window.symbol.setFocus()
        with patch('socket.create_connection',side_effect=AssertionError('Typing must stay offline')), \
                patch.object(self.window,'start') as start:
            QTest.keyClicks(self.window.symbol,'avago'); QTest.qWait(220)
            view = self.window.symbol_search.view
            self.assertTrue(view.isVisible())
            self.assertEqual(view.count(),1)
            self.assertIn('Broadcom',view.item(0).text())
            self.assertIn('Avago',view.item(0).text())
            QTest.mouseClick(view.viewport(),Qt.MouseButton.LeftButton,pos=view.visualItemRect(view.item(0)).center())
            self.assertEqual(self.window.symbol.text(),'AVGO')
            self.assertFalse(view.isVisible()); start.assert_not_called()
            QTest.keyClick(self.window.symbol,Qt.Key.Key_Return)
            start.assert_called_once_with('put')

    def test_prefix_wildcard_keyboard_selection_escape_and_stale_suggestions(self):
        self.seed_directory(); self.window.show(); self.window.symbol.setFocus()
        with patch.object(self.window,'start') as start:
            QTest.keyClicks(self.window.symbol,'av'); QTest.qWait(220)
            view = self.window.symbol_search.view
            self.assertEqual(view.count(),2)
            selected = self.window.symbol_search.rows[1]['code'].removeprefix('US.')
            QTest.keyClick(self.window.symbol,Qt.Key.Key_Down)
            QTest.keyClick(self.window.symbol,Qt.Key.Key_Return)
            self.assertEqual(self.window.symbol.text(),selected); start.assert_not_called()
            self.window.symbol.setText('*roadcom*'); QTest.qWait(220)
            self.assertEqual(view.count(),1)
            QTest.keyClick(self.window.symbol,Qt.Key.Key_Escape)
            self.assertFalse(view.isVisible())
            self.window.symbol.setText('av'); self.window.symbol.clear(); QTest.qWait(220)
            self.assertFalse(view.isVisible())

    def test_unselected_company_or_prefix_is_not_sent_as_a_ticker(self):
        self.seed_directory(); self.window.show()
        for value in ('avago','broad*','av'):
            self.window.symbol.setText(value)
            with patch('PySide6.QtCore.QProcess.start',side_effect=AssertionError('Must choose a security first')):
                self.window.start('put')
            self.assertIsNone(self.window.process)
            self.assertIn('选择',self.window.status.text())

    def test_directory_button_uses_worker_and_keeps_existing_watchlist_and_results(self):
        self.window.results['put'] = {'marker':'preserve'}
        previous = self.window.watchlist.symbols()
        with self.watchlist_worker():
            self.window.directory_action.trigger(); self.wait_worker()
        self.assertIn('2 条证券',self.window.status.text())
        self.assertEqual(self.window.results['put'],{'marker':'preserve'})
        self.assertEqual(self.window.watchlist.symbols(),previous)
        self.window.symbol.setText('avago'); self.window.symbol_search.update()
        self.assertEqual(self.window.symbol_search.rows[0]['code'],'US.AVGO')

    def test_directory_update_connection_failure_keeps_existing_catalog_and_results(self):
        self.seed_directory()
        self.window.results['put'] = {'marker':'preserve'}
        with socket.socket() as listener:
            listener.bind(('127.0.0.1',0))
            self.window.port.setValue(listener.getsockname()[1])
        self.window.results['put'] = {'marker':'preserve'}
        self.window.directory_action.trigger(); self.wait_worker()
        self.assertIn('保留原目录',self.window.status.text())
        self.assertEqual(self.window.results['put'],{'marker':'preserve'})
        self.assertEqual(self.window.symbol_search.directory.search('avago')[0]['code'],'US.AVGO')

    def test_blank_search_queries_whole_watchlist_and_single_search_keeps_same_table(self):
        self.seed_watchlist()
        self.assertEqual(self.window.symbol.text(), '')
        with self.watchlist_worker():
            self.window.start('put'); self.wait_worker()
            result = self.window.results['put']
            self.assertEqual(result['query_scope'], 'watchlist')
            self.assertEqual(result['report']['total_contracts'], 50)
            self.assertEqual(self.window.candidate_table.rowCount(), 10)
            self.assertTrue(all(self.window.candidate_table.item(i, 1).text() == 'TESTB' for i in range(10)))
            self.assertIn('Watchlist', self.window.ranking_title.text())
            self.window.symbol.setText('TEST')
            self.assertEqual(self.window.candidate_table.rowCount(), 0)
            self.window.symbol.returnPressed.emit(); self.wait_worker()
            self.assertEqual(self.window.results['put']['symbol'], 'US.TEST')
            self.assertEqual(self.window.results['put']['report']['total_contracts'], 25)
            self.assertEqual(self.window.candidate_table.rowCount(), 10)
            self.assertTrue(all(self.window.candidate_table.item(i, 1).text() == 'TEST' for i in range(10)))

    def test_watchlist_button_and_header_sort_rerank_all_candidates_offline(self):
        self.seed_watchlist()
        self.window.symbol.setText('TEST')
        with self.watchlist_worker():
            self.window.view_watchlist_action.trigger(); self.wait_worker()
            self.assertEqual(self.window.symbol.text(), '')
            for count in (5, 20):
                self.window.top_count.setCurrentIndex(self.window.top_count.findData(count)); self.wait_worker()
                self.assertEqual(self.window.candidate_table.rowCount(), count)
                self.assertEqual(self.window.results['put']['report']['qualified_count'], 50)
            self.window.candidate_table.horizontalHeader().sectionClicked.emit(4); self.wait_worker()
        report = self.window.results['put']['report']
        self.assertEqual(report['sort_order'][0], ['strike', 'asc'])
        self.assertEqual(report['total_contracts'], 50)
        self.assertEqual(self.window.results['put']['query_scope'], 'watchlist')
        self.assertIn('SQLite', self.window.data_state.text())

    def test_incremental_update_button_reuses_all_existing_watchlist_quotes(self):
        self.seed_watchlist()
        with self.watchlist_worker():
            self.window.refresh_button.click(); self.wait_worker()
        result=self.window.results['put']
        self.assertEqual(result['data_access']['source'],'database')
        self.assertEqual(len(result['data_access']['reused_symbols']),2)
        self.assertEqual(result['data_access']['fetched_symbols'],[])
        self.assertIn('复用 2 只，抓取 0 只',self.window.status.text())
        self.assertEqual(result['report']['ranking_reduction']['per_symbol_limit'],20)
        self.assertEqual(len(result['report']['ranked']),20)

    def test_whole_watchlist_trends_are_displayed_in_the_existing_trend_tab(self):
        self.seed_watchlist(count=1)
        with self.watchlist_worker():
            self.window.start('trend'); self.wait_worker()
        text = self.window.trend_result.toPlainText()
        self.assertIn('US.TEST', text)
        self.assertIn('US.TESTB', text)
        self.assertEqual(len(self.window.results['trend']['items']), 2)
        self.assertEqual(self.window.tabs.currentIndex(), 2)

    def test_add_button_validates_persists_and_rejects_duplicate_or_invalid_code(self):
        self.seed_watchlist(count=1)
        self.window.symbol.setText('TESTC')
        with self.watchlist_worker():
            self.window.add_watchlist_action.trigger(); self.wait_worker()
            self.assertIn('US.TESTC', self.window.watchlist.symbols())
            self.assertIn('已加入', self.window.status.text())
            self.assertIn('(3)', self.window.watchlist_button.text())
            saved = self.window.watchlist.status()['items']
            self.window.add_watchlist_action.trigger(); self.wait_worker()
            self.assertIn('没有重复添加', self.window.status.text())
            self.assertEqual(self.window.watchlist.status()['items'], saved)
            self.window.symbol.setText('BAD')
            self.window.add_watchlist_action.trigger(); self.wait_worker()
            self.assertIn('不识别', self.window.status.text())
            self.assertEqual(self.window.watchlist.status()['items'], saved)

    def test_failed_watchlist_precheck_shows_code_and_clears_old_candidates(self):
        self.seed_watchlist(count=1)
        self.window.display(self.result())
        self.window.watchlist._merge(['TEST','BAD'],'synthetic test',replace=True)
        with self.watchlist_worker():
            self.window.start('put'); self.wait_worker()
        self.assertFalse(self.window.results)
        self.assertEqual(self.window.candidate_table.rowCount(), 0)
        self.assertIn('US.BAD', self.window.put_result.toPlainText())
        self.assertIn('US.BAD', self.window.ranking_message.text())

    def test_uncached_after_hours_symbol_fetches_once_then_reuses_the_same_snapshot(self):
        self.window.symbol.setText('CBRS')
        with self.watchlist_worker():
            self.window.start('put'); self.wait_worker()
            first=self.window.results['put']
            self.assertEqual(first['data_access']['source'],'OpenD')
            self.assertTrue(first['data_access']['cache_miss_fetch'])
            self.assertGreater(self.window.candidate_table.rowCount(),0)
            self.window.start('put'); self.wait_worker()
            second=self.window.results['put']
            self.assertEqual(second['data_access']['source'],'database')
            self.assertEqual(second['report']['recommendations'],first['report']['recommendations'])
            self.assertEqual(second['report']['qualified_count'],first['report']['qualified_count'])
            self.assertEqual(second['collected_at'],first['collected_at'])
            self.assertEqual((Path(self.temp.name)/'requests.log').read_text().splitlines(),['US.CBRS'])

    def test_watchlist_deletion_is_staged_and_cancel_keeps_database_unchanged(self):
        before = self.window.watchlist.status()['items']
        dialog = WatchlistDialog(self.window.watchlist,self.window)
        dialog.show(); self.app.processEvents()
        dialog.items.setCurrentRow(0)
        dialog.remove_button.click()
        self.assertEqual(dialog.items.count(),len(before)-1)
        self.assertTrue(dialog.confirm_button.isEnabled())
        self.assertIn('待删除',dialog.message.text())
        self.assertEqual(self.window.watchlist.status()['items'],before)
        dialog.cancel_button.click()
        self.assertEqual(dialog.result(),dialog.DialogCode.Rejected)
        self.assertEqual(self.window.watchlist.status()['items'],before)

    def test_watchlist_confirm_removes_only_selected_items_and_updates_main_count(self):
        self.seed_watchlist(count=1)
        before = self.window.watchlist.status()['items']
        def confirm():
            dialog = self.window.findChild(WatchlistDialog)
            self.assertIsNotNone(dialog)
            dialog.items.setCurrentRow(0)
            dialog.remove_button.click()
            # A concurrent addition must survive confirmation of the staged deletion.
            self.window.watchlist._merge(['NEW'],'synthetic test')
            dialog.confirm_button.click()
        QTimer.singleShot(0,confirm)
        self.window.manage_watchlist_action.trigger()
        symbols = self.window.watchlist.symbols()
        self.assertNotIn(before[0]['symbol'],symbols)
        self.assertIn(before[1]['symbol'],symbols)
        self.assertIn('US.NEW',symbols)
        self.assertIn('(2)',self.window.watchlist_button.text())
        self.assertIn('删除 1 项',self.window.status.text())

    def test_watchlist_remove_all_confirmed_stays_empty_and_search_is_clear(self):
        dialog = WatchlistDialog(self.window.watchlist,self.window)
        dialog.items.selectAll(); dialog.remove_button.click()
        dialog.confirm_button.click()
        self.assertEqual(self.window.watchlist.symbols(),[])
        self.window.update_watchlist_label()
        self.assertIn('(0)',self.window.watchlist_button.text())
        with self.watchlist_worker():
            self.window.start('put'); self.wait_worker()
        self.assertIn('Watchlist 为空',self.window.put_result.toPlainText())

    def test_watchlist_save_failure_keeps_dialog_open_and_preserves_membership(self):
        before = self.window.watchlist.symbols()
        dialog = WatchlistDialog(self.window.watchlist,self.window)
        dialog.show(); self.app.processEvents()
        dialog.items.setCurrentRow(0); dialog.remove_button.click()
        with patch.object(self.window.watchlist,'remove_items',side_effect=RuntimeError('database locked')):
            dialog.confirm_button.click()
        self.assertTrue(dialog.isVisible())
        self.assertIn('保存失败',dialog.message.text())
        self.assertEqual(self.window.watchlist.symbols(),before)
        dialog.cancel_button.click()

    def test_database_provenance_survives_offline_top_change(self):
        self.window.symbol.setText('TEST')
        access = dict(source='database', fetched_at=self.dataset['collected_at'],
                      note='数据库保存的原始快照；采集于盘中，不代表收盘快照。')
        self.dataset['data_access'] = access
        result = self.result()
        result.update(input_dataset=self.dataset, data_access=access)
        self.window.display(result)
        self.assertIn('SQLite', self.window.data_state.text())
        self.assertIn('不代表收盘', self.window.data_state.toolTip())
        self.window.top_count.setCurrentIndex(self.window.top_count.findData(5))
        deadline = time.monotonic() + 15
        while self.window.process is not None and time.monotonic() < deadline:
            self.app.processEvents(); time.sleep(.01)
        self.assertIsNone(self.window.process)
        self.assertEqual(self.window.results['put']['data_access'], access)
        self.assertIn('SQLite', self.window.data_state.text())
        self.assertIn('不代表收盘', self.window.status.text())

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
