"""Copy OpenD metadata for the Python manager, optionally with a signed gateway."""
import hashlib,json,pathlib,plistlib,shutil,subprocess,sys,tarfile,urllib.request,tempfile
ROOT=pathlib.Path(__file__).resolve().parents[1]
META=json.loads((ROOT/'runtime/opend.json').read_text())
REQ='identifier "com.moomoo.opend" and anchor apple generic and certificate leaf[subject.OU] = "6HE4ZULJ45"'
def run(*args): return subprocess.check_output(args,text=True)
def prepare():
    cache=ROOT/'artifacts/opend'; cache.mkdir(parents=True,exist_ok=True)
    archive=cache/f"moomoo_OpenD_{META['version']}_Mac.tar.gz"
    if not archive.exists():
        part=archive.with_suffix('.part')
        try:
            with urllib.request.urlopen(META['url'],timeout=600) as src,part.open('wb') as dst: shutil.copyfileobj(src,dst)
            part.replace(archive)
        finally: part.unlink(missing_ok=True)
    digestor=hashlib.sha256()
    with archive.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''): digestor.update(block)
    digest=digestor.hexdigest()
    if digest!=META['sha256']: raise RuntimeError('Official archive SHA-256 mismatch; remove corrupt cached archive and retry')
    app=cache/f"pristine-{META['version']}/moomoo_OpenD.app"
    if not app.exists():
        with tempfile.TemporaryDirectory(dir=cache) as work:
            stage=pathlib.Path(work); version=META['version']
            entry=f'moomoo_OpenD_{version}_Mac/moomoo_OpenD-GUI_{version}_Mac/moomoo_OpenD-GUI_{version}_Mac.dmg'
            run('tar','-xzf',str(archive),'-C',str(stage),entry)
            mount=stage/'mount'; mount.mkdir()
            run('hdiutil','attach','-readonly','-nobrowse','-mountpoint',str(mount),str(stage/entry))
            try:
                source=mount/'moomoo_OpenD.app'
                run('codesign','--verify','--deep','--strict','-R','='+REQ,str(source))
                app.parent.mkdir(exist_ok=True)
                run('ditto',str(source),str(app))
            finally: run('hdiutil','detach',str(mount))
    run('codesign','--verify','--deep','--strict','-R','='+REQ,str(app))
    with (app/'Contents/Info.plist').open('rb') as f: info=plistlib.load(f)
    if info['CFBundleShortVersionString']!=META['version']: raise RuntimeError('OpenD version mismatch')
    return app
def main():
    updater_only = '--updater-only' in sys.argv
    app=None if updater_only else prepare()
    arguments=[arg for arg in sys.argv[1:] if arg != '--updater-only']
    if not arguments: return
    dest=pathlib.Path(arguments[0])/'Contents/Resources/OpenD'
    dest.mkdir(parents=True,exist_ok=True)
    if updater_only:
        if (dest/'moomoo_OpenD.app').exists(): shutil.rmtree(dest/'moomoo_OpenD.app')
    else: run('ditto',str(app),str(dest/'moomoo_OpenD.app'))
    (dest/'OpenDManager').unlink(missing_ok=True)  # Remove a stale helper when rebuilding an existing app.
    shutil.copy2(ROOT/'runtime/opend.json',dest/'opend.json')
    print('Copied OpenD metadata for the Python manager; official OpenD is installed separately' if updater_only else f"Embedded official signed OpenD {META['version']}; signature retained")
if __name__=='__main__': main()
