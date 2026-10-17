"""Include a snapshot of the canonical standalone rules in wheel/sdist builds."""
from pathlib import Path
import shutil
from setuptools import setup
from setuptools.command.build_py import build_py
from setuptools.command.sdist import sdist

ROOT = Path(__file__).resolve().parent
RULES = ROOT.parent.parent / 'modules/put-screener/put_rules.py'


class BuildPy(build_py):
    def run(self):
        super().run()
        if RULES.is_file():
            shutil.copy2(RULES, Path(self.build_lib) / 'moopython/_bundled_put_rules.py')


class Sdist(sdist):
    def make_release_tree(self, base_dir, files):
        super().make_release_tree(base_dir, files)
        shutil.copy2(RULES if RULES.is_file() else ROOT/'moopython/_bundled_put_rules.py',
                     Path(base_dir)/'moopython/_bundled_put_rules.py')


setup(cmdclass={'build_py': BuildPy, 'sdist': Sdist})
