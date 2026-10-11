"""Materialize resolved dependency versions in an ephemeral CI checkout."""
import argparse,hashlib,json,pathlib,re,subprocess,tempfile,urllib.request
from importlib.util import spec_from_file_location,module_from_spec
ROOT=pathlib.Path(__file__).resolve().parents[1]
spec=spec_from_file_location('resolver',ROOT/'scripts/resolve-upstream.py');resolver=module_from_spec(spec);spec.loader.exec_module(resolver)
def download(item,path):
    resolver.checked_url(item['url'],{'softwaredownload.moomoo.com','files.pythonhosted.org'})
    path.parent.mkdir(parents=True,exist_ok=True)
    if not path.exists():
        with urllib.request.urlopen(item['url'],timeout=600) as src,path.open('wb') as dst:
            while chunk:=src.read(1024*1024):dst.write(chunk)
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    if digest!=item['sha256']:raise RuntimeError('Resolved artifact SHA-256 mismatch')
def apply(manifest,cpp):
    sdk=manifest['sdk'];opend=manifest['opend'];v=sdk['version'];resolver.version(v);resolver.version(opend['version'])
    (ROOT/'runtime/opend.json').write_text(json.dumps(opend,indent=2)+'\n')
    (ROOT/'runtime/sdk.json').write_text(json.dumps(sdk,indent=2)+'\n')
    requirements=ROOT/'apps/python/requirements.txt';original=requirements.read_text()
    source=resolver.checked_url(sdk['python']['url'],{'files.pythonhosted.org'})
    if not re.fullmatch(r'[a-f0-9]{64}',sdk['python']['sha256']):raise ValueError('Invalid Python SDK hash')
    updated=re.sub(r'^moomoo-api.*$',f"moomoo-api @ {source}#sha256={sdk['python']['sha256']}",original,flags=re.M)
    if updated==original and 'moomoo-api' not in original:raise RuntimeError('Missing SDK requirement')
    requirements.write_text(updated)
    if cpp:
        archive=ROOT/'artifacts/upstream'/f'MMAPI4CPP_{v}.7z';download(sdk['cpp'],archive)
        vendor=ROOT/'apps/swift-cpp/vendor';source_dir=vendor/f'MMAPI4CPP_{v}'
        # Always unpack resolved bytes; never silently reuse the vendored old source.
        with tempfile.TemporaryDirectory(dir=vendor) as work:
            entries=subprocess.check_output(['/usr/bin/tar','-tf',str(archive)],text=True).splitlines()
            for name in entries:
                p=pathlib.PurePosixPath(name)
                if p.is_absolute() or '..' in p.parts:raise RuntimeError('Unsafe SDK archive member')
            subprocess.run(['/usr/bin/tar','-xf',str(archive),'-C',work,f'MMAPI4CPP_{v}'],check=True)
            extracted=pathlib.Path(work)/f'MMAPI4CPP_{v}'
            define=(extracted/'include/MMAPI_Define.h').read_text()
            if not re.search(r'#define\s+MMAPI_VERSION\s+"'+re.escape(v)+r'"',define):raise RuntimeError('C++ SDK header version mismatch')
            if not (extracted/'CMakeLists.txt').is_file():raise RuntimeError('Unsupported official SDK layout')
            import shutil
            if source_dir.exists():shutil.rmtree(source_dir)
            shutil.copytree(extracted,source_dir,symlinks=True)
        (ROOT/'apps/swift-cpp/sdk.json').write_text(json.dumps(dict(version=v,source_dir=f'vendor/MMAPI4CPP_{v}'))+'\n')
    print(f"Resolved build: SDK {v}, OpenD {opend['version']}")
def main():
    p=argparse.ArgumentParser();p.add_argument('manifest');p.add_argument('--cpp',action='store_true');a=p.parse_args();apply(json.loads(pathlib.Path(a.manifest).read_text()),a.cpp)
if __name__=='__main__':main()
