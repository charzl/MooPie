import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


@unittest.skipIf(os.name == 'nt', 'Bash launcher checks; Windows has native PowerShell checks')
class SetupToolsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='moomoo install ')
        self.root = Path(self.temp.name)
        for name in ('setup.sh', 'moomoo'): shutil.copy2(ROOT/name, self.root/name)
        self.python = self.root/'apps/python/.venv/bin/python'
        self.python.parent.mkdir(parents=True)
        self.python.write_text('#!/usr/bin/env bash\nprintf "%s\\n" "$@"\n')
        self.python.chmod(0o755)
        tools = self.root/'tools'; tools.mkdir()
        self.log = self.root/'uv.jsonl'
        uv = tools/'uv'
        uv.write_text('#!'+sys.executable+'\nimport json,os,sys\nwith open(os.environ["MOOMOO_TEST_LOG"],"a") as f: f.write(json.dumps(sys.argv[1:])+"\\n")\n')
        uv.chmod(0o755)
        self.env = dict(os.environ, PATH=str(tools)+os.pathsep+os.environ['PATH'], MOOMOO_TEST_LOG=str(self.log))

    def tearDown(self): self.temp.cleanup()

    def test_launcher_works_from_another_directory_with_spaces(self):
        result = subprocess.run([str(self.root/'moomoo'), 'collect', 'AVGO', '--output', 'my data/input.json'],
                                cwd='/', env=self.env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.splitlines(), ['-m','moopython.market_data_cli','AVGO','--output','my data/input.json'])
        self.assertFalse(self.log.exists())

    def test_database_cleanup_dispatch_preserves_arguments(self):
        result = subprocess.run([str(self.root/'moomoo'), 'db', 'cleanup', '--older-than-days', '180', '--dry-run'],
                                cwd='/', env=self.env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.splitlines(), ['-m', 'moopython.database_cli', 'cleanup', '--older-than-days', '180', '--dry-run'])

    def test_watchlist_dispatch_preserves_json_path_with_spaces(self):
        result = subprocess.run([str(self.root/'moomoo'), 'watchlist', 'my lists/watchlist.json', '--check-only'],
                                cwd='/', env=self.env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.splitlines(), ['-m', 'moopython.watchlist_cli', 'my lists/watchlist.json', '--check-only'])

    def test_reinstall_reuses_environment_and_desktop_is_explicit(self):
        for args in ([], ['--desktop']):
            result = subprocess.run([str(self.root/'setup.sh'),*args],cwd='/',env=self.env,capture_output=True,text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
        calls = [json.loads(line) for line in self.log.read_text().splitlines()]
        self.assertTrue(all('venv' not in call for call in calls))
        project_installs = [call for call in calls if '-e' in call]
        self.assertEqual(len(project_installs), 2)
        self.assertTrue(project_installs[0][-1].endswith('apps/python[mcp]'))
        self.assertTrue(project_installs[1][-1].endswith('apps/python[mcp,desktop]'))

    def test_wrong_existing_python_is_preserved_without_install(self):
        self.python.write_text('#!/usr/bin/env bash\nexit 1\n')
        original = self.python.read_bytes()
        result = subprocess.run([str(self.root/'setup.sh')],env=self.env,capture_output=True,text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('已保留', result.stderr)
        self.assertEqual(self.python.read_bytes(), original)
        self.assertFalse(self.log.exists())


if __name__ == '__main__': unittest.main()
