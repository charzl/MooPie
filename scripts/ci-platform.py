"""Acceptance checks for the documented platform install, without a broker login."""
import importlib.util
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
os.environ['PYTHONPATH'] = str(ROOT / 'apps/python')
os.environ['PYTHONUTF8'] = '1'
assert sys.version_info[:2] == (3, 14)
assert importlib.util.find_spec('PySide6') is None, 'Default tools installation must not require Qt'
launcher = (['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(ROOT/'moomoo.ps1')]
            if os.name == 'nt' else [str(ROOT/'moomoo')])

def run(*args):
    subprocess.run(args, check=True)

for command in ('options', 'collect', 'analyze', 'mcp', 'doctor', 'db', 'watchlist'):
    run(*launcher, command, '--help')
for directory, pattern in [('tests/unit', 'test_setup_*.py'), ('apps/python/tests/unit', 'test_doctor.py'),
                           ('apps/python/tests/unit', 'test_market_collection.py'), ('apps/python/tests/mcp', 'test*.py'),
                           ('apps/python/tests/unit', 'test_market_repository.py'),
                           ('apps/python/tests/unit', 'test_market_store.py'),
                           ('apps/python/tests/unit', 'test_security_directory.py'),
                           ('apps/python/tests/unit', 'test_watchlist*.py'),
                           ('apps/python/tests/unit', 'test_research*.py'),
                           ('modules/put-screener/tests', 'test*.py')]:
    run(sys.executable, '-m', 'unittest', 'discover', '-s', directory, '-p', pattern, '-v')
run(*launcher, 'analyze', 'modules/put-screener/example.json', '--output', 'artifacts/platform-check/report.json')
print('Platform installation, launchers, MCP and offline analysis passed.')
