"""Materialize resolved dependency versions in an ephemeral CI checkout."""
import argparse,json,pathlib,re
from importlib.util import spec_from_file_location,module_from_spec
ROOT=pathlib.Path(__file__).resolve().parents[1]
spec=spec_from_file_location('resolver',ROOT/'scripts/resolve-upstream.py');resolver=module_from_spec(spec);spec.loader.exec_module(resolver)
def apply(manifest):
    sdk=manifest['sdk'];opend=manifest['opend'];v=sdk['version'];resolver.version(v);resolver.version(opend['version'])
    (ROOT/'runtime/opend.json').write_text(json.dumps(opend,indent=2)+'\n')
    (ROOT/'runtime/sdk.json').write_text(json.dumps(sdk,indent=2)+'\n')
    requirements=ROOT/'apps/python/requirements.txt';original=requirements.read_text()
    source=resolver.checked_url(sdk['python']['url'],{'files.pythonhosted.org'})
    if not re.fullmatch(r'[a-f0-9]{64}',sdk['python']['sha256']):raise ValueError('Invalid Python SDK hash')
    updated=re.sub(r'^moomoo-api.*$',f"moomoo-api @ {source}#sha256={sdk['python']['sha256']}",original,flags=re.M)
    if updated==original and 'moomoo-api' not in original:raise RuntimeError('Missing SDK requirement')
    requirements.write_text(updated)
    print(f"Resolved build: SDK {v}, OpenD {opend['version']}")
def main():
    p=argparse.ArgumentParser();p.add_argument('manifest');a=p.parse_args();apply(json.loads(pathlib.Path(a.manifest).read_text()))
if __name__=='__main__':main()
