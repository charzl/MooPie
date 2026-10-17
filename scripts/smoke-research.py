"""Exercise explicit filters and offline reuse through a frozen desktop binary."""
import json
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
    config.write_text('{}', encoding='utf-8')
    command = [binary, 'research', 'put', 'TEST', '--input', str(source), '--config', str(config),
               '--port', '1', '--output', str(output)]
    subprocess.run(command, check=True, timeout=60)
    assert json.loads(output.read_text(encoding='utf-8'))['report']['qualified_count'] == 0
    config.write_text(json.dumps(dict(filters={rid: dict(enabled=False) for rid in ('earnings-checked', 'earnings-buffer')},
                                     sort_order=[['cash_collateral', 'asc']])), encoding='utf-8')
    subprocess.run(command, check=True, timeout=60)
    result = json.loads(output.read_text(encoding='utf-8'))
    assert result['report']['qualified_count'] == 1
    assert result['report']['ranked'][0]['warnings']
    assert result['report']['sort_order'] == [['cash_collateral', 'asc']]
    assert result['input_dataset'] == dataset and result['collected_at'] == dataset['collected_at']
print('Frozen filters, sorting and offline data reuse passed.')
