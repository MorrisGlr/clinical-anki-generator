#!/usr/bin/env bash
# build/build_macos.sh — Build the CAST macOS .app and wrap it in a .dmg
#
# Prerequisites:
#   pip install -e ".[dev]"   (installs pyinstaller)
#
# Usage:
#   bash build/build_macos.sh
#
# Output:
#   dist/CAST.app             — runnable .app bundle
#   dist/CAST-macOS.dmg       — distributable disk image

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "==> Building CAST.app with PyInstaller..."
pyinstaller cast.spec --clean --noconfirm

echo "==> Build complete: dist/CAST.app"
echo "    Size: $(du -sh dist/CAST.app | cut -f1)"

echo "==> Creating dist/CAST-macOS.dmg with hdiutil..."
DMG="dist/CAST-macOS.dmg"
rm -f "$DMG"

hdiutil create \
    -volname "CAST" \
    -srcfolder "dist/CAST.app" \
    -ov \
    -format UDZO \
    "$DMG"

echo ""
echo "==> Done."
echo "    App:  dist/CAST.app"
echo "    DMG:  $DMG ($(du -sh "$DMG" | cut -f1))"
echo ""
echo "    To test locally: open dist/CAST.app"
echo "    On a fresh machine: right-click CAST.app → Open (bypasses Gatekeeper)"
