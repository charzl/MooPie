"""Build artifact metadata; this is not a runtime performance benchmark."""
import json,os,pathlib,platform,subprocess,sys
app=pathlib.Path(sys.argv[1]).resolve()
gateway=app/'Contents/Resources/OpenD/moomoo_OpenD.app'
print(json.dumps(dict(app=app.name,architecture=platform.machine(),os=platform.platform(),
 commit=os.environ.get('GITHUB_SHA','local'),
 disk_kib=int(subprocess.check_output(['du','-sk',str(app)],text=True).split()[0]),
 sdk_version=json.loads((app/'Contents/Resources/build-manifest.json').read_text())['sdk']['version'],
 opend_version=json.loads((app/'Contents/Resources/OpenD/opend.json').read_text())['version'],
 opend_bundled=gateway.exists(),
 opend_disk_kib=int(subprocess.check_output(['du','-sk',str(gateway)],text=True).split()[0]) if gateway.exists() else 0,
 note='OpenD is independently installed for MooPie; excludes the shared user runtime copy, downloads, caches and runtime CPU/memory.'),indent=2))
