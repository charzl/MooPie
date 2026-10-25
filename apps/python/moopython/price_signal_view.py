"""Presentation for descriptive signals; no ranking logic or dependencies on Qt."""
from html import escape


def _zone_price(zones):
    if not zones: return '暂无已确认区间'
    zone = zones[0]
    return f'${zone["low"]:,.2f}–${zone["high"]:,.2f}'


def _overlap(left, right):
    return bool(left and right and max(left[0]['low'], right[0]['low']) <=
                min(left[0]['high'], right[0]['high']))


def _multi_timeframe_html(signal):
    multi = signal.get('multi_timeframe')
    if not multi: return ''
    if multi.get('status') != 'ok':
        return '<h3>周线 / 月线参考</h3><p>多周期价位不可用：'+escape(multi.get('reason', '数据不完整'))+'</p>'
    content = '<h3>日线、周线与月线价位</h3>'
    content += '<p>周 / 月周期由同一批已验证日线汇总，未结束的周期不参与确认。</p>'
    content += '<table width="100%" cellspacing="0" cellpadding="8"><tr><th>周期</th><th>下方支撑</th><th>上方阻力</th><th>数据截至</th></tr>'
    periods = [('日线', signal), ('周线', multi['periods']['week']), ('月线', multi['periods']['month'])]
    for label, item in periods:
        if item.get('status') != 'ok':
            content += '<tr><td>'+label+'</td><td colspan="3">'+escape(item.get('reason', '数据不足'))+'</td></tr>'
            continue
        content += ('<tr><td><b>'+label+'</b></td>'
                    '<td><span style="color:#32b873"><b>'+_zone_price(item['support_zones'])+'</b></span></td>'
                    '<td><span style="color:#e26060"><b>'+_zone_price(item['resistance_zones'])+'</b></span></td>'
                    '<td>'+escape(item['as_of'])+'</td></tr>')
    content += '</table>'
    aligned = []
    for label, item in periods[1:]:
        if item.get('status') == 'ok' and _overlap(signal['support_zones'], item['support_zones']):
            aligned.append('日线与'+label)
    if (multi['periods']['week'].get('status') == 'ok' and multi['periods']['month'].get('status') == 'ok'
            and _overlap(multi['periods']['week']['support_zones'], multi['periods']['month']['support_zones'])):
        aligned.append('周线与月线')
    content += ('<p><b>支撑区间重叠：</b>'+('、'.join(aligned) if aligned else '未观察到')
                +'。仅表示价格区间相交，不代表更高胜率。</p>')
    return content


def signals_html(signals):
    content = '<h2>价格位置与择时信号</h2><p>独立展示，暂不参与 Filter、收益分、风险分、综合分或排序。</p>'
    if not signals:
        return content+'<p>暂无价格信号，请先查询股票或 Watchlist。</p>'
    for symbol, signal in signals.items():
        content += '<hr><h3>'+escape(symbol)+' · '+escape(signal['summary'])+'</h3>'
        if signal['status'] != 'ok':
            content += '<p>数据不足：'+escape(signal.get('reason', '日线未验证'))+'</p>'
            continue
        reference = signal['reference']
        basis = '标的 last_price（不替换为盘后价）' if reference['basis']=='underlying_snapshot' else '已完成日线收盘'
        time_label = '快照更新时间（纽约）' if reference['basis']=='underlying_snapshot' else '日线日期'
        content += (f'<p>{basis}：<b>${reference["price"]:,.2f}</b> · {time_label}：'
                    +escape(reference.get('time') or '报价未提供时间')+'</p>')
        content += '<p>日线截至 '+escape(signal['as_of'])+f' · 分析最近 {signal["lookback_bars"]} 根日线</p>'
        cards = []
        for field, title, background, foreground in (
                ('support_zones', '下方潜在支撑', '#153527', '#a7f3c5'),
                ('resistance_zones', '上方潜在阻力', '#482425', '#ffc1c1')):
            zone = signal[field][0] if signal[field] else None
            value = (f'${zone["low"]:,.2f}–${zone["high"]:,.2f}' if zone else '暂无已确认区间')
            distance = (f'距区域边缘 {zone["distance_pct"]:.2f}%' if zone else '等待后续日线确认')
            cards.append(f'<td width="50%" bgcolor="{background}" style="padding:12px;">'
                         f'<p style="color:{foreground};font-size:13px;">{title}</p>'
                         f'<p style="color:{foreground};font-size:21px;"><b>{value}</b></p>'
                         f'<p style="color:{foreground};font-size:12px;">{distance}</p></td>')
        content += '<table width="100%" cellspacing="8"><tr>'+''.join(cards)+'</tr></table>'
        content += _multi_timeframe_html(signal)
        for field, title in [('support_zones', '下方潜在支撑'), ('resistance_zones', '上方潜在阻力')]:
            content += '<h4>'+title+'</h4>'
            if not signal[field]:
                direction = '下方的转折低点' if field == 'support_zones' else '上方的转折高点'
                content += '<p>日线已通过验证；分析窗口内未找到位于参考价'+direction+'且已得到后续日线确认的区域，因此暂无可确认价位。</p>'
                continue
            content += '<table cellspacing="0" cellpadding="8"><tr><th>价格区域</th><th>距区域边缘</th><th>历史转折证据</th></tr>'
            for zone in signal[field]:
                count = zone['independent_touches']
                strength = '多次转折' if count>1 else '单次转折，依据有限'
                dates = '、'.join(escape(p['date']) for p in zone['evidence'])
                content += (f'<tr><td>${zone["low"]:,.2f}–${zone["high"]:,.2f}</td>'
                            f'<td>{zone["distance_pct"]:.2f}% / {zone["distance_atr"]:.2f} ATR</td>'
                            f'<td>{count} 次 · {strength}<br>{dates}</td></tr>')
            content += '</table>'
        content += '<p><b>下一步观察：</b>'+escape(signal['next_check'])+'</p>'
        content += '<ul>'+''.join('<li>'+escape(reason)+'</li>' for reason in signal['reasons'])+'</ul>'
        content += '<p><b>盘口承接 / 买卖盘比例：未验证。</b>这些价位是历史转折推断，不是正在等待成交的买单或卖单。</p>'
        content += '<p>'+escape(' '.join(signal['limitations']))+'</p>'
        content += '<p>信号版本 '+escape(signal['version'])+' · 条件判断未经回测，不代表胜率。</p>'
    return content
