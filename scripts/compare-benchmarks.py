"""Validate matched workloads and emit a per-metric comparison, without assuming an overall winner."""
import argparse, json, pathlib

def compare(directory, output):
    paths=list(pathlib.Path(directory).rglob('*-benchmark.json'))
    results={json.loads(path.read_text())['implementation']:json.loads(path.read_text()) for path in paths}
    assert set(results)=={'python-qt','swiftui-cpp'}, 'Both benchmark artifacts are required'
    python=results['python-qt']; native=results['swiftui-cpp']
    assert python['fixture_sha256']==native['fixture_sha256'], 'Fixture mismatch'
    assert python['workload']==native['workload'], 'Workload mismatch'
    assert python['trials'][0]['fixture_first_quote']==native['trials'][0]['fixture_first_quote'], 'App fixture loading mismatch'
    comparable=all(python[key]==native[key] for key in ('architecture','os','hardware'))
    rows=[('应用包体积，含 OpenD (MiB)',python['bundle_disk_mib'],native['bundle_disk_mib'])]
    metrics=[('启动到首张界面快照 (秒)','startup_to_first_snapshot_seconds'),
        ('空闲 CPU (%)','idle_cpu_percent'),('更新 CPU (%)','replay_cpu_percent'),
        ('空闲 RSS (MiB)','idle_rss_mib_median'),('更新 RSS (MiB)','replay_rss_mib_median'),
        ('更新与离屏截图 p50 (ms)','render_ms_p50'),('更新与离屏截图 p95 (ms)','render_ms_p95'),
        ('每轮超过 50ms 的更新数','over_50ms_count')]
    rows.extend((label,python['summary'][key],native['summary'][key]) for label,key in metrics)
    text='# macOS 客户端性能对比\n\n'
    text+='三轮测量取中位数；同一合成行情、13 只股票、180 根 K 线、1500×900 像素、每秒 20 次更新，每轮空闲 5 秒并回放 120 次更新。\n\n'
    text+='| 指标（越低越好） | Python + Qt | SwiftUI + C++ SDK |\n| --- | ---: | ---: |\n'
    text+='\n'.join(f'| {label} | {a:.3f} | {b:.3f} |' for label,a,b in rows)+'\n\n'
    text+='硬件与系统信息一致。两份结果仍来自不同 runner VM，存在调度与宿主机噪声。\n\n' if comparable else '**两台 runner 的硬件或系统信息不同，不能直接据此排名；请在同一台 Mac 上串行复测。**\n\n'
    text+='包体积包含官方 OpenD；运行测量只覆盖客户端进程，未计入 OpenD 或共享更新目录。CPU 100% 代表占满一个核心。启动时间包含 SDK 加载，采样精度约 50ms。RSS 为常驻内存，每 250ms 采样。\n\n'
    text+='测量的是 SDK 已加载、未连接 OpenD 的离屏界面更新与截图；不是屏幕 FPS、真实行情延迟、网络性能或交易性能。两版使用不同 UI 框架，因此结果比较整套客户端方案，不能单独归因于 Python/C++ 语言。首轮及后续轮次的缓存状态可能不同，原始逐轮数据一并保存。\n\n'
    text+='公开 artifact 使用 ad-hoc 签名；尚未完成真实 OpenD 账号验收，当前不能完整替代原版 moomoo。\n'
    output=pathlib.Path(output); output.parent.mkdir(parents=True,exist_ok=True); output.write_text(text)
    output.with_suffix('.json').write_text(json.dumps(dict(hardware_matches=comparable,results=results),indent=2))
    print(text)
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('directory');parser.add_argument('output');args=parser.parse_args();compare(args.directory,args.output)
