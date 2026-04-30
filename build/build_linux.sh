#!/usr/bin/env bash
# build/build_linux.sh — Build SimpleLog for Linux
# Produces:
#   dist/simplelog-x86_64.AppImage   (universal, no install needed)
#   dist/simplelog_amd64.deb         (Debian / Ubuntu)
set -euo pipefail

VERSION="${VERSION:-1.0.0}"
DEB_VERSION="${VERSION#v}"   # dpkg rejects leading 'v' (v1.0.0 → 1.0.0)
ARCH="$(uname -m)"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

log()  { echo "▶ $*"; }
ok()   { echo "✓ $*"; }
bail() { echo "✗ $*" >&2; exit 1; }

cd "$REPO_ROOT"

# ── 1. PyInstaller ────────────────────────────────────────────────────────────
log "Installing PyInstaller…"
pip install pyinstaller --quiet

log "Building with PyInstaller…"
pyinstaller simplelog.spec --noconfirm --clean
ok "PyInstaller done → dist/simplelog/"

# ── 2. AppImage ───────────────────────────────────────────────────────────────
log "Creating AppImage…"

APPDIR="dist/SimpleLog.AppDir"
rm -rf "$APPDIR"
mkdir -p "$APPDIR/usr/bin"
cp -r dist/simplelog/* "$APPDIR/usr/bin/"

# AppRun entry point
cat > "$APPDIR/AppRun" <<'APPRUN'
#!/bin/bash
HERE="$(dirname "$(readlink -f "$0")")"
exec "$HERE/usr/bin/simplelog" "$@"
APPRUN
chmod +x "$APPDIR/AppRun"

# .desktop file
cat > "$APPDIR/simplelog.desktop" <<DESKTOP
[Desktop Entry]
Name=SimpleLog
Comment=Multi-source log viewer (CloudWatch, files, stdin)
Exec=simplelog
Icon=simplelog
Type=Application
Categories=Development;Utility;
Terminal=false
DESKTOP

# Generate app icon from SVG
log "Generating app icon…"
python3 packaging/make_icon.py dist/simplelog.png 256
cp dist/simplelog.png "$APPDIR/simplelog.png"

# Download appimagetool
if ! command -v appimagetool &>/dev/null; then
    TOOL="/tmp/appimagetool-${ARCH}.AppImage"
    if [ ! -f "$TOOL" ]; then
        log "Downloading appimagetool…"
        curl -sSL -o "$TOOL" \
            "https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-${ARCH}.AppImage"
        chmod +x "$TOOL"
    fi
    APPIMAGETOOL="$TOOL"
else
    APPIMAGETOOL="appimagetool"
fi

ARCH="$ARCH" "$APPIMAGETOOL" "$APPDIR" "dist/simplelog-${ARCH}.AppImage" 2>&1
ok "AppImage → dist/simplelog-${ARCH}.AppImage"

# ── 3. .deb ───────────────────────────────────────────────────────────────────
log "Creating .deb package…"

DEB_ROOT="dist/deb_build/simplelog_${DEB_VERSION}_amd64"
rm -rf dist/deb_build
mkdir -p "${DEB_ROOT}/DEBIAN"
mkdir -p "${DEB_ROOT}/usr/lib/simplelog"
mkdir -p "${DEB_ROOT}/usr/bin"
mkdir -p "${DEB_ROOT}/usr/share/applications"
mkdir -p "${DEB_ROOT}/usr/share/pixmaps"
mkdir -p "${DEB_ROOT}/usr/share/icons/hicolor/256x256/apps"

cp -r dist/simplelog/* "${DEB_ROOT}/usr/lib/simplelog/"

# App icon — pixmaps (classic) + hicolor (modern icon theme)
cp dist/simplelog.png "${DEB_ROOT}/usr/share/pixmaps/simplelog.png"
cp dist/simplelog.png "${DEB_ROOT}/usr/share/icons/hicolor/256x256/apps/simplelog.png"

# Launcher wrapper so PATH resolves to /usr/bin/simplelog
cat > "${DEB_ROOT}/usr/bin/simplelog" <<'WRAPPER'
#!/bin/bash
exec /usr/lib/simplelog/simplelog "$@"
WRAPPER
chmod +x "${DEB_ROOT}/usr/bin/simplelog"

# .desktop integration
cat > "${DEB_ROOT}/usr/share/applications/simplelog.desktop" <<DESKTOP
[Desktop Entry]
Name=SimpleLog
Comment=Multi-source log viewer (CloudWatch, files, stdin)
Exec=/usr/bin/simplelog
Icon=simplelog
Type=Application
Categories=Development;Utility;
Terminal=false
DESKTOP

# DEBIAN/control
cat > "${DEB_ROOT}/DEBIAN/control" <<CONTROL
Package: simplelog
Version: ${DEB_VERSION}
Section: utils
Priority: optional
Architecture: amd64
Depends: libgl1, libegl1, libxkbcommon0, libxkbcommon-x11-0, libdbus-1-3, libxcb-icccm4, libxcb-image0, libxcb-keysyms1, libxcb-randr0, libxcb-render-util0, libxcb-xinerama0, libxcb-xkb1, libxcb-cursor0
Maintainer: SimpleLog <https://github.com/sindus/simplelog>
Homepage: https://github.com/sindus/simplelog
Description: Multi-source log viewer for CloudWatch, files and stdin
 SimpleLog is a fast, Material Design log viewer that unifies AWS CloudWatch
 streams, local log files, and piped stdin in a single tabbed interface.
 .
 Features: live tailing, split view, syntax highlighting, search.
CONTROL

# DEBIAN/postinst — update desktop DB and icon cache
cat > "${DEB_ROOT}/DEBIAN/postinst" <<'POSTINST'
#!/bin/bash
update-desktop-database /usr/share/applications 2>/dev/null || true
gtk-update-icon-cache -f -t /usr/share/icons/hicolor 2>/dev/null || true
POSTINST
chmod 755 "${DEB_ROOT}/DEBIAN/postinst"

dpkg-deb --build --root-owner-group "${DEB_ROOT}" "dist/simplelog_amd64.deb"
ok ".deb → dist/simplelog_amd64.deb"

echo ""
echo "=== Linux build complete ==="
ls -lh dist/simplelog-*.AppImage dist/simplelog_amd64.deb
