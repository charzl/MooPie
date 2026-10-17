"""Build and smoke-test a portable Windows GUI; no OpenD or credentials bundled."""
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    if os.name != 'nt': raise SystemExit('Run this builder on Windows.')
    app = ROOT / 'apps/python'
    subprocess.run([sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean', '--windowed',
                    '--name', 'MooPie', '--hidden-import', 'moomoo', '--collect-data', 'moomoo',
                    '--collect-data', 'tzdata', '--add-data', f'{ROOT / "modules/put-screener/put_rules.py"}:.',
                    '--add-data', f'{ROOT / "fixtures/market.json"}:fixtures', 'main.py'], cwd=app, check=True)
    binary = app/'dist/MooPie/MooPie.exe'
    subprocess.run([str(binary), '--sdk-check'], check=True, timeout=90)
    preview = ROOT/'artifacts/MooPie-windows-preview.png'
    preview.parent.mkdir(exist_ok=True)
    subprocess.run([str(binary), '--render-preview', str(preview)], check=True, timeout=90)
    assert preview.read_bytes().startswith(b'\x89PNG\r\n\x1a\n')
    # Also run the actual frozen analysis path: closed test port must produce
    # structured failure, proving that Qt launch and research subprocess dispatch work.
    result = ROOT/'artifacts/windows-research-error.json'
    process = subprocess.run([str(binary), 'research', 'trend', 'AAPL', '--port', '1', '--output', str(result)], timeout=30)
    import json
    assert process.returncode == 1 and json.loads(result.read_text(encoding='utf-8'))['error']
    shutil.make_archive(str(app/'dist/MooPie-windows-x64'), 'zip', root_dir=app/'dist', base_dir='MooPie')


if __name__ == '__main__': main()
