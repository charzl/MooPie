"""Human-readable evidence from the actual rule configuration and report."""
from collections import Counter
from html import escape

METRICS = {
    'symbol': '股票代码', 'earnings_date': '财报列示日期',
    'strike': '行权价', 'ask': 'Ask（每股美元）',
    'breakeven_before_costs': '盈亏平衡价', 'breakeven_buffer_pct': '盈亏平衡缓冲',
    'standard_contract': '标准美股合约（每张 100 股）', 'not_suspended': '未停牌',
    'same_session_snapshot': '报价属于当前交易日', 'days_to_expiry': '剩余到期天数（自然日）',
    'otm_pct': '价外幅度', 'abs_delta': '|Delta|', 'bid': 'Bid（每股美元）',
    'bid_size': '买方报价数量', 'open_interest': '未平仓量', 'volume': '当日成交量',
    'spread_pct_of_mid': '买卖价差 / 中间价', 'earnings_known': '已知下次财报日且日历抓取完整',
    'days_expiry_before_earnings': '到期早于财报的天数', 'trend_allowed': '标的通过全部趋势检查',
    'distance_to_ma50_pct': '收盘相对 MA50 的幅度', 'ma50_slope_5d_pct': 'MA50 五日斜率',
    'breakdown_20d': '收盘跌破此前 20 日低点', 'rsi14': 'RSI14',
    'macd_histogram_change': 'MACD 柱较前日变化', 'cash_collateral': '现金担保（美元）',
    'annualized_gross_return_pct': '现金担保权利金简单年化',
    'daily_gross_return_pct': '日均权利金毛收益率',
    'expiration': '到期日',
    'return_score': '收益分', 'risk_score': '风险分（越低越好）', 'composite_score': '综合分',
    'gross_return_pct': '权利金 / 担保本金',
    'premium_per_contract_before_costs': '每张权利金（费用前）',
}
FLAGS = {'standard_contract', 'not_suspended', 'same_session_snapshot', 'earnings_known',
         'trend_allowed', 'breakdown_20d'}
ERRORS = {'Invalid implied volatility': '隐含波动率无效',
    'Need a positive, uncrossed two-sided quote with bid below strike': '缺少有效双边报价，或 Bid/Ask 倒挂',
    'Invalid PUT delta': 'Put Delta 无效',
    'Chain and snapshot identities / contract sizes do not match': '合约表与报价身份或合约股数不一致'}


def value_text(metric, value):
    if value is None: return '未知 / 缺失'
    if metric in FLAGS: return '是' if value else '否'
    if isinstance(value, (int, float)):
        suffix = '%' if metric.endswith('_pct') or metric == 'spread_pct_of_mid' else ''
        return f'{value:,.4f}'.rstrip('0').rstrip('.') + suffix
    return str(value)


def condition_text(rule):
    _, metric, op, threshold = rule
    label = METRICS.get(metric, metric)
    if metric in FLAGS and op == '==': return label + '：' + value_text(metric, threshold)
    return f'{label} {op} {value_text(metric, threshold)}'


def table(headers, rows):
    head = ''.join(f'<th align="left">{escape(str(h))}</th>' for h in headers)
    body = ''.join('<tr>' + ''.join('<td>' + escape(str(v)).replace('\n', '<br>') + '</td>' for v in row) + '</tr>' for row in rows)
    return f'<table width="98%" cellpadding="5" cellspacing="0"><tr>{head}</tr>{body}</table>'


def rules_html(config):
    content = '<h2>筛选条件</h2><p>只要求已启用的 Filter 全部通过，再按独立 Sort 排序。阈值为初版研究规则，尚未经回测。</p>'
    content += '<h3>标的趋势</h3>' + table(['条件'], [[condition_text(r)] for r in config['trend_rules']])
    content += '<h3>合约条件</h3>' + table(['条件'], [[condition_text(r)] for r in config['rules']])
    content += '<p>还需有有效 Bid/Ask、Put Delta、合约身份、股数及已完成日线；缺少关键数据会排除。IV 仅展示，不参与当前排序；接口返回 IV=0 时记为未知。</p>'
    order = sort_description(config['sort_order'])
    content += '<h3>通过后的排序</h3><p>' + escape(order) + '</p>'
    content += '<p>日均毛收益率 = 权利金 ÷ 全额担保本金 ÷ 剩余自然日 × 100%；简单年化为日均值 × 365。这是完整保留权利金时的比较指标，不是实际每天盈利。按一张标准合约计算，不含费用，不保证成交；桌面尚未校验个人预算。</p>'
    content += '<p>财报未知不等于没有财报。用户关闭财报 Filter 后可留下合约，但未知状态仍会显示。</p>'
    return content


def sort_description(order):
    return ' → '.join(METRICS.get(metric, metric) + ('从高到低' if direction == 'desc' else '从低到高') for metric, direction in order)


def ranking_html(report):
    primary = report['sort_order'][0][0]
    rows = [[row['rank'], row['code'], value_text(primary, row['metrics'][primary])] for row in report['ranked'][:10]]
    return '<h3>候选排序（前10名）</h3>' + table(['排名', '合约', METRICS.get(primary, primary)], rows)


def recommendations_html(report):
    choices = report.get('recommendations', [])
    if not choices: return ''
    content = f'<h3>Top {report.get("top_n_requested", 10)} · 规则引擎的到期日 / 行权价比较</h3>'
    if len(choices) < report.get('top_n_requested', 10): content += f'<p>风险边界内只有 {len(choices)} 份合约，返回实际数量。</p>'
    content += table(['排名', '到期 / 天数', '行权价 / 成本', '日均毛收益率', '风险分↓', '综合分↑'],
        [[c['overall_rank'], f"{c['expiration']}\n{c['days_to_expiry']} 天",
          f"${c['strike']:,.2f}\n${c['cash_collateral']:,.0f}", f"{c['daily_gross_return_pct']:.4f}%",
          f"{c['risk_score']:.2f}", f"{c['composite_score']:.2f}"] for c in choices])
    p = report['configuration']['scoring']['parameters']
    content += f'<p>担保成本 = 行权价 ×100股。收益分 = min(100, 日均毛收益率 / {p["daily_return_target_pct"]:g}% ×100)。综合分 = {100*p["return_weight"]:g}% ×收益分 + {100*(1-p["return_weight"]):g}% ×(100−风险分)。评分参数为研究示例，未回测校准。</p>'
    content += '<p>日均毛收益率 = 权利金 ÷ 担保本金 ÷ 剩余自然日 × 100%。假设完整保留权利金；不是实际每天到账的收益，股价下跌可产生亏损。</p>'
    return content


def score_breakdown_html(choice, heading='首选的评分依据'):
    scoring = choice['scoring']
    content = '<h3>' + escape(heading) + '</h3>'
    content += table(['风险维度', '分数', '权重', '贡献分'],
        [[c['label'] + ('（信息缺失）' if not c['known'] else ''), f"{c['score']:.2f}",
          f"{c['weight_pct']:.1f}%", f"{c['contribution']:.2f}"] for c in scoring['components']])
    content += '<ul>' + ''.join('<li>' + escape(c['explanation']) + '</li>' for c in scoring['components']) + '</ul>'
    content += f'<p>有数据支持的风险权重覆盖率 {scoring["evidence_coverage_pct"]:.1f}%；未知项按设置计惩罚分。风险分是相对研究指标，不是亏损概率；部分维度相关，不代表独立风险。</p>'
    content += '<h3>选择理由与取舍</h3><ul>' + ''.join('<li>' + escape(r) + '</li>' for r in choice['reasons']+choice['tradeoffs']) + '</ul>'
    if choice['risk_notes']: content += '<p>需复核：' + escape('；'.join(choice['risk_notes'])) + '</p>'
    return content


def explanation_html(report):
    content = '<h3>筛选依据与排除原因</h3>'
    configuration = report.get('configuration', {})
    options = configuration.get('filters', {})
    trend_options = configuration.get('trend_filters', {})
    trend_enabled = options.get('underlying-trend', {}).get('enabled', True)
    disabled = report.get('disabled_filters', [])
    if disabled:
        sources = {rid: metric for rid, metric, _, _ in report.get('all_rules', report['rules'])}
        content += '<p><b>已关闭的 Filter：</b>' + escape('、'.join(METRICS.get(sources.get(rid), rid) for rid in disabled)) + '。这些条件不参与排除，相关风险仍需复核。</p>'
    for code, trend in report['underlyings'].items():
        state = '趋势 Filter 已关闭（以下仅作参考）' if not trend_enabled else '已选趋势 Filter 通过' if trend['allowed'] else '已选趋势 Filter 未通过'
        content += f'<p><b>{escape(code)}：{state}</b></p>'
        if trend['status'] != 'ok':
            content += '<p>日线数据无法验证：' + escape(trend.get('error', '未知原因')) + '</p>'
            continue
        metrics = trend['metrics']
        content += f'<p>日线 {escape(trend["as_of"])}：收盘 {metrics["close"]:.2f}，MA50 {metrics["ma50"]:.2f}。</p>'
        selected = {r['id']: r for r in trend['rules']}
        rows = []
        for reference in trend.get('reference_rules', trend['rules']):
            r = selected.get(reference['id'], reference)
            enabled = trend_enabled and trend_options.get(r['id'], {}).get('enabled', True)
            rows.append([condition_text((r['id'], r['metric'], r['op'], r['threshold'])),
                         value_text(r['metric'], r['actual']), ('通过' if r['passed'] else '未通过') if enabled else '未启用'])
        content += table(['趋势条件', '实际值', '结果'], rows)
    valid = [row for row in report['results'] if row['status'] == 'ok']
    counts = Counter(r for row in valid for r in row['failed_rules'])
    content += f'<h3>合约条件逐项检查</h3><p>以下统计针对 {len(valid)} 个基础数据有效的合约；同一合约可同时违反多个条件，不能将各项数量相加。</p>'
    content += table(['条件', '未通过 / 已评估'],
                     [[condition_text(r), f'{counts[r[0]]} / {len(valid)}'] for r in report['rules']])
    if report.get('qualified_count') == 0 and report.get('filter_impact'):
        sources = {r[0]: r for r in report['rules']}
        content += '<h3>放宽预览（尚未应用）</h3><p>下面只展示模拟数量，不会替你修改 Filter。基础数据无效的合约不会被放回。</p>'
        candidates = [r for r in report['filter_impact'] if r['id'] not in ('standard-contract', 'not-suspended') and r['excluded_count']]
        content += table(['如果关闭这一项', '预计候选数'], [[condition_text(sources[r['id']]), r['qualified_without_filter']] for r in candidates])
        group_labels = {frozenset({'underlying-trend'}): '关闭整个趋势 Filter',
                        frozenset({'earnings-checked', 'earnings-buffer'}): '同时关闭两项财报 Filter',
                        frozenset({'earnings-checked', 'earnings-buffer', 'underlying-trend'}): '同时关闭趋势与财报 Filter'}
        content += table(['组合模拟', '预计候选数'], [[group_labels.get(frozenset(r['disabled_filters']), '关闭多项'), r['qualified_count']] for r in report.get('relaxation_preview', [])])
    errors = Counter(row['error'] for row in report['results'] if row['status'] == 'invalid_data')
    if errors:
        content += '<h3>基础数据问题</h3>' + table(['原因', '合约数'], [[ERRORS.get(e, e), count] for e, count in errors.most_common()])
    content += '<p>点「Filter / 评分设置」调整条件；点击候选表头排序。导出 JSON 可查看原始数据、配置及每个合约的实际值、阈值和未通过项。</p>'
    return content
