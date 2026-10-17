"""Small cross-platform desktop: one symbol, Put ranking and trend evidence."""
import html
import json
from pathlib import Path
import sys
import tempfile

from PySide6.QtCore import QProcess, QProcessEnvironment, QSettings, Qt
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QTextBrowser, QSpinBox, QFileDialog, QMessageBox,
    QDialog, QDialogButtonBox)

from .market_collection import us_symbols
from .runtime import OpenDRuntime
from .research_explanation import explanation_html, sort_description, ranking_html
from .research import load_rules
from .research_controls import FilterSortDialog

STYLE = '''
QWidget {background:#10171e;color:#e8eef2;font-size:14px;font-family:"Noto Sans SC";}
QLabel#eyebrow {color:#6fd9bf;font-size:12px;font-weight:bold;}
QLabel#title {font-size:30px;font-weight:bold;}
QLabel#muted {color:#9aaab7;font-size:12px;}
QLineEdit,QSpinBox,QDoubleSpinBox,QComboBox {background:#1a2631;border:1px solid #354756;border-radius:8px;padding:10px;}
QComboBox QAbstractItemView {background:#1a2631;color:#e8eef2;selection-background-color:#304655;}
QTabBar::tab {background:#1a2631;padding:10px 18px;border:1px solid #354756;}
QTabBar::tab:selected {color:#6fd9bf;background:#233340;}
QPushButton {background:#233340;border:1px solid #354756;border-radius:8px;padding:12px 18px;font-weight:bold;}
QPushButton:hover {background:#304655;}
QPushButton#primary {background:#ef9854;color:#171d22;border:0;}
QPushButton:disabled {background:#1a2631;color:#62717d;}
QTextBrowser {background:#16212b;border:1px solid #2b3b49;border-radius:12px;padding:16px;font-size:14px;}
QScrollBar:vertical {background:#16212b;width:8px;}
QScrollBar::handle:vertical {background:#425767;border-radius:4px;min-height:24px;}
QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical {height:0px;}
'''

def esc(value):
    return html.escape(str(value))


class ResearchWindow(QMainWindow):
    def __init__(self, settings=None, port=11111):
        super().__init__()
        font_path = Path(__file__).with_name('fonts') / 'NotoSansSC.ttf'
        if QFontDatabase.addApplicationFont(str(font_path)) < 0:
            raise RuntimeError('Bundled Chinese font is missing or unreadable; reinstall the desktop package.')
        self.setWindowTitle('MooPie · 股票研究')
        self.resize(1120, 790)
        self.setMinimumSize(820, 620)
        self.settings = settings or QSettings('MooClients', 'Research')
        self.process = None
        self.results = {}
        self.put_dataset = None
        try:
            saved_config = self.settings.value('filter_sort_configuration', '')
            self.configuration = load_rules().resolve_configuration(json.loads(saved_config) if saved_config else None)
        except (ValueError, TypeError): self.configuration = load_rules().default_configuration()
        self.output = bytearray()
        self.errors = bytearray()
        self.action = None
        self.cancelled = False
        self.workspace = tempfile.TemporaryDirectory(prefix='moomoo-research-')
        self.result_path = Path(self.workspace.name) / 'result.json'
        self.runtime = OpenDRuntime(self)
        self.runtime.status.connect(lambda text: self.status.setText(text))
        root = QWidget()
        layout = QVBoxLayout(root)
        layout.setContentsMargins(32, 28, 32, 20)
        layout.setSpacing(16)
        eyebrow = QLabel('MOOPIE   /   STOCK RESEARCH'); eyebrow.setObjectName('eyebrow')
        layout.addWidget(eyebrow)
        title = QLabel('一只股票，两个判断。'); title.setObjectName('title'); layout.addWidget(title)
        subtitle = QLabel('筛选卖出 Put 的候选合约，或查看接下来走势的判断依据。')
        subtitle.setObjectName('muted'); layout.addWidget(subtitle)
        controls = QHBoxLayout()
        self.symbol = QLineEdit(self.settings.value('symbol', 'AVGO'))
        self.symbol.setPlaceholderText('美股代码，例如 AAPL / NVDA / AVGO')
        self.symbol.setMinimumWidth(220)
        self.symbol.returnPressed.connect(lambda: self.start('trend'))
        controls.addWidget(self.symbol, 1)
        self.put_button = QPushButton('筛选卖出 Put'); self.put_button.setObjectName('primary')
        self.trend_button = QPushButton('分析走势')
        self.put_button.clicked.connect(lambda: self.start('put'))
        self.trend_button.clicked.connect(lambda: self.start('trend'))
        controls.addWidget(self.put_button); controls.addWidget(self.trend_button)
        layout.addLayout(controls)
        settings_row = QHBoxLayout()
        hint = QLabel('美股 · 未来三个月期权 · 现金担保 Put'); hint.setObjectName('muted')
        settings_row.addWidget(hint); settings_row.addStretch()
        self.rules_button = QPushButton('Filter / Sort 设置')
        self.rules_button.clicked.connect(self.show_rules)
        settings_row.addWidget(self.rules_button)
        settings_row.addWidget(QLabel('OpenD 端口'))
        self.port = QSpinBox(); self.port.setRange(1, 65535); self.port.setValue(port)
        self.port.valueChanged.connect(self.reset_panels)
        settings_row.addWidget(self.port)
        layout.addLayout(settings_row)
        panels = QHBoxLayout(); panels.setSpacing(16)
        self.put_result = QTextBrowser(); self.trend_result = QTextBrowser()
        for panel in (self.put_result, self.trend_result):
            panel.setOpenExternalLinks(False); panels.addWidget(panel, 1)
        layout.addLayout(panels, 1)
        self.reset_panels()
        self.symbol.textChanged.connect(self.reset_panels)
        footer = QHBoxLayout()
        self.status = QLabel('请先在官方 OpenD 登录，保持本机 API 开启。'); self.status.setObjectName('muted')
        self.status.setWordWrap(True); footer.addWidget(self.status, 1)
        self.cancel_button = QPushButton('取消'); self.cancel_button.hide()
        self.cancel_button.clicked.connect(self.cancel); footer.addWidget(self.cancel_button)
        self.export_button = QPushButton('导出结果'); self.export_button.setEnabled(False)
        self.export_button.clicked.connect(self.export); footer.addWidget(self.export_button)
        layout.addLayout(footer)
        self.setCentralWidget(root); self.setStyleSheet(STYLE)

    def reset_panels(self):
        self.results.clear()
        self.put_dataset = None
        self.put_result.setHtml('<h2>卖出 Put</h2><p>先按已启用的 Filter 过滤，再按独立 Sort 设置排序。</p><p style="color:#9aaab7">可以选择过滤条件和阈值；没有候选时，查看原因后自行调整。</p>')
        self.trend_result.setHtml('<h2>走势分析</h2><p>均线 · RSI · MACD · 成交量</p><p style="color:#9aaab7">显示趋势、关键价位和改判条件。数据来自已完成日线。</p>')
        if hasattr(self, 'export_button'): self.export_button.setEnabled(False)

    def busy(self, value):
        for control in (self.symbol, self.port, self.put_button, self.trend_button, self.rules_button): control.setEnabled(not value)
        self.cancel_button.setVisible(value)

    def start(self, action, reuse=False):
        if self.process is not None: return
        try: code = us_symbols([self.symbol.text().strip()])[0]
        except ValueError as error:
            self.status.setText(str(error)); return
        dataset = self.put_dataset if action == 'put' and reuse else None
        if reuse and dataset is None:
            self.status.setText('没有可复用的数据，请先抓取。'); return
        if action == 'put' and not reuse: self.put_dataset = None
        self.settings.setValue('symbol', code.removeprefix('US.'))
        self.action = action
        self.cancelled = False
        self.results.pop(action, None)
        self.export_button.setEnabled(bool(self.results))
        self.panel(action).setHtml(f'<h2>{esc(code)}</h2><p>正在抓取和分析…</p>')
        self.status.setText('正在用已采集的数据重新过滤和排序，不重新抓取行情。' if reuse else
                            '正在读取 OpenD；期权查询有频率限制，可能需要几分钟。' if action == 'put' else '正在读取已完成日线…')
        self.output.clear(); self.errors.clear()
        self.result_path.unlink(missing_ok=True)
        process = QProcess(self); self.process = process
        environment = QProcessEnvironment.systemEnvironment()
        environment.insert('PYTHONUTF8', '1'); environment.insert('PYTHONUNBUFFERED', '1')
        process.setProcessEnvironment(environment)
        process.readyReadStandardOutput.connect(lambda: self.output.extend(bytes(process.readAllStandardOutput())))
        process.readyReadStandardError.connect(lambda: self.read_progress(process))
        process.finished.connect(self.finished)
        process.errorOccurred.connect(self.process_error)
        args = (['research'] if getattr(sys, 'frozen', False) else ['-X', 'utf8', '-m', 'moopython.research_cli'])
        extra = []
        if action == 'put':
            config_path = Path(self.workspace.name) / 'configuration.json'
            config_path.write_text(json.dumps(self.configuration, allow_nan=False), encoding='utf-8')
            extra += ['--config', str(config_path)]
            if dataset is not None:
                dataset_path = Path(self.workspace.name) / 'dataset.json'
                dataset_path.write_text(json.dumps(dataset, allow_nan=False), encoding='utf-8')
                extra += ['--input', str(dataset_path)]
        self.busy(True)
        process.start(sys.executable, [*args, action, code, '--port', str(self.port.value()), '--output', str(self.result_path), *extra])

    def panel(self, action):
        return self.put_result if action == 'put' else self.trend_result

    def read_progress(self, process):
        data = bytes(process.readAllStandardError())
        self.errors.extend(data)
        self.errors = self.errors[-8000:]
        lines = data.decode('utf-8', errors='replace').strip().splitlines()
        if lines: self.status.setText(lines[-1][-200:])

    def process_error(self, error):
        if error == QProcess.ProcessError.FailedToStart:
            message = self.process.errorString()
            self.show_error(message)
            self.release_process()

    def finished(self, exit_code, _status):
        process = self.process
        if process is None: return
        self.output.extend(bytes(process.readAllStandardOutput()))
        self.read_progress(process)
        if self.cancelled:
            self.panel(self.action).setPlainText('本次分析已取消。可以重新输入股票并开始查询。')
            self.status.setText('已取消；没有生成本次分析结果。')
            self.release_process()
            return
        try:
            result = json.loads(self.result_path.read_text(encoding='utf-8')) if self.result_path.exists() else json.loads(self.output.decode('utf-8'))
            if exit_code or result.get('error'):
                raise ValueError(result.get('error', f'分析进程退出：{exit_code}'))
            self.display(result)
        except (ValueError, KeyError, TypeError) as error:
            detail = str(error) if self.output else self.errors.decode('utf-8', errors='replace')[-1500:]
            self.show_error(detail or f'分析进程退出：{exit_code}')
        self.release_process()

    def release_process(self):
        if self.process:
            self.process.deleteLater(); self.process = None
        self.busy(False)

    def show_error(self, message):
        self.results.pop(self.action, None)
        self.export_button.setEnabled(bool(self.results))
        self.panel(self.action).setPlainText('分析未完成\n\n' + message + '\n\n请检查 OpenD 登录、端口，以及该股票的期权/日线权限。')
        self.status.setText('分析未完成；没有生成候选或走势结论。')

    def display(self, result):
        action = result['action']
        self.results[action] = result
        heading = f'<h2>{esc(result["symbol"])} · {"卖出 Put" if action == "put" else "走势"}</h2>'
        if action == 'trend':
            trend = result['trend']; outlook = trend['outlook']
            content = f'<h3>{esc(outlook["heading"])}</h3><p>{esc(outlook["horizon"])}</p>'
            content += '<ul>' + ''.join(f'<li>{esc(r)}</li>' for r in outlook['reasons']) + '</ul>'
            content += '<h3>关键价位</h3>' + ''.join(f'<p>{esc(r["label"])}：<b>{r["value"]:.2f}</b></p>' for r in outlook['levels'])
            content += f'<h3>什么会改变判断</h3><p>{esc(outlook["change_condition"])}</p><p>日线截至 {esc(trend["as_of"])} · 纽约交易日</p><p>{esc(outlook["limitation"])}</p>'
        else:
            report = result['report']; ranked = report['ranked']
            self.put_dataset = result.get('input_dataset')
            self.configuration = report.get('configuration', self.configuration)
            content = f'<p>检查 {report["total_contracts"]} 个合约，{report["qualified_count"]} 个通过当前 Filter。</p>'
            content += '<p>Sort：' + esc(sort_description(report['sort_order'])) + '</p>'
            if ranked:
                best = ranked[0]; m = best['metrics']
                content += f'<h3>{esc(best["code"])}</h3><p>到期 {esc(best["expiration"])} · {m["days_to_expiry"]} 天</p>'
                fields = [('行权价', f'${m["strike"]:,.2f}'), ('参考 Bid / Ask', f'${m["bid"]:.2f} / ${m["ask"]:.2f}'),
                          ('每张权利金（费用前）', f'${m["premium_per_contract_before_costs"]:,.2f}'),
                          ('现金担保要求', f'${m["cash_collateral"]:,.2f}'),
                          ('到期收益 / 简单年化', f'{m["gross_return_pct"]:.2f}% / {m["annualized_gross_return_pct"]:.2f}%'),
                          ('盈亏平衡价', f'${m["breakeven_before_costs"]:.2f}'),
                          ('价外幅度 / Delta', f'{m["otm_pct"]:.2f}% / {-m["abs_delta"]:.2f}'),
                          ('买卖价差 / 未平仓量', f'{m["spread_pct_of_mid"]:.2f}% / {m["open_interest"]:,.0f}'),
                          ('最大亏损（股价归零）', f'${m["max_loss_before_costs"]:,.2f}')]
                content += ''.join(f'<p>{label}：<b>{value}</b></p>' for label, value in fields)
                content += '<h3>排名原因</h3><p>通过当前已启用的 Filter，在上述 Sort 设置下排名第一。</p>'
                for warning in best.get('warnings', []): content += '<p><b>需复核：' + esc(warning) + '</b></p>'
                content += f'<p>合约快照：{esc(best["snapshot_update_time"])} · 纽约时间</p>'
                if not best['live_review_ready']: content += '<p><b>仅供研究；交易前需核对上述风险并刷新报价。</b></p>'
                content += ranking_html(report)
            else:
                content += '<h3>没有符合当前 Filter 的 Put</h3><p>可打开 Filter / Sort 设置，自行关闭条件或调整阈值；程序不会自动放宽。</p>'
                unknown = len(report['earnings_unverified_watchlist'])
                if unknown: content += f'<p>{unknown} 个合约仅因财报日期尚未验证，保留在导出结果的观察名单中。</p>'
            missing = len(report['missing_quote_codes'])
            if missing: content += f'<p>另有 {missing} 个合约缺少报价，未参与排名。</p>'
            if report['calendar_errors']: content += '<p>财报日历读取不完整，相关合约无法通过财报检查。</p>'
            content += explanation_html(report)
            content += f'<p>交易日 {esc(report["session_date"])} · 规则 {esc(report["ruleset_version"])}</p><p>按一张标准合约全额现金担保计算；未校验个人资金预算。收益不含费用、不保证成交，规则尚未经回测。</p>'
        self.panel(action).setHtml(heading + content)
        self.status.setText('分析完成 · 数据采集：' + result['collected_at'] + ' · 可导出数据、Filter、Sort 和规则证据')
        self.export_button.setEnabled(True)

    def show_rules(self):
        report = self.results.get('put', {}).get('report')
        dialog = FilterSortDialog(self.configuration, report, self.put_dataset is not None, self)
        if dialog.exec() != QDialog.DialogCode.Accepted: return
        self.configuration = dialog.selected_configuration
        self.settings.setValue('filter_sort_configuration', json.dumps(self.configuration))
        if self.put_dataset is not None: self.start('put', reuse=True)
        else:
            self.results.pop('put', None)
            self.put_result.setPlainText('Filter / Sort 已保存。点击“筛选卖出 Put”抓取并分析。')
            self.export_button.setEnabled(bool(self.results))
            self.status.setText('设置已保存；尚未重新抓取行情。')

    def cancel(self):
        if self.process:
            self.cancelled = True
            self.process.kill()

    def export(self):
        path, _ = QFileDialog.getSaveFileName(self, '导出研究结果', 'moomoo-research.json', 'JSON (*.json)')
        if path:
            try: Path(path).write_text(json.dumps(self.results, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
            except OSError as error: QMessageBox.warning(self, '导出失败', str(error))

    def closeEvent(self, event):
        if self.process:
            self.process.kill(); self.process.waitForFinished(2000)
        self.workspace.cleanup()
        event.accept()


def main():
    import argparse
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication
    parser = argparse.ArgumentParser(description='MooPie stock research desktop')
    parser.add_argument('--port', type=int, default=11111)
    args = parser.parse_args()
    app = QApplication([sys.argv[0]])
    app.setApplicationName('MooPie')
    window = ResearchWindow(port=args.port)
    window.show()
    QTimer.singleShot(300, lambda: window.runtime.run('launch'))
    return app.exec()
