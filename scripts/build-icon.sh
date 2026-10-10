#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p artifacts/AppIcon.iconset
swift scripts/render-icon.swift artifacts/AppIcon.png
for SIZE in 16 32 128 256 512; do
 sips -z "$SIZE" "$SIZE" artifacts/AppIcon.png --out "artifacts/AppIcon.iconset/icon_${SIZE}x${SIZE}.png" >/dev/null
 DOUBLE=$((SIZE*2))
 sips -z "$DOUBLE" "$DOUBLE" artifacts/AppIcon.png --out "artifacts/AppIcon.iconset/icon_${SIZE}x${SIZE}@2x.png" >/dev/null
done
iconutil -c icns artifacts/AppIcon.iconset -o assets/AppIcon.icns
