"""Build artifact metadata; this is not a runtime performance benchmark."""
import json,os,pathlib,platform,subprocess,sys
app=pathlib.Path(sys.argv[1]).resolve()
print(json.dumps(dict(app=app.name,architecture=platform.machine(),os=platform.platform(),
 commit=os.environ.get('GITHUB_SHA','local'),
 disk_kib=int(subprocess.check_output(['du','-sk',str(app)],text=True).split()[0]),
 sdk_version=json.loads((app/'Contents/Resources/build-manifest.json').read_text())['sdk']['version'],
 opend_version=json.loads((app/'Contents/Resources/OpenD/opend.json').read_text())['version'],
 opend_disk_kib=int(subprocess.check_output(['du','-sk',str(app/'Contents/Resources/OpenD/moomoo_OpenD.app')],text=True).split()[0]),
 note='Installed bundle includes official OpenD; excludes the shared user runtime copy, downloads, caches and runtime CPU/memory.'),indent=2))
