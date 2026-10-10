#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
swift build -c release
BIN_DIR="$(swift build -c release --show-bin-path)"
APP_DIR="$PWD/dist/MooSwift.app"
mkdir -p "$APP_DIR/Contents/MacOS"
cp "$BIN_DIR/MooSwift" "$APP_DIR/Contents/MacOS/MooSwift"
cat > "$APP_DIR/Contents/Info.plist" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>CFBundleName</key><string>MooSwift</string>
<key>CFBundleDisplayName</key><string>MooSwift</string>
<key>CFBundleIdentifier</key><string>local.charlie.mooswift</string>
<key>CFBundleExecutable</key><string>MooSwift</string>
<key>CFBundlePackageType</key><string>APPL</string>
<key>CFBundleShortVersionString</key><string>0.1.0</string>
<key>CFBundleVersion</key><string>1</string>
<key>LSMinimumSystemVersion</key><string>14.0</string>
<key>NSHighResolutionCapable</key><true/>
</dict></plist>
PLIST
codesign --force --sign - "$APP_DIR"
du -sh "$APP_DIR"
