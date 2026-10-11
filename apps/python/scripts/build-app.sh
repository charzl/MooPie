#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -m PyInstaller --noconfirm --clean --windowed --name MooPie \
  --icon ../../assets/AppIcon.icns --add-data "../../fixtures/market.json:fixtures" \
  --osx-bundle-identifier local.charlie.moopython --hidden-import moomoo --collect-data moomoo main.py
codesign --force --deep --sign - dist/MooPie.app
python3 ../../scripts/bundle-opend.py --updater-only dist/MooPie.app
# The installer contains only the client and small OpenD manager.
python3 ../../scripts/stamp-build.py dist/MooPie.app
codesign --force --sign - dist/MooPie.app
codesign --verify --deep --strict dist/MooPie.app
du -sh dist/MooPie.app

python3 ../../scripts/package-dmg.py --external-opend dist/MooPie.app "dist/MooPie-macos-$(uname -m).dmg"
