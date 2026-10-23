"""Manual entry details plus a local-only short-put efficiency indicator."""
from datetime import datetime

from PySide6.QtWidgets import (QDialog,QVBoxLayout,QFormLayout,QLineEdit,QLabel,
                               QDialogButtonBox)

from .market_sessions import NY
from .position_efficiency import put_efficiency


SIGNALS = {
    'observe':'指标已计算 · 平仓阈值尚未设置',
    'hold':'未触发设定的效率退出条件',
    'review_close':'低于设定阈值 · 考虑买回平仓',
    'not_profitable':'尚未盈利 · 不适用止盈判断',
    'same_day':'开仓当天 · 暂不提供持有或止盈倾向',
    'expired':'已到期 · 不适用剩余效率判断',
}


class EfficiencyDialog(QDialog):
    def __init__(self,parent,*,row=None,session_date=None,exit_threshold_pct=None):
        super().__init__(parent)
        self.ui=parent.ui
        self.result=None
        self.exit_threshold_pct=exit_threshold_pct
        self.setWindowTitle('持仓效率 · 不考虑风险')
        self.resize(760,660);self.setMinimumWidth(640)
        layout=QVBoxLayout(self);layout.setContentsMargins(24,20,24,20);layout.setSpacing(12)
        context=QLabel(row['code'] if row else '手动计算 · 现金担保 Put')
        context.setWordWrap(True);layout.addWidget(context)
        instruction=QLabel('填写真实开仓信息。开仓权利金和当前回购价均为每股价格，按一张100股标准合约计算。')
        instruction.setWordWrap(True);layout.addWidget(instruction)
        form=QFormLayout();form.setSpacing(10)
        self.fields={}
        labels=[('opened_on','开仓日期'),('expires_on','到期日'),('as_of','评估日期'),
                ('strike','行权价 $'),('opening_premium','开仓权利金／股 $'),('buyback_price','当前回购价／股 $')]
        for name,label in labels:
            field=QLineEdit();field.setPlaceholderText('YYYY-MM-DD' if name in ('opened_on','expires_on','as_of') else '请输入价格')
            self.fields[name]=field;form.addRow(label,field)
        self.fields['as_of'].setText(session_date or datetime.now(NY).date().isoformat())
        if row:
            metrics=row['metrics']
            self.fields['expires_on'].setText(row['expiration'])
            self.fields['strike'].setText(str(metrics['strike']))
            ask=metrics.get('ask')
            if ask is not None and ask>0: self.fields['buyback_price'].setText(str(ask))
        layout.addLayout(form)
        self.quote_note=QLabel(('回购价参考所选合约 Ask，报价时间：'+row['snapshot_update_time']+' · 纽约时间。请核对可成交价格。')
                              if row else '当前回购价请填写可成交买价；不要使用卖出时参考的 Bid。')
        self.quote_note.setObjectName('muted');self.quote_note.setWordWrap(True);layout.addWidget(self.quote_note)
        self.value=QLabel('—');self.value.setObjectName('efficiencyValue');layout.addWidget(self.value)
        self.decision=QLabel();self.decision.setWordWrap(True);layout.addWidget(self.decision)
        self.breakdown=QLabel();self.breakdown.setWordWrap(True);layout.addWidget(self.breakdown)
        formula=QLabel('保留率 =（回购价 ÷ 剩余天数）÷（开仓权利金 ÷ 原始期限）×100%。\n100%为开仓效率基准；低于100%表示效率下降，高于100%表示剩余效率更高。')
        formula.setWordWrap(True);layout.addWidget(formula)
        threshold_note=QLabel('开仓效率基准不等于退出阈值。退出阈值由后续模拟盘策略单独指定，80%仅是待测试候选。')
        threshold_note.setWordWrap(True);layout.addWidget(threshold_note)
        limitation=QLabel('仅比较最大收益上限与时间，忽略风险、费用和利息，不改变当前 Put 排名，也不自动交易。')
        limitation.setObjectName('muted');limitation.setWordWrap(True);layout.addWidget(limitation)
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        self.ui.set_text(buttons.button(QDialogButtonBox.StandardButton.Close),'关闭')
        buttons.rejected.connect(self.reject);layout.addWidget(buttons)
        for field in self.fields.values(): field.textChanged.connect(self.update_result)
        self.ui.localize_tree(self)
        self.update_result()

    def update_result(self):
        self.result=None
        self.ui.set_text(self.value,'—')
        self.ui.set_text(self.breakdown,'')
        data={name:field.text().strip() for name,field in self.fields.items()}
        if not all(data.values()):
            self.ui.set_text(self.decision,'补齐开仓日期、开仓权利金和其他输入后，自动计算。');return
        try: result=put_efficiency(**data,exit_threshold_pct=self.exit_threshold_pct)
        except ValueError:
            self.ui.set_text(self.decision,'请核对输入：日期使用YYYY-MM-DD，开仓早于到期、评估不早于开仓；权利金与行权价大于0，回购价不小于0。');return
        self.result=result
        retention=result['retention_pct']
        self.ui.set_text(self.value,'保留率 '+f'{retention:.2f}%' if retention is not None else '—')
        threshold=result['configuration']['exit_threshold_pct']
        self.ui.set_text(self.decision,SIGNALS[result['signal']]
                         +(f' · 平仓阈值 {threshold:g}%' if threshold is not None else ''))
        remainder=result['remaining_daily_return_pct']
        remaining_text=f'{remainder:.4f}%' if remainder is not None else '—'
        self.ui.set_text(self.breakdown,f'已获利 {result["profit_capture_pct"]:.2f}% · 已用时间 {result["time_elapsed_pct"]:.2f}% · 剩余 {result["remaining_days"]} 天\n开仓最大日均收益率 {result["opening_daily_return_pct"]:.4f}% · 剩余最大日均收益率 {remaining_text}')
