import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import sysconfig
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


@unittest.skipUnless(os.name == 'nt', 'Requires actual Windows PowerShell and Windows Python')
class WindowsSetupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='moomoo Windows ')
        self.root = Path(self.temp.name)
        for name in ('setup.ps1', 'moomoo.ps1'): shutil.copy2(ROOT/name, self.root/name)
        self.environment = self.root/'apps/python/.venv'
        scripts = self.environment/'Scripts'; scripts.mkdir(parents=True)
        self.python = scripts/'python.exe'
        shutil.copy2(sys.executable, self.python)
        shutil.copy2(Path(sys.prefix)/'pyvenv.cfg', self.environment/'pyvenv.cfg')
        rules = self.root/'modules/put-screener'; rules.mkdir(parents=True)
        for name in ('put_rules.py', 'example.json'): shutil.copy2(ROOT/'modules/put-screener'/name, rules/name)
        # Relocated Python needs the installed dependencies from the real venv.
        self.env = dict(os.environ, PYTHONUTF8='1',
                        PYTHONPATH=os.pathsep.join(filter(None, [sysconfig.get_path('purelib'), os.environ.get('PYTHONPATH')])))

    def tearDown(self): self.temp.cleanup()

    def command(self, script, *arguments):
        return subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(self.root/script),*arguments],
                              cwd=self.root, env=self.env, capture_output=True, text=True, encoding='utf-8', errors='replace')

    def test_real_launcher_preserves_paths_with_spaces(self):
        source=self.root/'input data.json'; output=self.root/'output data.json'
        shutil.copy2(self.root/'modules/put-screener/example.json', source)
        result=self.command('moomoo.ps1','analyze',str(source),'--output',str(output))
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertEqual(json.loads(output.read_text())['qualified_count'],1)

    def test_launcher_propagates_underlying_command_failure(self):
        result=self.command('moomoo.ps1','analyze','missing input.json','--output','unused.json')
        self.assertEqual(result.returncode,2,result.stdout+result.stderr)
        self.assertFalse((self.root/'unused.json').exists())

    def test_incomplete_environment_is_preserved(self):
        self.python.unlink()
        marker=self.environment/'user data.txt'; marker.write_text('keep this')
        result=self.command('setup.ps1')
        self.assertNotEqual(result.returncode,0)
        self.assertEqual(marker.read_text(),'keep this')
        self.assertFalse(self.python.exists())


if __name__ == '__main__': unittest.main()
