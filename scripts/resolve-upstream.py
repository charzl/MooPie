"""Resolve the Python SDK/OpenD pair; skip unchanged published builds."""
import argparse,hashlib,json,os,pathlib,re,subprocess,urllib.request
ROOT=pathlib.Path(__file__).resolve().parents[1]
def version(text):
    if not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+',text): raise ValueError('Invalid stable upstream version')
    return tuple(map(int,text.split('.')))
def checked_url(url,hosts):
    from urllib.parse import urlparse
    parsed=urlparse(url)
    if parsed.scheme!='https' or parsed.hostname not in hosts or parsed.username or parsed.password: raise ValueError('Untrusted upstream URL')
    return url
def get_json(url):
    with urllib.request.urlopen(url,timeout=30) as r: return json.load(r)
def latest_opend():
    for host in ('www.moomoo.com','www.futunn.com'):
        r=subprocess.run(['curl','--fail','--silent','--show-error','--proto','=https','--max-time','30','-I',f'https://{host}/download/fetch-lasted-link?name=opend-macos'],capture_output=True,text=True)
        if r.returncode: continue
        for location in re.findall(r'^location:\s*(.+)$',r.stdout,re.I|re.M):
            try:
                url=checked_url(location.strip(),{'softwaredownload.moomoo.com','softwaredownload.futunn.com'})
                match=re.search(r'/(?:moomoo|Futu)_OpenD_([0-9]+\.[0-9]+\.[0-9]+)_Mac\.tar\.gz$',url)
                if match: return match.group(1)
            except ValueError: pass
    raise RuntimeError('Official OpenD latest-version service unavailable')
def digest_url(url):
    digest=hashlib.sha256()
    with urllib.request.urlopen(url,timeout=600) as r:
        for chunk in iter(lambda:r.read(1024*1024),b''): digest.update(chunk)
    return digest.hexdigest()
def tag_for(commit,sdk,opend):
    if not re.fullmatch(r'[a-f0-9]{40}',commit): raise ValueError('Invalid source commit')
    version(sdk);version(opend)
    return f'build-{commit[:12]}-sdk{sdk}-opend{opend}'
def resolve(latest,commit):
    sdk=json.loads((ROOT/'runtime/sdk.json').read_text()); opend=json.loads((ROOT/'runtime/opend.json').read_text())
    if latest:
        sv=get_json('https://pypi.org/pypi/moomoo-api/json')['info']['version'];ov=latest_opend()
        if version(sv)<version(sdk['version']) or version(ov)<version(opend['version']): raise RuntimeError('Upstream version went backwards; refusing downgrade')
        if version(ov)<version(sv): raise RuntimeError('New SDK is ahead of available OpenD; wait for a compatible official release')
        if sv!=sdk['version']:
            release=get_json(f'https://pypi.org/pypi/moomoo-api/{sv}/json')
            files=release['urls']; source=next((f for f in files if f['packagetype']=='sdist' and not f.get('yanked')),None)
            if source is None: raise RuntimeError('No non-yanked official Python SDK source distribution')
            python=dict(url=checked_url(source['url'],{'files.pythonhosted.org'}),sha256=source['digests']['sha256'])
            sdk=dict(version=sv,python=python)
        if ov!=opend['version']:
            opend={**opend,'version':ov,'url':f'https://softwaredownload.moomoo.com/moomoo_OpenD_{ov}_Mac.tar.gz','sha256':None}
    return dict(schema=1,source_commit=commit,sdk=sdk,opend=opend,release_tag=tag_for(commit,sdk['version'],opend['version']))
def fill_hashes(manifest):
    for item in (manifest['sdk']['python'],manifest['opend']):
        checked_url(item['url'],{'softwaredownload.moomoo.com','files.pythonhosted.org'})
        if not item['sha256']: item['sha256']=digest_url(item['url'])
        if not re.fullmatch(r'[a-f0-9]{64}',item['sha256']): raise ValueError('Invalid artifact SHA-256')
def main():
    parser=argparse.ArgumentParser();parser.add_argument('output');parser.add_argument('--latest',action='store_true');parser.add_argument('--skip-published',action='store_true');parser.add_argument('--force',action='store_true');args=parser.parse_args()
    commit=os.environ.get('GITHUB_SHA') or subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    manifest=resolve(args.latest,commit)
    if args.force: manifest['release_tag']+=f"-run{os.environ.get('GITHUB_RUN_ID','local')}"
    build=True
    if args.skip_published:
        check=subprocess.run(['gh','api',f"repos/{os.environ['GITHUB_REPOSITORY']}/releases/tags/{manifest['release_tag']}"],capture_output=True,text=True)
        if check.returncode==0: build=json.loads(check.stdout).get("draft",False)
        elif '404' not in check.stderr: raise RuntimeError('Cannot determine published release status: '+check.stderr)
    if build: fill_hashes(manifest)
    output=pathlib.Path(args.output);output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(manifest,indent=2)+'\n')
    if os.environ.get('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'],'a') as f:
            f.write(f"build={'true' if build else 'false'}\ntag={manifest['release_tag']}\nsdk={manifest['sdk']['version']}\nopend={manifest['opend']['version']}\n")
    print(json.dumps(dict(build=build,tag=manifest['release_tag'],sdk=manifest['sdk']['version'],opend=manifest['opend']['version'])))
if __name__=='__main__':main()
