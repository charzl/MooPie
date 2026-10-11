#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ ! -f build-sdk/libMMAPI.a ]]; then ./scripts/build-sdk.sh; fi
swift build -c release
BIN_DIR="$(swift build -c release --show-bin-path)"
APP_DIR="$PWD/dist/MooSwiftCpp.app"
rm -rf "$APP_DIR"
mkdir -p "$APP_DIR/Contents/MacOS" "$APP_DIR/Contents/Frameworks" "$APP_DIR/Contents/Resources"
cp ../../assets/AppIcon.icns "$APP_DIR/Contents/Resources/AppIcon.icns"
cp ../../fixtures/market.json "$APP_DIR/Contents/Resources/market.json"
cp "$BIN_DIR/MooSwiftCpp" "$APP_DIR/Contents/MacOS/MooSwiftCpp"
python3 - "$APP_DIR" <<'PY'
import plistlib,sys,pathlib
path=pathlib.Path(sys.argv[1])/'Contents/Info.plist'
path.write_bytes(plistlib.dumps(dict(CFBundleName='MooSwiftCpp',CFBundleDisplayName='MooSwift C++',
 CFBundleIconFile='AppIcon.icns',CFBundleIdentifier='local.charlie.mooswiftcpp',CFBundleExecutable='MooSwiftCpp',CFBundlePackageType='APPL',
 CFBundleShortVersionString='0.1.0',CFBundleVersion='1',LSMinimumSystemVersion='14.0',NSHighResolutionCapable=True)))
PY
for COMPONENT in protobuf ssl crypto; do
  SOURCE="thirdlib/lib/lib${COMPONENT}.dylib"
  LIB=$(otool -D "$SOURCE" | tail -1 | xargs basename)
  cp -L "$SOURCE" "$APP_DIR/Contents/Frameworks/$LIB"
  install_name_tool -id "@rpath/$LIB" "$APP_DIR/Contents/Frameworks/$LIB"
done
python3 - "$APP_DIR" <<'PY'
import pathlib,sys,subprocess
app=pathlib.Path(sys.argv[1]); libraries={p.name for p in (app/'Contents/Frameworks').glob('*.dylib')}
files=[app/'Contents/MacOS/MooSwiftCpp',*(app/'Contents/Frameworks').iterdir()]
for file in files:
 output=subprocess.check_output(['otool','-L',str(file)],text=True)
 for line in output.splitlines()[1:]:
  old=line.strip().split(' (',1)[0]; name=pathlib.Path(old).name
  if name in libraries:
   subprocess.check_call(['install_name_tool','-change',old,'@rpath/'+name,str(file)])
# Remove build-machine search paths so smoke tests exercise bundled libraries.
for file in files:
 lines=subprocess.check_output(['otool','-l',str(file)],text=True).splitlines()
 for index,line in enumerate(lines):
  if line.strip()=='cmd LC_RPATH':
   rpath=lines[index+2].strip().split('path ',1)[1].split(' (offset',1)[0]
   if rpath.startswith('/') and rpath!='/usr/lib/swift':
    subprocess.check_call(['install_name_tool','-delete_rpath',rpath,str(file)])
subprocess.check_call(['install_name_tool','-add_rpath','@executable_path/../Frameworks',str(files[0])])
PY
mkdir -p "$APP_DIR/Contents/Resources/THIRD_PARTY_LICENSES"
python3 - "$APP_DIR" <<'PYLICENSE'
import json,pathlib,sys,tarfile
sdk=pathlib.Path(json.loads(pathlib.Path('sdk.json').read_text())['source_dir'])
dest=pathlib.Path(sys.argv[1])/'Contents/Resources/THIRD_PARTY_LICENSES'
for component in ('protobuf','openssl'):
 archives=list((sdk/'ThirdLibSrc').glob(component+'-*.tar.gz')); assert len(archives)==1
 with tarfile.open(archives[0]) as tar:
  names=[n for n in tar.getnames() if pathlib.PurePosixPath(n).name in ('LICENSE','LICENSE.txt') and len(pathlib.PurePosixPath(n).parts)==2]
  assert len(names)==1, 'Expected a root dependency license'
  dest.joinpath(component+'-LICENSE.txt').write_bytes(tar.extractfile(names[0]).read())
PYLICENSE
for LIB in "$APP_DIR"/Contents/Frameworks/*.dylib; do codesign --force --sign - "$LIB"; done
python3 ../../scripts/bundle-opend.py "$APP_DIR"
python3 ../../scripts/stamp-build.py "$APP_DIR"
codesign --force --sign - "$APP_DIR"
codesign --verify --deep --strict "$APP_DIR"
du -sh "$APP_DIR"

python3 ../../scripts/package-dmg.py "$APP_DIR" "dist/MooSwiftCpp-macos-$(uname -m).dmg"
