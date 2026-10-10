"""Deterministic offscreen UI replay, with the official SDK imported before readiness."""
import json, math, resource, time
from dataclasses import replace
from pathlib import Path
from PySide6.QtCore import QTimer, Qt
from .market import DEFAULT_SYMBOLS, demo_quote, demo_candles

def cpu_seconds():
    usage=resource.getrusage(resource.RUSAGE_SELF)
    return usage.ru_utime+usage.ru_stime

def start(window, output):
    output=Path(output); phase=Path(str(output)+'.phase.json')
    durations=[]; started=time.monotonic(); idle_cpu=0; idle_start=0; replay_cpu=0; replay_start=0
    window.state.symbols=list(DEFAULT_SYMBOLS); window.state.favorites={'US.PLTR','US.NVDA','US.AAPL'}; window.state.red_up=True
    window.selected=DEFAULT_SYMBOLS[0]; window.period='日K'; window.show_demo()
    quotes={code:demo_quote(code) for code in DEFAULT_SYMBOLS}
    bars={code:demo_candles(code) for code in DEFAULT_SYMBOLS}
    def snapshot():
        image=window.grab().toImage()
        assert (image.width(),image.height())==(1500,900), 'Unexpected render size'
    def ready():
        nonlocal idle_cpu,idle_start
        snapshot(); idle_start=time.monotonic(); idle_cpu=cpu_seconds()
        phase.write_text(json.dumps({'phase':'idle'}))
        QTimer.singleShot(5000,replay)
    def replay():
        nonlocal replay_cpu,replay_start
        now=time.monotonic()
        window._bench_idle=dict(wall_seconds=now-idle_start,cpu_seconds=cpu_seconds()-idle_cpu)
        replay_cpu=cpu_seconds(); replay_start=time.monotonic()
        phase.write_text(json.dumps({'phase':'replay'}))
        window._benchmark_frame=0
        window._benchmark_timer=QTimer(window); window._benchmark_timer.setTimerType(Qt.TimerType.PreciseTimer)
        window._benchmark_timer.timeout.connect(tick); window._benchmark_timer.start(50)
    def tick():
        i=window._benchmark_frame; begin=time.monotonic(); delta=math.sin(i*.1)*.25
        code=DEFAULT_SYMBOLS[(i//10)%len(DEFAULT_SYMBOLS)]
        window.state.quotes={key:replace(q,price=q.price+delta) for key,q in quotes.items()}
        window.state.sparks={key:[b.close for b in bars[key][-59:]]+[q.price] for key,q in window.state.quotes.items()}
        window.selected=code
        data=list(bars[code]); last=data[-1]; close=last.close+delta
        data[-1]=replace(last,close=close,high=max(last.high,close),low=min(last.low,close))
        window.chart.set_bars(data,'日K'); window.update_table(); window.update_heading()
        snapshot(); durations.append((time.monotonic()-begin)*1000)
        window._benchmark_frame+=1
        if window._benchmark_frame==120:
            window._benchmark_timer.stop()
            result=dict(schema=1,implementation='python-qt',render_pixels=[1500,900],frame_count=120,
                idle=window._bench_idle,replay=dict(wall_seconds=time.monotonic()-replay_start,cpu_seconds=cpu_seconds()-replay_cpu),
                update_and_snapshot_ms=durations,sdk_loaded=True,opend_connected=False,fixture_first_quote=quotes[DEFAULT_SYMBOLS[0]].price)
            output.write_text(json.dumps(result,indent=2)); phase.write_text(json.dumps({'phase':'done'})); window.close()
    QTimer.singleShot(0,ready)
