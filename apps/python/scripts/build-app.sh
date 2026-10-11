#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -m PyInstaller --noconfirm --clean --windowed --name MooPython \
  --icon ../../assets/AppIcon.icns --add-data "../../fixtures/market.json:fixtures" \
  --osx-bundle-identifier local.charlie.moopython --hidden-import moomoo --collect-data moomoo main.py
codesign --force --deep --sign - dist/MooPython.app
python3 ../../scripts/bundle-opend.py dist/MooPython.app
# Preserve the nested official publisher signature.
python3 ../../scripts/stamp-build.py dist/MooPython.app
codesign --force --sign - dist/MooPython.app
codesign --verify --deep --strict dist/MooPython.app
du -sh dist/MooPython.app

python3 ../../scripts/package-dmg.py dist/MooPython.app "dist/MooPython-macos-$(uname -m).dmg"
