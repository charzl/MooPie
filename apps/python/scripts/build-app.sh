#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -m PyInstaller --noconfirm --clean --windowed --name MooPython \
  --icon ../../assets/AppIcon.icns --add-data "../../fixtures/market.json:fixtures" \
  --osx-bundle-identifier local.charlie.moopython --hidden-import moomoo --collect-data moomoo main.py
codesign --force --deep --sign - dist/MooPython.app
codesign --verify --deep --strict dist/MooPython.app
ditto -c -k --sequesterRsrc --keepParent dist/MooPython.app "dist/MooPython-macos-$(uname -m).zip"
du -sh dist/MooPython.app
