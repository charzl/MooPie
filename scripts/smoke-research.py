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
    for count in (5, 10, 20):
        subprocess.run([*command, '--top', str(count)], check=True, timeout=60)
        result = json.loads(output.read_text(encoding='utf-8'))
        report = result['report']
        assert len(report['recommendations']) == min(count, len(dataset['contracts']))
        assert [r['code'] for r in report['recommendations']] == report['ranked_codes'][:count]
        assert report['configuration']['scoring']['parameters']['return_weight'] == .3
        assert len(report['best_recommendation']['scoring']['components']) == 5
        assert report['best_recommendation']['scoring']['missing_components'] == ['earnings']
        assert all(0 <= r['risk_score'] <= 100 for r in report['recommendations'])
        assert result['input_dataset'] == dataset
    bounds = {'min-cost': 8500, 'max-cost': 9000, 'min-daily-return': .01,
              'max-risk': 90, 'expiry-before': '2026-11-21'}
    config.write_text(json.dumps(dict(filters={key: dict(enabled=True, threshold=value) for key, value in bounds.items()},
                                     sort_order=[['cash_collateral', 'asc']])), encoding='utf-8')
    subprocess.run([*command, '--top', '10'], check=True, timeout=60)
    report = json.loads(output.read_text(encoding='utf-8'))['report']
    assert report['qualified_count'] == 9 and len(report['recommendations']) == 9
    for choice in report['recommendations']:
        assert 8500 < choice['cash_collateral'] < 9000
        assert choice['daily_gross_return_pct'] > .01 and choice['risk_score'] < 90
        assert choice['expiration'] < '2026-11-21'
print('Frozen combined filters, Top 5/10/20 scoring, sorting and offline data reuse passed.')
