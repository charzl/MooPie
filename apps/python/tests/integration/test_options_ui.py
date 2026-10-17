import json
import os
import tempfile
import time
from types import SimpleNamespace
import unittest

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PySide6.QtCore import QSettings, QTimer
from PySide6.QtWidgets import QApplication
from moopython.gateway import Gateway
from moopython.ui import MainWindow
from moopython.options import OptionQuery


class Rows:
    def __init__(self, rows): self.rows = rows
    def to_dict(self, orient): return self.rows


class OptionUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.window = MainWindow(QSettings(self.temp.name + '/settings.ini', QSettings.Format.IniFormat))
        self.window.mode = 'live'
        self.window.show_option_range()
        self.page = self.window.data_pages['期权范围']

    def wait(self, predicate):
        deadline = time.monotonic() + 4
        while not predicate() and time.monotonic() < deadline:
            self.app.processEvents()
            time.sleep(.005)
        self.assertTrue(predicate())

    def tearDown(self):
        self.window.close()
        self.wait(lambda: self.window.closed)
        self.temp.cleanup()

    def response(self, request):
        days = [self.page.start_date.date().toString('yyyy-MM-dd'), self.page.end_date.date().toString('yyyy-MM-dd')]
        return dict(op='options', request=request, symbol='US.NVDA', start=days[0], end=days[1],
                    option_type='ALL', source='test', timezone='America/New_York', queried_at='test',
                    expirations=days, contracts=[dict(code=f'US.NVDA-{day}', strike_time=day,
                    option_type='CALL', strike_price=strike, stock_owner='US.NVDA', lot_size=100,
                    name='Test contract', option_standard_type='STANDARD') for day, strike in zip(days, (90, 100))])

    def test_navigation_dates_filter_sort_export_and_input_invalidation(self):
        self.assertTrue(self.window.nav_buttons['期权'].isChecked())
        self.assertIs(self.window.pages.currentWidget(), self.page)
        query = OptionQuery.upcoming(self.window.selected)
        self.assertEqual(self.page.end_date.date().toPython(), query.end)
        self.page.code.setText('NVDA')
        self.page.load_chain()
        self.page.receive(self.window.token, 'user_data', self.response(self.page.request))
        self.assertEqual(self.page.table.rowCount(), 2)
        self.page.table.sortItems(2)
        self.assertEqual(self.page.table.item(0, 2).data(0), 90)
        self.page.expiry.setCurrentIndex(2)
        self.assertEqual(self.page.table.rowCount(), 1)
        output = self.temp.name + '/options.json'
        self.page.save_result(output, 'json')
        with open(output) as stream: exported = json.load(stream)
        self.assertEqual(len(exported['contracts']), 1)
        self.assertEqual(exported['expirations'], [self.page.expiry.currentData()])
        self.page.code.setText('AAPL')
        self.assertEqual(self.page.table.rowCount(), 0)
        self.assertFalse(self.page.export.isEnabled())
        self.window.show_charts()
        self.assertFalse(self.window.nav_buttons['期权'].isChecked())

    def test_cancel_and_session_change_ignore_late_results(self):
        self.page.load_chain()
        request = self.page.request
        self.page.cancel_query()
        self.assertTrue(self.window.gateway.option_cancel.is_set())
        self.page.receive(self.window.token, 'user_data', self.response(request))
        self.assertEqual(self.page.table.rowCount(), 0)
        self.page.load_chain()
        request = self.page.request
        self.window.token = 'new-session'
        self.page.check_session()
        self.page.receive(self.page.session, 'user_data', self.response(request))
        self.assertEqual(self.page.table.rowCount(), 0)
        self.assertFalse(self.page.read.isEnabled())

    def test_api_error_clears_results_and_reenables_query(self):
        self.page.load_chain()
        self.page.receive(self.window.token, 'user_data_error', dict(request=self.page.request, error='permission denied'))
        self.assertIn('permission denied', self.page.status.text())
        self.assertTrue(self.page.read.isEnabled())
        self.assertFalse(self.page.cancel.isEnabled())
        self.assertFalse(self.page.export.isEnabled())

    def test_existing_option_page_links_to_range_query_and_back(self):
        self.window.show_data_page('期权')
        single = self.window.data_pages['期权']
        self.window.show_option_range('NVDA')
        self.assertEqual(self.page.code.text(), 'NVDA')
        self.assertTrue(self.window.nav_buttons['期权'].isChecked())
        self.page.reject()
        self.assertIs(self.window.pages.currentWidget(), single)

    def test_slow_query_runs_off_gui_thread_and_reports_progress(self):
        events = []
        today = OptionQuery.upcoming('AAPL').start.isoformat()

        class Context:
            def __init__(self, **kwargs): pass
            def set_handler(self, handler): pass
            def get_global_state(self): return 0, {}
            def get_option_expiration_date(self, code): return 0, Rows([dict(strike_time=today)])
            def get_option_chain(self, *args, **kwargs): time.sleep(.2); return 0, Rows([])
            def close(self): events.append('closed')

        sdk = SimpleNamespace(RET_OK=0, OpenQuoteContext=Context, StockQuoteHandlerBase=object,
                              CurKlineHandlerBase=object, OptionType=SimpleNamespace(ALL='ALL'))
        gateway = Gateway(sdk_factory=lambda: sdk)
        gateway.event.connect(lambda token, kind, data: events.append(kind))
        try:
            gateway.send('connect', 'test', host='127.0.0.1', port=11111, symbols=[])
            self.wait(lambda: 'connected' in events)
            gateway.send('options', 'test', code='AAPL', start=today, end=today, option_type='ALL', request='query')
            QTimer.singleShot(20, lambda: events.append('heartbeat'))
            self.wait(lambda: 'user_data' in events)
            self.assertIn('options_progress', events)
            self.assertLess(events.index('heartbeat'), events.index('user_data'))
        finally:
            gateway.shutdown()
            self.wait(lambda: not gateway.thread.isRunning())
        self.assertIn('closed', events)
