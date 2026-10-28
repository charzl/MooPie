"""Bilingual presentation of support studies; calculations stay in the engine."""
from html import escape


STATE_LABELS = {
    'active': ('已确认 · 待测试', 'Confirmed · waiting for test'),
    'testing': ('正在测试', 'Testing'), 'held': ('触及后收回上沿', 'Closed above after test'),
    'broken': ('收盘已跌破', 'Closed below support'),
    'broken_retest': ('跌破后反抽区间内', 'Retesting after break'),
    'resistance': ('跌破后反抽受阻', 'Retest rejected after break'),
    'reclaimed': ('跌破后已收复', 'Reclaimed after break'),
    'basis_changed': ('历史数据已修订 · 停止延续', 'History revised · tracking stopped'),
    'history_gap': ('衔接日线缺失 · 停止延续', 'History gap · tracking stopped'),
}
EVENT_LABELS = {
    'created': ('冻结区间并开始跟踪', 'Region frozen; tracking began'),
    'test': ('日内触及支撑区', 'Daily range touched support'), 'held': ('收盘站回区间上沿', 'Closed above upper edge'),
    'break': ('收盘跌破区间下沿', 'Closed below lower edge'),
    'resistance_test': ('跌破后反抽测试', 'Retest after break'),
    'resistance': ('反抽后收盘仍低于下沿', 'Retest closed below lower edge'),
    'reclaim': ('收盘重新站上上沿', 'Closed above upper edge again'),
    'basis_changed': ('历史数据修订，原区间不再延续', 'History revised; original region no longer advanced'),
    'history_gap': ('缺少衔接日线，原区间不再延续', 'Missing bridging bars; original region no longer advanced'),
}


def _pct(value):
    return '—' if value is None else f'{value:+.2f}%'


def _range(zone):
    return f'${zone["low"]:,.2f}–${zone["high"]:,.2f}'


def _state(record, english):
    color = ('#e26060' if record['state'] in ('broken', 'resistance') else
             '#b78718' if record['state'] in ('testing', 'broken_retest', 'basis_changed', 'history_gap') else '#269e60')
    return '<b style="color:'+color+'">'+STATE_LABELS[record['state']][int(english)]+'</b>'


def _table(headers, rows):
    return ('<table width="99%" cellspacing="0" cellpadding="6"><tr>'
            + ''.join('<th align="left">'+header+'</th>' for header in headers)+'</tr>'
            + ''.join('<tr>'+''.join('<td>'+cell+'</td>' for cell in row)+'</tr>' for row in rows)+'</table>')


def _opening(study, title, english):
    content = '<h2>'+title+'</h2>'
    if not study:
        return content+('<p>Open a stock detail to calculate from validated daily bars.</p>' if english else
                        '<p>打开个股详情后，使用已验证日线计算。</p>'), False
    if study.get('status') != 'ok':
        return content+('<p>Unavailable: ' if english else '<p>暂不可用：')+escape(study.get('reason', ''))+'</p>', False
    start = study['input_series']['bars'][0]['date']
    content += (f'<p>{escape(study["symbol"])} · {start} → {study["as_of"]} · '
                + ('Historical reconstruction using the current adjusted daily history.' if english else
                   '使用当前版本前复权日线进行历史重建。')+'</p>')
    return content, True


def backtest_html(study, language='zh'):
    english = language == 'en'
    content, ready = _opening(study, 'Support Touch Study' if english else '支撑区触及后表现回测', english)
    if not ready: return content
    backtest = study['backtest']
    params = study['definition']['parameters']
    content += ('<p>The nearest support is frozen at the previous close. A later low reaching its upper edge, '
                'including a gap below it, starts an event. The reference is the touch-day close; later '
                'highs and lows start on the next trading day. Sample windows do not overlap.</p>' if english else
                '<p>在前一交易日收盘冻结最近支撑区；之后日内低点触及上沿或跳空穿过区间时计入样本。'
                '表现以触及当日收盘为基准，最高／最低价从下一交易日起统计。样本窗口不重叠。</p>')
    content += (f'<p>{backtest["sample_count"]} events · {params["warmup_bars"]} warm-up bars · '
                f'{params["separation_bars"]} trading days between windows.</p>' if english else
                f'<p>共 {backtest["sample_count"]} 个触及样本 · 前 {params["warmup_bars"]} 根为预热 · '
                f'每个样本后间隔 {params["separation_bars"]} 个交易日。</p>')
    headers = (['Horizon', 'Complete / pending', 'Positive closes', 'Median close return', 'Median max rise',
                'Median max drop', 'Worst drop', 'Close below support'] if english else
               ['观察期', '完成／待观察', '收盘上涨次数', '收盘涨跌中位数', '最大反弹中位数',
                '最大下跌中位数', '最差下跌', '收盘跌破次数'])
    rows = []
    for summary in backtest['summaries']:
        total = summary['complete']
        rows.append([str(summary['horizon'])+(' days' if english else ' 个交易日'),
                     f'{total} / {summary["pending"]}', f'{summary["positive"]} / {total}',
                     _pct(summary['median_return_pct']), _pct(summary['median_max_rise_pct']),
                     _pct(summary['median_max_drop_pct']), _pct(summary['worst_drop_pct']),
                     f'{summary["broken"]} / {total}'])
    content += _table(headers, rows)
    if any(row['small_sample'] for row in backtest['summaries']):
        content += (f'<p><b>Limited sample: fewer than {params["minimum_summary_samples"]} completed events in at least one horizon.</b></p>' if english else
                    f'<p><b>样本偏少：至少一个观察期不足 {params["minimum_summary_samples"]} 个完成样本。</b></p>')
    content += ('<p>Counts describe this historical sample; they are not calibrated probabilities. '
                'Pending windows are excluded from summary statistics. A break uses a close strictly below the frozen lower edge, '
                'including the touch-day close. Adjusted history can be revised; this does not simulate fills, fees, slippage or total return.</p>' if english else
                '<p>次数描述当前历史样本，不是经过校准的概率。待观察样本不进入汇总；跌破指收盘严格低于冻结下沿，'
                '包含触及当日收盘。复权历史可能修订；这里未模拟成交、费用、滑点或分红总收益。</p>')
    content += '<h3>'+('Recent events' if english else '最近触及记录')+'</h3>'
    rows = []
    for sample in reversed(backtest['samples'][-50:]):
        values = [escape(sample['touch_date']), escape(sample['signal_date']), _range(sample['zone']),
                  f'${sample["reference_price"]:,.2f}'+(' · gap' if english else ' · 跳空穿过') if sample['gap_through'] else f'${sample["reference_price"]:,.2f}']
        values.extend(_pct(outcome['close_return_pct']) if outcome['status'] == 'complete' else
                      (f'Pending ({outcome["observed_bars"]}d)' if english else f'待观察（已 {outcome["observed_bars"]} 日）')
                      for outcome in sample['outcomes'])
        rows.append(values)
    content += _table((['Touch date', 'Defined at close', 'Frozen support', 'Reference close', '5d close', '10d close', '20d close'] if english else
                       ['触及日期', '区间确定于收盘', '冻结支撑区', '参考收盘', '5 日收盘表现', '10 日收盘表现', '20 日收盘表现']), rows)
    if not rows: content += '<p>'+('No qualifying touch in the available history.' if english else '现有历史中没有符合定义的触及样本。')+'</p>'
    content += '<p>'+('Displays the latest 50 events; export includes every event, input bar and parameter.' if english else
                     '页面显示最近 50 个事件；导出包含全部事件、原始日线和参数。')+'</p>'
    return content


def lifecycle_html(study, language='zh'):
    english = language == 'en'
    content, ready = _opening(study, 'Frozen Support Lifecycle' if english else '冻结支撑区生命周期', english)
    if not ready: return content
    content += ('<p>Each region keeps the boundaries observed at its tracking start. Later daily closes advance its state; '
                'a recalculated region does not move these boundaries. Early events are reconstructed from history.</p>' if english else
                '<p>每个区域固定使用首次跟踪时的上下沿，后续已完成日线推进状态；重新计算价位不会移动这条记录的边界。'
                '早期事件由历史日线重建，不代表当时已实际记录。</p>')
    if study['lifecycle']['notices']:
        content += '<p><b>'+('History changed or bridging bars are missing. Affected old regions stop advancing; new reconstructions are listed separately.' if english else
                             '历史数据修订或衔接日线缺失：受影响旧区间已停止延续，新重建记录单独保留。')+'</b></p>'
    records = sorted(study['lifecycle']['records'], key=lambda item: (item['detected_at'], item['zone_id']), reverse=True)[:50]
    headers = (['Frozen region', 'First pivot confirmed', 'Tracking start', 'State', 'Support tests / breaks', 'Through'] if english else
               ['冻结价格区间', '首个转折确认', '首次跟踪', '当前状态', '测试／跌破次数', '状态截至'])
    rows = []
    for record in records:
        label = _state(record, english)
        rows.append([f'<a href="#zone-{record["zone_id"]}">{_range(record)}</a>', record['formed_at'],
                     record['detected_at'], label, f'{record["tests"]} / {record["breaks"]}',
                     record.get('stopped_at', record['last_evaluated'])])
    content += _table(headers, rows)
    if not records: content += '<p>'+('No confirmed support region to track in this history.' if english else '现有历史中没有可跟踪的已确认支撑区。')+'</p>'
    for record in records:
        content += f'<a name="zone-{record["zone_id"]}"></a><h3>'+_range(record)+' · '+STATE_LABELS[record['state']][int(english)]+'</h3>'
        evidence = sorted(record['evidence'], key=lambda item: item['date'])[-8:]
        content += '<p>'+('Pivot evidence (latest 8): ' if english else '转折证据（最近 8 条）：')
        content += '<br>'.join(escape(item['date'])+f' · ${item["price"]:,.2f} · '
                              + ('confirmed ' if english else '确认于 ')+escape(item['confirmed_at'])
                              for item in evidence)+'</p>'
        events = record['events'][-30:]
        content += _table(['Date', 'Event', 'Close'] if english else ['日期', '观察到的事件', '当日收盘'],
                          [[event['date'], EVENT_LABELS[event['kind']][int(english)]
                            + ((' · gap through' if english else ' · 跳空穿过') if event.get('gap_through') else ''),
                            f'${event["close"]:,.2f}'] for event in events])
    content += '<p>'+('Displays 50 recent regions and 30 recent events per region; export includes the full history. '
                     'Tests use daily range overlap; consecutive contact days count once per role. Rejection after a break is a daily price observation.' if english else
                     '页面显示最近 50 个区域及各自最近 30 条事件，导出保留完整历史。测试按日内价格范围相交判断，'
                     '同一角色下连续接触只计一次；跌破后反抽受阻是日线价格观察。')+'</p>'
    return content


def zone_context_html(study, signal, language='zh'):
    if not study or study.get('status') != 'ok' or not signal or signal.get('status') != 'ok': return ''
    english = language == 'en'
    rows = []
    for zone in signal.get('support_zones', []):
        dates = {item['date'] for item in zone['evidence']}
        matches = [record for record in study['lifecycle']['records']
                   if dates.intersection(item['date'] for item in record['evidence'])]
        if not matches: continue
        record = max(matches, key=lambda item: (item['state'] not in ('basis_changed', 'history_gap'), item['detected_at']))
        rows.append(_range(record)+' · '+_state(record, english))
    if not rows: return ''
    return ('<h3>'+('Related frozen support history' if english else '相关冻结支撑区状态')+'</h3><p>'
            + '<br>'.join(rows)+'</p><p>'+('Boundaries belong to the tracking record; see Support Tracking for dates.' if english else
                                                        '以上为跟踪记录的冻结边界，可能与本次重新计算区间不同；日期与事件见「支撑追踪」。')+'</p>')
