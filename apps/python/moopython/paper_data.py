"""Paper-only price inputs, collected with quote APIs and cached by the router."""
from datetime import datetime,timezone
from zoneinfo import ZoneInfo
from .market_collection import collect_daily_series,us_symbols,clean
from .account_data import records


def collect_paper_inputs(sdk,context,symbols):
    symbols=us_symbols(symbols)
    now=datetime.now(timezone.utc)
    result=collect_daily_series(sdk,context,symbols,now.astimezone(ZoneInfo('America/New_York')).date().isoformat(),now,adjustment='none')
    actions=[]
    for symbol in symbols:
        rows=records(sdk,context.get_rehab(symbol))
        actions.append(dict(symbol=symbol,rows=rows,source='moomoo OpenD get_rehab'))
    result.update(schema=1,symbols=symbols,source='moomoo OpenD raw daily bars and corporate actions',
                  decision_cutoff=now.isoformat(),fetched_at=datetime.now(timezone.utc).isoformat(),actions=actions)
    return clean(result)
