"""Compare actual sampled visible depth in stable current price buckets."""
from datetime import datetime, timedelta, timezone

from .order_book import auto_bucket_width, quote_reference, visible_price_buckets


def bucket_timeline(history, current_book, quote, *, now=None):
    """Show 1/5/15-minute samples for today's largest visible bucket per side."""
    reference = quote_reference(quote)['price']
    if not reference or not current_book or current_book.get('status') != 'ok':
        return {}
    width = auto_bucket_width(reference)
    current = visible_price_buckets(current_book, width, reference, anchor_to_reference=True)
    now = now or datetime.now(timezone.utc)
    result = {}
    for side in ('bids', 'asks'):
        target = max((bucket for bucket in current[side]
                      if bucket['kind'] == 'normal' and bucket['volume'] > 0),
                     key=lambda bucket: bucket['volume'], default=None)
        if target is None:
            continue
        windows = []
        for minutes in (1, 5, 15):
            cutoff = now - timedelta(minutes=minutes)
            samples = []
            for record in history:
                stamp = datetime.fromisoformat(record['collected_at'])
                if stamp.tzinfo is None or not cutoff <= stamp <= now:
                    continue
                book = record['book']
                if book.get('status') != 'ok':
                    continue
                value = sum(row['price'] * row['volume'] for row in book.get(side, [])
                            if target['low'] <= row['price'] < target['high'])
                samples.append((stamp, round(value, 2)))
            samples.sort()
            windows.append(dict(minutes=minutes, samples=len(samples),
                                points=[dict(time=stamp.isoformat(), value=value)
                                        for stamp, value in samples] if minutes == 15 else [],
                                first_at=samples[0][0].isoformat() if samples else None,
                                last_at=samples[-1][0].isoformat() if samples else None,
                                first=samples[0][1] if samples else None,
                                latest=samples[-1][1] if samples else None,
                                average=round(sum(value for _, value in samples)/len(samples), 2)
                                        if samples else None))
        result[side] = dict(bucket=target, windows=windows)
    return result
