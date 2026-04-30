#!/usr/bin/env bash
# build/build_macos.sh — Build SimpleLog for macOS
# Produces:
#   dist/SimpleLog-macOS.dmg   (drag-and-drop installer)
set -euo pipefail

VERSION="${VERSION:-1.0.0}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

log()  { echo "▶ $*"; }
ok()   { echo "✓ $*"; }

cd "$REPO_ROOT"

# ── 1. PyInstaller ────────────────────────────────────────────────────────────
log "Installing PyInstaller…"
pip install pyinstaller --quiet

log "Building with PyInstaller…"
pyinstaller simplelog.spec --noconfirm --clean
ok "PyInstaller done → dist/SimpleLog.app"

[ -d "dist/SimpleLog.app" ] || { echo "✗ SimpleLog.app not found — build failed"; exit 1; }

# ── 2. DMG ────────────────────────────────────────────────────────────────────
log "Creating .dmg…"

DMG_STAGING="dist/dmg_staging"
DMG_NAME="dist/SimpleLog-macOS.dmg"

rm -rf "$DMG_STAGING"
mkdir -p "$DMG_STAGING"
cp -r "dist/SimpleLog.app" "$DMG_STAGING/"

# Applications symlink so user can drag-and-drop
ln -sf /Applications "$DMG_STAGING/Applications"

for attempt in 1 2 3; do
    hdiutil create \
        -volname "SimpleLog ${VERSION}" \
        -srcfolder "$DMG_STAGING" \
        -ov \
        -format UDZO \
        -imagekey zlib-level=9 \
        "$DMG_NAME" && break
    echo "hdiutil attempt ${attempt} failed, retrying in 10s…"
    sleep 10
done
[ -f "$DMG_NAME" ] || { echo "✗ hdiutil failed after 3 attempts"; exit 1; }

ok ".dmg → $DMG_NAME"
ls -lh "$DMG_NAME"

echo ""
echo "=== macOS build complete ==="
