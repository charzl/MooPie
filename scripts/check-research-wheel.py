"""Verify the distributable works outside the checkout, with its frozen rule snapshot."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
wheel = Path(sys.argv[1]).resolve()
with tempfile.TemporaryDirectory(prefix='moomoo wheel ') as directory:
    target = Path(directory)
    with zipfile.ZipFile(wheel) as archive: archive.extractall(target)
    assert (target/'moopython/_bundled_put_rules.py').read_bytes() == (ROOT/'modules/put-screener/put_rules.py').read_bytes()
    program = "from moopython.research import load_rules; import pathlib; r=load_rules(); assert pathlib.Path(r.__file__).name == '_bundled_put_rules.py'; print(r.ENGINE_VERSION)"
    subprocess.run([sys.executable, '-c', program], cwd=target, env=dict(os.environ, PYTHONPATH=directory), check=True)
