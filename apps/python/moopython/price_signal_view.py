"""Presentation for descriptive signals; no ranking logic or dependencies on Qt."""
from html import escape


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
        for field, title in [('support_zones', '下方潜在支撑'), ('resistance_zones', '上方潜在阻力')]:
            content += '<h4>'+title+'</h4>'
            if not signal[field]:
                content += '<p>当前历史范围内没有足够的转折依据，不推测具体价位。</p>'
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
