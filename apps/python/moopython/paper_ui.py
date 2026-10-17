"""Native virtual-account comparison; quote collection runs in a subprocess."""
import html
import json
from pathlib import Path
import sys
import tempfile

from PySide6.QtCore import QDate, QProcess, QProcessEnvironment, Qt
from .desktop_widgets import SelectBox
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QSpinBox, QDoubleSpinBox, QDateEdit,
    QTableWidget, QTableWidgetItem, QHeaderView, QTextBrowser)
from .paper_store import PaperStore


def esc(value): return html.escape(str(value))


class PaperPanel(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.owner = parent
        self.ui = parent.ui
        self.store = PaperStore()
        self.process = None
        self.current_report = None
        self.workspace = tempfile.TemporaryDirectory(prefix='moomoo-paper-')
        self.output_path = Path(self.workspace.name) / 'result.json'
        layout = QVBoxLayout(self)
        title=QLabel('模拟盘'); title.setObjectName('title'); layout.addWidget(title)
        note = QLabel('三个策略与股票池买入持有，并列比较 QQQ 和 SPY 大盘基线。各账户起始资金、成交时点与费用口径一致。')
        note.setWordWrap(True); layout.addWidget(note)
        row = QHBoxLayout()
        self.experiments = SelectBox(); self.experiments.setMinimumWidth(260)
        self.experiments.setProperty('i18nSkipItems', True)
        self.experiments.currentIndexChanged.connect(self.select_experiment)
        row.addWidget(self.experiments, 1)
        self.reload_button = QPushButton('读取账本'); self.reload_button.clicked.connect(lambda: self.reload())
        self.update_button = QPushButton('更新模拟盘'); self.update_button.clicked.connect(lambda: self.run('update'))
        row.addWidget(self.reload_button); row.addWidget(self.update_button)
        self.new_button=QPushButton('新建实验'); self.new_button.setCheckable(True); row.addWidget(self.new_button)
        layout.addLayout(row)
        self.create_form=QWidget(); form=QVBoxLayout(self.create_form); form.setContentsMargins(0,0,0,0)
        self.new_button.toggled.connect(self.create_form.setVisible)
        layout.addWidget(self.create_form)
        create = QHBoxLayout()
        self.name = QLineEdit(); self.name.setPlaceholderText('实验名称（可留空）')
        create.addWidget(self.name, 1)
        create.addWidget(QLabel('虚拟客户'))
        self.clients = QSpinBox(); self.clients.setRange(6,100); self.clients.setValue(6); create.addWidget(self.clients)
        create.addWidget(QLabel('单股投入 $'))
        self.notional = QDoubleSpinBox(); self.notional.setRange(1,100000000); self.notional.setDecimals(0)
        self.notional.setValue(10000); create.addWidget(self.notional)
        self.create_button = QPushButton('创建前向模拟')
        self.create_button.clicked.connect(lambda: self.run('create')); create.addWidget(self.create_button)
        form.addLayout(create)
        self.symbols = QLineEdit()
        self.symbols.setPlaceholderText('股票池：留空使用 Watchlist，或输入 AVGO,NVDA,AAPL；每只需要253个交易日历史')
        form.addWidget(self.symbols)
        replay = QHBoxLayout()
        replay.addWidget(QLabel('历史开始日期'))
        self.start_date = QDateEdit(QDate.currentDate().addMonths(-3)); self.start_date.setCalendarPopup(True)
        self.start_date.setDisplayFormat('yyyy-MM-dd'); replay.addWidget(self.start_date)
        self.backtest_button = QPushButton('历史回测（独立实验）')
        self.backtest_button.clicked.connect(lambda: self.run('backtest')); replay.addWidget(self.backtest_button)
        hint = QLabel('创建时冻结当前 Watchlist；复制客户不增加独立样本。'); hint.setWordWrap(True)
        replay.addWidget(hint, 1); form.addLayout(replay)
        self.status = QLabel('尚未创建模拟实验。'); self.status.setWordWrap(True); layout.addWidget(self.status)
        self.table = QTableWidget(0,11)
        self.table.setHorizontalHeaderLabels(['客户 / 策略','净收益率','最大回撤','净损益 $','持仓比例',
            '成交数','换手率','相对 SPY','1个月','3个月','6个月'])
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        self.table.itemSelectionChanged.connect(self.show_client)
        layout.addWidget(self.table, 2)
        self.details = QTextBrowser(); self.details.setOpenExternalLinks(False); layout.addWidget(self.details, 1)
        self.reload()
        self.new_button.setChecked(self.experiments.count()==0)
        self.create_form.setVisible(self.experiments.count()==0)

    def reload(self, selected=None):
        selected = selected or self.experiments.currentData()
        try:
            rows = self.store.list()
            self.experiments.blockSignals(True); self.experiments.clear()
            for row in rows:
                self.experiments.addItem(f'#{row["id"]} [{row["mode"]}] {row["name"]}', row['id'])
            index = self.experiments.findData(selected)
            if index >= 0: self.experiments.setCurrentIndex(index)
            self.experiments.blockSignals(False)
            self.select_experiment()
        except (ValueError, RuntimeError, OSError) as error:
            self.ui.set_text(self.status, str(error))

    def select_experiment(self, *_):
        identifier = self.experiments.currentData()
        self.update_button.setEnabled(identifier is not None and self.process is None)
        if identifier is None: return
        try: self.display(self.store.report(identifier))
        except (ValueError, RuntimeError, OSError) as error: self.ui.set_text(self.status, str(error))

    def display(self, report):
        self.current_report = report
        mode = '前向模拟' if report['mode']=='forward' else '历史回测'
        self.ui.set_text(self.status, f'{mode} · 开始 {report["start_date"]} · 数据截至 {report["as_of"]} · '
                         + ', '.join(report['config']['symbols']))
        self.update_button.setEnabled(report['mode']=='forward' and self.process is None)
        self.table.blockSignals(True); self.table.setRowCount(len(report['clients']))
        self.table.setHorizontalHeaderLabels(['客户 / 策略','净收益率','最大回撤','净损益 $','持仓比例',
            '成交数','换手率','相对 SPY','1个月','3个月','6个月'])
        for row,client in enumerate(report['clients']):
            pct = lambda key: f'{client[key]:+.2f}%' if client.get(key) is not None else '—'
            values = [client['id']+' / '+client['name'],pct('return_pct'),pct('drawdown_pct'),
                      f'{client["net_pnl"]:,.2f}',f'{client["exposure_pct"]:.1f}%',
                      str(client['fill_count']),f'{client["turnover_pct"]:.1f}%',pct('excess_vs_spy_pct')]
            values += [f'{p["return_pct"]:+.2f}%' if p['status']=='complete' else '等待 '+p['target_date'] for p in client['periods']]
            for col,value in enumerate(values):
                item=QTableWidgetItem(value)
                if col>=8: item.setToolTip(json.dumps(client['periods'][col-8],ensure_ascii=False))
                self.table.setItem(row,col,item)
        self.table.blockSignals(False)
        self.ui.localize_table(self.table, fresh=True)
        if self.table.rowCount(): self.table.selectRow(0)
        self.show_client()

    def show_client(self):
        report=self.current_report
        if report is None: return
        index=self.table.currentRow()
        if not 0<=index<len(report['clients']): return
        client=report['clients'][index]
        history=[r for r in report['history'] if r['client_id']==client['id']]
        last=history[-1]
        fills=[r for r in report['fills'] if r['client_id']==client['id']]
        content=f'<h3>{esc(client["id"])} / {esc(client["name"])}</h3>'
        content+=f'<p>NAV ${client["nav"]:,.2f} · Cash ${client["cash"]:,.2f} · Contributions ${client["contributions"]:,.2f} · Fees ${client["fees"]:.2f} · Slippage ${client["slippage"]:.2f}</p>'
        excess=lambda key: f'{client[key]:+.2f} pp' if client.get(key) is not None else '—'
        content+=f'<p>QQQ excess: {excess("excess_vs_qqq_pct")} · SPY excess: {excess("excess_vs_spy_pct")}</p>'
        content+='<p>换手率 = 累计买卖成交额 / 平均每日净资产；收益率剔除追加资金。</p>'
        content+='<h4>最新决策 / 退出条件</h4><pre>'+esc(json.dumps(last.get('decision'),ensure_ascii=False,indent=2))+'</pre>'
        content+='<h4>最近成交（最多20笔）</h4>'
        content+='<pre>'+esc(json.dumps(fills[-20:],ensure_ascii=False,indent=2))+'</pre>'
        content+='<p>漏过的决策日：'+esc(', '.join(report['skipped_decision_dates']) or '—')+'</p>'
        content+='<ul>'+''.join('<li>'+esc(x)+'</li>' for x in report['limitations'])+'</ul>'
        self.ui.set_text(self.details,content,'setHtml')

    def run(self, action):
        if self.process is not None: return
        args=['paper'] if getattr(sys,'frozen',False) else ['-X','utf8','-m','moopython.paper_cli']
        args += [action]
        if action=='update':
            identifier=self.experiments.currentData()
            if identifier is None: return
            args += [str(identifier)]
        else:
            args += ['--name',self.name.text().strip() or ('Forward' if action=='create' else 'Historical replay'),
                     '--clients',str(self.clients.value()),'--notional',str(self.notional.value())]
            symbols=self.symbols.text().replace(',', ' ').split()
            if symbols: args += ['--symbols',*symbols]
            if action=='backtest': args += ['--start',self.start_date.date().toString('yyyy-MM-dd')]
        args += ['--port',str(self.owner.port.value()),'--output',str(self.output_path)]
        self.output_path.unlink(missing_ok=True)
        process=QProcess(self); self.process=process
        environment=QProcessEnvironment.systemEnvironment(); environment.insert('PYTHONUTF8','1')
        process.setProcessEnvironment(environment)
        process.setProgram(sys.executable); process.setArguments(args)
        process.setStandardOutputFile(str(Path(self.workspace.name)/'stdout.log'))
        process.setStandardErrorFile(str(Path(self.workspace.name)/'stderr.log'))
        process.finished.connect(lambda code,status: self.finished(action,code))
        process.errorOccurred.connect(lambda error: self.finished(action,-1) if error==QProcess.ProcessError.FailedToStart else None)
        self.busy(True); self.ui.set_text(self.status,'正在更新模拟账本…'); process.start()

    def busy(self, value):
        for widget in (self.create_button,self.backtest_button,self.reload_button,self.update_button,self.experiments): widget.setEnabled(not value)
        self.update_button.setEnabled(not value and self.current_report is not None and self.current_report['mode']=='forward')

    def finished(self, action, code):
        process=self.process
        if process is None: return
        self.process=None; self.busy(False); process.deleteLater()
        try:
            result=json.loads(self.output_path.read_text(encoding='utf-8'))
            if code or result.get('error'): raise ValueError(result.get('error') or f'Paper worker exited {code}')
            self.reload(result['id'])
            if action in ('create','backtest'): self.new_button.setChecked(False)
        except (ValueError, OSError) as error: self.ui.set_text(self.status,str(error))

    def shutdown(self):
        if self.process is not None:
            process=self.process; process.blockSignals(True); process.kill(); process.waitForFinished(3000)
            process.deleteLater(); self.process=None
        self.workspace.cleanup()
