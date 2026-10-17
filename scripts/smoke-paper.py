"""Exercise a frozen application's paper dispatch and source audit resources offline."""
from datetime import date,timedelta
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


def main():
    binary=Path(sys.argv[1]).resolve()
    with tempfile.TemporaryDirectory(prefix='paper frozen smoke ') as directory:
        root=Path(directory); dates=[]; day=date(2026,10,16)
        while len(dates)<260:
            if day.weekday()<5: dates.append(day.isoformat())
            day-=timedelta(days=1)
        dates.reverse()
        bars=[dict(date=d,open=100+i,close=100+i,low=99+i,high=101+i,volume=1000,complete=True) for i,d in enumerate(dates)]
        payload=dict(daily_series=[dict(symbol='US.TEST',interval='1d',adjustment='none',session='regular',
            as_of=dates[-1],available_at=dates[-1]+'T16:05:00-04:00',trade_date_type='WHOLE',calendar_dates=dates,bars=bars)],
            actions=[dict(symbol='US.TEST',rows=[])])
        for symbol in ('US.QQQ','US.SPY'):
            row=copy.deepcopy(payload['daily_series'][0]); row['symbol']=symbol
            payload['daily_series'].append(row); payload['actions'].append(dict(symbol=symbol,rows=[]))
        source=root/'input.json'; source.write_text(json.dumps(payload),encoding='utf-8')
        result=root/'output.json'
        environment=dict(os.environ,MOOMOO_DB_PATH=str(root/'paper.sqlite3'))
        subprocess.run([str(binary),'paper','backtest','--symbols','TEST','--start',dates[254],
                        '--input',str(source),'--output',str(result)],env=environment,check=True,timeout=60)
        report=json.loads(result.read_text(encoding='utf-8'))
        assert report['mode']=='backtest' and len(report['clients'])==6 and report['fills']
        assert len(report['config']['engine_sha256'])==64
        assert all(p['status']=='pending' for c in report['clients'] for p in c['periods'])
    print('Frozen offline paper ledger and audit resources passed.')


if __name__=='__main__': main()
