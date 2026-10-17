"""Small cross-platform desktop: one symbol, Put ranking and trend evidence."""
import html
import json
from pathlib import Path
import sys
import tempfile

from PySide6.QtCore import QProcess, QProcessEnvironment, QSettings, Qt
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QTextBrowser, QSpinBox, QFileDialog, QMessageBox)

from .market_collection import us_symbols
from .runtime import OpenDRuntime

STYLE = '''
QWidget {background:#10171e;color:#e8eef2;font-size:14px;font-family:"Arial";}
QLabel#eyebrow {color:#6fd9bf;font-size:12px;font-weight:bold;}
QLabel#title {font-size:30px;font-weight:bold;}
QLabel#muted {color:#9aaab7;font-size:12px;}
QLineEdit,QSpinBox {background:#1a2631;border:1px solid #354756;border-radius:8px;padding:10px;}
QPushButton {background:#233340;border:1px solid #354756;border-radius:8px;padding:12px 18px;font-weight:bold;}
QPushButton:hover {background:#304655;}
QPushButton#primary {background:#ef9854;color:#171d22;border:0;}
QPushButton:disabled {background:#1a2631;color:#62717d;}
QTextBrowser {background:#16212b;border:1px solid #2b3b49;border-radius:12px;padding:16px;font-size:14px;}
QScrollBar:vertical {background:#16212b;width:8px;}
QScrollBar::handle:vertical {background:#425767;border-radius:4px;min-height:24px;}
QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical {height:0px;}
'''

RULE_LABELS = {'underlying-trend': '标的趋势不符合要求', 'earnings-checked': '财报日期未确认',
    'earnings-buffer': '财报安全间隔不足或未知', 'min-days': '到期不足 21 天', 'max-days': '到期超过 60 天',
    'otm-buffer': '价外幅度不足', 'min-delta': 'Delta 太低', 'max-delta': 'Delta 太高',
    'spread': '买卖价差过大', 'volume': '成交量不足', 'open-interest': '未平仓量不足',
    'bid-size': '买方报价数量不足', 'min-bid': '权利金不足', 'same-session-snapshot': '报价不属于当前交易日',
    'standard-contract': '不是标准合约', 'not-suspended': '合约停牌'}


def esc(value):
    return html.escape(str(value))


class ResearchWindow(QMainWindow):
    def __init__(self, settings=None, port=11111):
        super().__init__()
        self.setWindowTitle('MooPie · 股票研究')
        self.resize(1120, 790)
        self.setMinimumSize(820, 620)
        self.settings = settings or QSettings('MooClients', 'Research')
        self.process = None
        self.results = {}
        self.output = bytearray()
        self.errors = bytearray()
        self.action = None
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
        settings_row.addWidget(QLabel('OpenD 端口'))
        self.port = QSpinBox(); self.port.setRange(1, 65535); self.port.setValue(port)
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
        self.put_result.setHtml('<h2>卖出 Put</h2><p>通过趋势、期限、流动性和财报检查后，显示规则排名第一的合约。</p><p style="color:#9aaab7">不符合条件时，保留空结果并说明原因。</p>')
        self.trend_result.setHtml('<h2>走势分析</h2><p>均线 · RSI · MACD · 成交量</p><p style="color:#9aaab7">显示趋势、关键价位和改判条件。数据来自已完成日线。</p>')
        if hasattr(self, 'export_button'): self.export_button.setEnabled(False)

    def busy(self, value):
        for control in (self.symbol, self.port, self.put_button, self.trend_button): control.setEnabled(not value)
        self.cancel_button.setVisible(value)

    def start(self, action):
        if self.process is not None: return
        try: code = us_symbols([self.symbol.text().strip()])[0]
        except ValueError as error:
            self.status.setText(str(error)); return
        self.settings.setValue('symbol', code.removeprefix('US.'))
        self.action = action
        self.results.pop(action, None)
        self.export_button.setEnabled(bool(self.results))
        self.panel(action).setHtml(f'<h2>{esc(code)}</h2><p>正在抓取和分析…</p>')
        self.status.setText('正在读取 OpenD；期权查询有频率限制，可能需要几分钟。' if action == 'put' else '正在读取已完成日线…')
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
        self.busy(True)
        process.start(sys.executable, [*args, action, code, '--port', str(self.port.value()), '--output', str(self.result_path)])

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
            content = f'<p>检查 {report["total_contracts"]} 个合约，{report["qualified_count"]} 个符合规则。</p>'
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
                content += '<h3>入选原因</h3><p>通过全部硬性规则；按现金担保权利金简单年化排序，价差和 Delta 用于同分比较。</p>'
                content += f'<p>合约快照：{esc(best["snapshot_update_time"])} · 纽约时间</p>'
                if not best['live_review_ready']: content += '<p><b>休市或快照较旧，仅供研究；交易前需刷新报价。</b></p>'
            else:
                from collections import Counter
                counts = Counter(rule for row in report['results'] for rule in row.get('failed_rules', []))
                invalid = sum(row['status'] == 'invalid_data' for row in report['results'])
                content += '<h3>没有符合当前规则的 Put</h3><p>不自动放宽规则。</p>'
                content += ''.join(f'<p>{esc(RULE_LABELS.get(rule, rule))}：{count} 个未通过</p>' for rule, count in counts.most_common(5))
                if invalid: content += f'<p>数据不足或无效：{invalid} 个合约</p>'
                unknown = len(report['earnings_unverified_watchlist'])
                if unknown: content += f'<p>{unknown} 个合约仅因财报日期尚未验证，保留在导出结果的观察名单中。</p>'
            missing = len(report['missing_quote_codes'])
            if missing: content += f'<p>另有 {missing} 个合约缺少报价，未参与排名。</p>'
            if report['calendar_errors']: content += '<p>财报日历读取不完整，相关合约无法通过财报检查。</p>'
            content += f'<p>交易日 {esc(report["session_date"])} · 规则 {esc(report["ruleset_version"])}</p><p>按一张标准合约全额现金担保计算；未校验个人资金预算。收益不含费用、不保证成交，规则尚未经回测。</p>'
        self.panel(action).setHtml(heading + content)
        self.status.setText('抓取完成：' + result['collected_at'] + ' · 可导出完整指标和规则证据')
        self.export_button.setEnabled(True)

    def cancel(self):
        if self.process:
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
