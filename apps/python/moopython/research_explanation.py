"""Human-readable evidence from the actual rule configuration and report."""
from collections import Counter
from html import escape

METRICS = {
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
    body = ''.join('<tr>' + ''.join(f'<td>{escape(str(v))}</td>' for v in row) + '</tr>' for row in rows)
    return f'<table width="100%" cellpadding="5" cellspacing="0"><tr>{head}</tr>{body}</table>'


def rules_html(config):
    content = '<h2>筛选条件</h2><p>以下条件必须全部通过，再比较收益。阈值为初版研究规则，尚未经回测。</p>'
    content += '<h3>标的趋势</h3>' + table(['条件'], [[condition_text(r)] for r in config['trend_rules']])
    content += '<h3>合约条件</h3>' + table(['条件'], [[condition_text(r)] for r in config['rules']])
    content += '<p>还需有有效 Bid/Ask、Put Delta、合约身份、股数及已完成日线；缺少关键数据会排除。IV 仅展示，不参与当前排序；接口返回 IV=0 时记为未知。</p>'
    order = ' → '.join(METRICS.get(metric, metric) + ('从高到低' if direction == 'desc' else '从低到高') for metric, direction in config['sort_order'])
    content += '<h3>通过后的排序</h3><p>' + escape(order) + '</p>'
    content += '<p>简单年化 = Bid ÷ 行权价 × 365 ÷ 到期天数 × 100%。按一张标准合约全额现金担保，不含费用，不保证成交；桌面尚未校验个人预算。</p>'
    content += '<p>财报未知不等于没有财报。未全部通过的合约不会被标成推荐。</p>'
    return content


def explanation_html(report):
    content = '<h3>筛选依据与排除原因</h3>'
    for code, trend in report['underlyings'].items():
        content += f'<p><b>{escape(code)}：{"趋势通过" if trend["allowed"] else "趋势未通过"}</b></p>'
        if trend['status'] != 'ok':
            content += '<p>日线数据无法验证：' + escape(trend.get('error', '未知原因')) + '</p>'
            continue
        metrics = trend['metrics']
        content += f'<p>日线 {escape(trend["as_of"])}：收盘 {metrics["close"]:.2f}，MA50 {metrics["ma50"]:.2f}。</p>'
        rows = [[condition_text((r['id'], r['metric'], r['op'], r['threshold'])),
                 value_text(r['metric'], r['actual']), '通过' if r['passed'] else '未通过'] for r in trend['rules']]
        content += table(['趋势条件', '实际值', '结果'], rows)
    valid = [row for row in report['results'] if row['status'] == 'ok']
    counts = Counter(r for row in valid for r in row['failed_rules'])
    content += f'<h3>合约条件逐项检查</h3><p>以下统计针对 {len(valid)} 个基础数据有效的合约；同一合约可同时违反多个条件，不能将各项数量相加。</p>'
    content += table(['条件', '未通过 / 已评估'],
                     [[condition_text(r), f'{counts[r[0]]} / {len(valid)}'] for r in report['rules']])
    errors = Counter(row['error'] for row in report['results'] if row['status'] == 'invalid_data')
    if errors:
        content += '<h3>基础数据问题</h3>' + table(['原因', '合约数'], [[ERRORS.get(e, e), count] for e, count in errors.most_common()])
    content += '<p>点「筛选条件」查看完整规则；导出 JSON 可查看每个合约的实际值、阈值和未通过项。</p>'
    return content
