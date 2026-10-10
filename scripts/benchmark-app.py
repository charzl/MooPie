"""Three matched offline UI trials. Poll RSS externally; CPU deltas come from each process."""
import argparse, hashlib, json, os, pathlib, platform, plistlib, statistics, subprocess, time

def percentile(values, p):
    values=sorted(values); return values[min(len(values)-1,int((len(values)-1)*p))]

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('app'); parser.add_argument('output'); parser.add_argument('--trials',type=int,default=3)
    args=parser.parse_args(); app=pathlib.Path(args.app).resolve(); output=pathlib.Path(args.output).resolve()
    output.parent.mkdir(parents=True,exist_ok=True)
    fixture=pathlib.Path(__file__).resolve().parent.parent/'fixtures/market.json'
    info=plistlib.loads((app/'Contents/Info.plist').read_bytes()); binary=app/'Contents/MacOS'/info['CFBundleExecutable']
    results=[]
    for trial in range(args.trials):
        raw=output.parent/f'{output.stem}-trial-{trial+1}.json'; phase=pathlib.Path(str(raw)+'.phase.json')
        raw.unlink(missing_ok=True); phase.unlink(missing_ok=True)
        env=dict(os.environ,MOOMOO_BENCHMARK_FIXTURE=str(fixture),QT_QPA_PLATFORM='offscreen',QT_SCALE_FACTOR='1')
        samples={'idle':[],'replay':[]}; ready=None; start=time.monotonic()
        with (output.parent/f'{output.stem}-trial-{trial+1}.log').open('w') as log:
            process=subprocess.Popen([str(binary),'--benchmark-output',str(raw)],env=env,stdout=log,stderr=log)
            try:
                while process.poll() is None:
                    if time.monotonic()-start>90: raise TimeoutError('Benchmark timed out')
                    state=None
                    if phase.exists():
                        try: state=json.loads(phase.read_text())['phase']
                        except (ValueError,KeyError): pass
                    if state and ready is None: ready=time.monotonic()-start
                    if state in samples:
                        rss=subprocess.run(['ps','-p',str(process.pid),'-o','rss='],capture_output=True,text=True).stdout.strip()
                        if rss: samples[state].append(int(rss)/1024)
                    time.sleep(.05 if ready is None else .25)
                if process.returncode: raise RuntimeError(f'App exited {process.returncode}; see {log.name}')
            finally:
                if process.poll() is None: process.kill(); process.wait()
        result=json.loads(raw.read_text()); assert result['render_pixels']==[1500,900] and result['frame_count']==120
        result['startup_to_first_snapshot_seconds']=ready
        for state in samples:
            assert samples[state], f'No RSS samples for {state}'
            result[state]['rss_mib_median']=statistics.median(samples[state])
            result[state]['rss_mib_peak']=max(samples[state])
            result[state]['cpu_percent']=100*result[state]['cpu_seconds']/result[state]['wall_seconds']
        values=result['update_and_snapshot_ms']
        result['render_ms_p50']=percentile(values,.5); result['render_ms_p95']=percentile(values,.95)
        result['over_50ms_count']=sum(value>50 for value in values)
        results.append(result)
    fields=['startup_to_first_snapshot_seconds','render_ms_p50','render_ms_p95','over_50ms_count']
    summary={key:statistics.median(r[key] for r in results) for key in fields}
    summary.update({f'{state}_{field}':statistics.median(r[state][field] for r in results) for state in ('idle','replay') for field in ('cpu_percent','rss_mib_median','rss_mib_peak')})
    hardware={key:subprocess.check_output(['sysctl','-n',key],text=True).strip() for key in ('machdep.cpu.brand_string','hw.memsize','hw.ncpu')}
    final=dict(schema=1,implementation=results[0]['implementation'],fixture_sha256=hashlib.sha256(fixture.read_bytes()).hexdigest(),
        workload=dict(symbols=13,candles=180,logical_size=[1500,900],render_pixels=[1500,900],idle_seconds=5,frames=120,requested_updates_per_second=20,switch_symbol_every_frames=10),
        architecture=platform.machine(),os=platform.platform(),hardware=hardware,commit=os.environ.get('GITHUB_SHA','local'),
        note='Offline SDK-loaded UI update + snapshot benchmark. No OpenD connection, network, trading or display/GPU FPS measurement. Separate runner VMs can introduce noise. Startup includes SDK loading and is sampled to 50ms.',
        bundle_disk_mib=int(subprocess.check_output(['du','-sk',str(app)],text=True).split()[0])/1024,summary=summary,trials=results)
    output.write_text(json.dumps(final,indent=2)); print(json.dumps(summary,indent=2))
if __name__=='__main__': main()
