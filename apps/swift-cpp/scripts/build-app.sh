#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
./scripts/build-sdk.sh
swift build -c release
BIN_DIR="$(swift build -c release --show-bin-path)"
APP_DIR="$PWD/dist/MooSwiftCpp.app"
rm -rf "$APP_DIR"
mkdir -p "$APP_DIR/Contents/MacOS" "$APP_DIR/Contents/Frameworks"
cp "$BIN_DIR/MooSwiftCpp" "$APP_DIR/Contents/MacOS/MooSwiftCpp"
python3 - "$APP_DIR" <<'PY'
import plistlib,sys,pathlib
path=pathlib.Path(sys.argv[1])/'Contents/Info.plist'
path.write_bytes(plistlib.dumps(dict(CFBundleName='MooSwiftCpp',CFBundleDisplayName='MooSwift C++',
 CFBundleIdentifier='local.charlie.mooswiftcpp',CFBundleExecutable='MooSwiftCpp',CFBundlePackageType='APPL',
 CFBundleShortVersionString='0.1.0',CFBundleVersion='1',LSMinimumSystemVersion='14.0',NSHighResolutionCapable=True)))
PY
for LIB in libprotobuf.32.dylib libssl.3.dylib libcrypto.3.dylib; do
  cp -L "thirdlib/lib/$LIB" "$APP_DIR/Contents/Frameworks/$LIB"
  install_name_tool -id "@rpath/$LIB" "$APP_DIR/Contents/Frameworks/$LIB"
done
python3 - "$APP_DIR" <<'PY'
import pathlib,sys,subprocess
app=pathlib.Path(sys.argv[1]); libraries={'libprotobuf.32.dylib','libssl.3.dylib','libcrypto.3.dylib'}
files=[app/'Contents/MacOS/MooSwiftCpp',*(app/'Contents/Frameworks').iterdir()]
for file in files:
 output=subprocess.check_output(['otool','-L',str(file)],text=True)
 for line in output.splitlines()[1:]:
  old=line.strip().split(' (',1)[0]; name=pathlib.Path(old).name
  if name in libraries:
   subprocess.check_call(['install_name_tool','-change',old,'@rpath/'+name,str(file)])
subprocess.check_call(['install_name_tool','-add_rpath','@executable_path/../Frameworks',str(files[0])])
PY
mkdir -p "$APP_DIR/Contents/Resources/THIRD_PARTY_LICENSES"
tar -xOf vendor/MMAPI4CPP_10.11.7108/ThirdLibSrc/protobuf-3.21.5.tar.gz protobuf-3.21.5/LICENSE > "$APP_DIR/Contents/Resources/THIRD_PARTY_LICENSES/protobuf-LICENSE"
tar -xOf vendor/MMAPI4CPP_10.11.7108/ThirdLibSrc/openssl-3.0.17.tar.gz openssl-3.0.17/LICENSE.txt > "$APP_DIR/Contents/Resources/THIRD_PARTY_LICENSES/openssl-LICENSE.txt"
for LIB in "$APP_DIR"/Contents/Frameworks/*.dylib; do codesign --force --sign - "$LIB"; done
codesign --force --sign - "$APP_DIR"
codesign --verify --deep --strict "$APP_DIR"
ditto -c -k --sequesterRsrc --keepParent "$APP_DIR" "dist/MooSwiftCpp-macos-$(uname -m).zip"
du -sh "$APP_DIR"
