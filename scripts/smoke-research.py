"""Exercise explicit filters and offline reuse through a frozen desktop binary."""
import json
import copy
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
binary = str(Path(sys.argv[1]).resolve())
dataset = json.loads((ROOT/'modules/put-screener/example.json').read_text())
dataset['contracts'][0]['earnings'] = None
with tempfile.TemporaryDirectory(prefix='moomoo frozen research ') as directory:
    root = Path(directory); source = root/'input data.json'; config = root/'filters.json'; output = root/'result.json'
    source.write_text(json.dumps(dataset), encoding='utf-8')
    config.write_text(json.dumps(dict(filters={'max-delta': dict(threshold=.1)})), encoding='utf-8')
    command = [binary, 'research', 'put', 'TEST', '--input', str(source), '--config', str(config),
               '--port', '1', '--output', str(output)]
    subprocess.run(command, check=True, timeout=60)
    assert json.loads(output.read_text(encoding='utf-8'))['report']['qualified_count'] == 0
    config.write_text(json.dumps(dict(filters={rid: dict(enabled=False) for rid in ('earnings-checked', 'earnings-buffer')},
                                     sort_order=[['cash_collateral', 'asc']])), encoding='utf-8')
    subprocess.run(command, check=True, timeout=60)
    result = json.loads(output.read_text(encoding='utf-8'))
    assert result['report']['qualified_count'] == 1
    assert result['report']['best_recommendation']['code'] == dataset['contracts'][0]['code']
    assert result['report']['best_recommendation']['daily_gross_return_pct'] > 0
    assert result['report']['ranked'][0]['warnings']
    assert result['report']['sort_order'] == [['cash_collateral', 'asc']]
    assert result['input_dataset'] == dataset and result['collected_at'] == dataset['collected_at']
    for index in range(1, 14):
        row = copy.deepcopy(dataset['contracts'][0])
        row.update(code=f'US.TEST-SYNTHETIC-{index}', strike=90-index*.5, snapshot_strike=90-index*.5,
                   bid=1.5+index*.01, ask=1.6+index*.01, delta=-.2+index*.005)
        dataset['contracts'].append(row)
    source.write_text(json.dumps(dataset), encoding='utf-8')
    config.write_text(json.dumps(dict(sort_order=[['composite_score', 'desc']],
        scoring=dict(parameters=dict(return_weight=.3, stress_drop_pct=30)))), encoding='utf-8')
    subprocess.run(command, check=True, timeout=60)
    result = json.loads(output.read_text(encoding='utf-8'))
    report = result['report']
    assert len(report['recommendations']) == 10
    assert [r['code'] for r in report['recommendations']] == report['ranked_codes'][:10]
    assert report['configuration']['scoring']['parameters']['return_weight'] == .3
    assert len(report['best_recommendation']['scoring']['components']) == 5
    assert report['best_recommendation']['scoring']['missing_components'] == ['earnings']
    assert all(0 <= r['risk_score'] <= 100 for r in report['recommendations'])
print('Frozen filters, Top 10 scoring, sorting and offline data reuse passed.')
