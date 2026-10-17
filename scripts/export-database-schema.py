"""Generate/check the readable schema from the packaged migration definitions."""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'apps/python'))
from moopython.database import ROOT as DATABASE_ROOT, SCHEMA_VERSION, schema_sql

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--check', action='store_true', help='Fail if schema.sql needs regeneration')
args = parser.parse_args()
target = DATABASE_ROOT / 'schema.sql'
generated = schema_sql()
if args.check:
    if not target.is_file() or target.read_text(encoding='utf-8') != generated:
        parser.exit(1, 'schema.sql is out of date; run scripts/export-database-schema.py\n')
    print(f'Database schema matches migrations (v{SCHEMA_VERSION}).')
else:
    target.write_text(generated, encoding='utf-8')
    print(target.relative_to(ROOT))
