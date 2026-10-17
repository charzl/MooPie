"""User-selected strategy filters and a separate lexicographic sort editor."""
import copy
from PySide6.QtCore import QDate

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTabWidget,
    QWidget, QScrollArea, QCheckBox, QDoubleSpinBox, QComboBox, QPushButton,
    QDialogButtonBox, QMessageBox, QDateEdit)

from .research import load_rules
from .research_explanation import METRICS, FLAGS, value_text


class FilterSortDialog(QDialog):
    def __init__(self, configuration, report=None, has_dataset=False, parent=None):
        super().__init__(parent)
        self.engine = load_rules()
        self.initial = self.engine.recommendation_configuration(configuration)
        self.report = report
        self.has_dataset = has_dataset
        self.controls = {}
        self.sort_controls = []
        self.score_controls = {}
        self.selected_configuration = None
        self.setWindowTitle('Filter 过滤 / Sort 排序')
        self.resize(880, 760)
        outer = QVBoxLayout(self)
        hint = QLabel('Filter 是不可越过的风险边界；Sort 比较边界内的收益。初始数值仅作研究示例，请按自己的承受范围调整。趋势和财报默认作为风险提示，可勾选升级为硬限制。')
        hint.setWordWrap(True); outer.addWidget(hint)
        tabs = QTabWidget(); outer.addWidget(tabs, 1)
        page = QWidget(); filters = QVBoxLayout(page)
        actions = QHBoxLayout()
        clear = QPushButton('关闭全部可选 Filter'); clear.clicked.connect(self.disable_optional)
        defaults = QPushButton('恢复默认 Filter'); defaults.clicked.connect(self.restore_filters)
        actions.addWidget(clear); actions.addWidget(defaults); actions.addStretch(); filters.addLayout(actions)
        base = QLabel('基础校验始终执行：计算所需数据有效、合约身份一致、未过期、标准100股合约、未停牌。')
        base.setWordWrap(True); filters.addWidget(base)
        impacts = {item['id']: item for item in (report or {}).get('filter_impact', [])}
        for group, source, heading in [('filters', self.engine.RULES, '合约 Filter'),
                                       ('trend_filters', self.engine.TREND_RULES, '趋势 Filter（由“标的通过全部趋势检查”开关控制）')]:
            if group == 'filters':
                source = sorted(source, key=lambda rule: rule[0] not in self.engine.OPTIONAL_SELECTION_FILTERS)
            title = QLabel(heading); title.setStyleSheet('font-weight:bold;padding-top:12px;'); filters.addWidget(title)
            for rid, metric, op, _ in source:
                if rid in self.engine.REQUIRED_FILTERS: continue
                row = QHBoxLayout()
                label = METRICS.get(metric, metric)
                check = QCheckBox(label if metric in FLAGS else label + ' ' + op)
                chosen = self.initial[group][rid]
                check.setChecked(chosen['enabled']); row.addWidget(check, 1)
                field = None
                if metric == 'expiration':
                    field = QDateEdit(); field.setCalendarPopup(True); field.setDisplayFormat('yyyy-MM-dd')
                    field.setDate(QDate.fromString(chosen['threshold'], 'yyyy-MM-dd')
                                  if chosen['threshold'] else QDate.currentDate().addMonths(3))
                    field.setEnabled(chosen['enabled']); check.toggled.connect(field.setEnabled); row.addWidget(field)
                elif metric not in FLAGS:
                    field = QDoubleSpinBox(); field.setDecimals(4)
                    if metric in ('days_to_expiry', 'volume', 'open_interest', 'bid_size'): field.setDecimals(0)
                    elif metric != 'macd_histogram_change': field.setDecimals(2)
                    field.setRange(-1_000_000_000 if group == 'trend_filters' else 0, 1_000_000_000)
                    if metric == 'abs_delta': field.setRange(0, 1); field.setSingleStep(.05)
                    if metric == 'rsi14': field.setRange(0, 100)
                    if metric == 'risk_score': field.setRange(0, 100)
                    if metric == 'cash_collateral': field.setPrefix('$')
                    if metric == 'daily_gross_return_pct': field.setDecimals(4); field.setSingleStep(.01)
                    field.setValue(chosen['threshold']); field.setEnabled(chosen['enabled'])
                    if metric.endswith('_pct') or metric == 'spread_pct_of_mid': field.setSuffix('%')
                    check.toggled.connect(field.setEnabled); row.addWidget(field)
                else: row.addWidget(QLabel('要求：' + value_text(metric, chosen['threshold'])))
                if rid in impacts:
                    effect = impacts[rid]
                    count = QLabel(f'排除 {effect["excluded_count"]}')
                    count.setToolTip(f'仅关闭这一项后预计 {effect["qualified_without_filter"]} 个候选；不自动应用。')
                    row.addWidget(count)
                self.controls[(group, rid)] = (check, field)
                filters.addLayout(row)
        note = QLabel('成本上下限、最低日均毛收益率、最高风险分和到期截止日可组合启用；先过滤完整数据，再取Top数量。< / > 为严格不等式，到期截止日不含当天。收益门槛以百分数输入，例如0.05表示0.05%/天。财报未知时，启用的财报条件无法通过；关闭后仍保留风险提示。')
        note.setWordWrap(True); filters.addWidget(note)
        filters.addStretch()
        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setWidget(page)
        tabs.addTab(scroll, 'Filter 过滤')
        sorting = QWidget(); sort_layout = QVBoxLayout(sorting)
        explanation = QLabel('依次比较第一、第二、第三排序；相同值才使用下一项。排序不会替你放宽任何 Filter。')
        explanation.setWordWrap(True); sort_layout.addWidget(explanation)
        preferred = ['daily_gross_return_pct', 'risk_score', 'composite_score', 'return_score',
                     'annualized_gross_return_pct', 'gross_return_pct', 'spread_pct_of_mid', 'abs_delta',
                     'otm_pct', 'breakeven_buffer_pct', 'cash_collateral', 'days_to_expiry',
                     'premium_per_contract_before_costs']
        order = self.initial['sort_order']
        for index in range(3):
            row = QHBoxLayout(); row.addWidget(QLabel(f'第 {index+1} 排序'))
            metric = QComboBox(); direction = QComboBox()
            if index: metric.addItem('不使用', None)
            choices = list(dict.fromkeys(preferred + [item[0] for item in order]))
            for key in choices: metric.addItem(METRICS.get(key, key), key)
            direction.addItem('从高到低', 'desc'); direction.addItem('从低到高', 'asc')
            if index < len(order):
                metric.setCurrentIndex(metric.findData(order[index][0])); direction.setCurrentIndex(direction.findData(order[index][1]))
            elif index: metric.setCurrentIndex(0)
            row.addWidget(metric, 1); row.addWidget(direction); sort_layout.addLayout(row)
            self.sort_controls.append((metric, direction))
        sort_layout.addStretch(); tabs.addTab(sorting, 'Sort 排序')
        score_page = QWidget(); score_layout = QVBoxLayout(score_page)
        note = QLabel('风险分0–100，越高越危险；收益分和综合分越高越好。以下为待验证的研究参数，不代表亏损概率。权重自动归一化，缺失信息有单独惩罚。修改评分不更改 Filter 设置；启用最高风险分限制时，评分变化会影响是否通过。')
        note.setWordWrap(True); score_layout.addWidget(note)
        restore = QPushButton('恢复示例评分参数'); restore.clicked.connect(self.restore_scoring)
        score_layout.addWidget(restore)
        for group in ('weights', 'parameters'):
            title = QLabel('风险维度权重（至少一项大于0）' if group == 'weights' else '评分尺度和收益 / 风险取舍')
            title.setStyleSheet('font-weight:bold;padding-top:12px;'); score_layout.addWidget(title)
            for key, value in self.initial['scoring'][group].items():
                if group == 'weights': low, high, label = 0, 100, self.engine.RISK_LABELS[key]
                else: _, low, high, label = self.engine.SCORING_PARAMETERS[key]
                row = QHBoxLayout(); text = QLabel(label); text.setWordWrap(True); row.addWidget(text, 1)
                field = QDoubleSpinBox(); field.setDecimals(6 if group == 'parameters' else 2)
                field.setRange(low, high); field.setValue(value)
                if key in ('return_weight', 'delta_high', 'daily_return_target_pct'): field.setSingleStep(.05)
                row.addWidget(field); score_layout.addLayout(row)
                self.score_controls[(group, key)] = field
        score_layout.addStretch()
        score_scroll = QScrollArea(); score_scroll.setWidgetResizable(True); score_scroll.setWidget(score_page)
        tabs.addTab(score_scroll, '收益 / 风险评分')
        if report:
            text = f'本次数据：{report["qualified_count"]} / {report["total_contracts"]} 个合约符合已启用 Filter。'
            if report['qualified_count'] == 0:
                text += '\n关闭某一项仍可能为0，因为同一合约可能同时违反多项。可参考结果中的放宽预览，再自行决定。'
            status = QLabel(text); status.setWordWrap(True); outer.addWidget(status)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        apply = buttons.addButton('应用并重新筛选（已有数据）' if has_dataset else '保存设置', QDialogButtonBox.ButtonRole.AcceptRole)
        buttons.accepted.connect(self.apply); buttons.rejected.connect(self.reject); outer.addWidget(buttons)

    def disable_optional(self):
        for check, _ in self.controls.values(): check.setChecked(False)

    def restore_filters(self):
        defaults = self.engine.recommendation_configuration()
        for (group, rid), (check, field) in self.controls.items():
            check.setChecked(defaults[group][rid]['enabled'])
            if isinstance(field, QDateEdit):
                value = defaults[group][rid]['threshold']
                self.initial[group][rid]['threshold'] = value
                field.setDate(QDate.fromString(value, 'yyyy-MM-dd') if value else QDate.currentDate().addMonths(3))
            elif field: field.setValue(defaults[group][rid]['threshold'])

    def configuration(self):
        result = copy.deepcopy(self.initial)
        for (group, rid), (check, field) in self.controls.items():
            result[group][rid]['enabled'] = check.isChecked()
            if isinstance(field, QDateEdit):
                if check.isChecked(): result[group][rid]['threshold'] = field.date().toString('yyyy-MM-dd')
            elif field: result[group][rid]['threshold'] = field.value()
        result['sort_order'] = [[metric.currentData(), direction.currentData()]
                                for metric, direction in self.sort_controls if metric.currentData() is not None]
        for (group, key), field in self.score_controls.items(): result['scoring'][group][key] = field.value()
        return self.engine.resolve_configuration(result)

    def restore_scoring(self):
        defaults = self.engine.default_configuration()['scoring']
        for (group, key), field in self.score_controls.items(): field.setValue(defaults[group][key])

    def apply(self):
        try: self.selected_configuration = self.configuration()
        except ValueError as error:
            message = str(error)
            if message.startswith('Invalid, duplicate'): message = '排序项不能重复，请把重复的后续项改为“不使用”。'
            elif message.startswith('Minimum filter exceeds'): message = '最小值不能大于最大值，请检查到期天数或 Delta 范围。'
            elif message.startswith('At least one risk'): message = '至少一项风险维度的权重需要大于0。'
            QMessageBox.warning(self, '设置无效', message); return
        self.accept()
