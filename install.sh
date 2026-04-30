#!/usr/bin/env bash
# SimpleLog — one-liner installer
# Usage:  curl -sSL https://raw.githubusercontent.com/simplelogdev/simplelog/master/install.sh | bash
set -euo pipefail

REPO="simplelogdev/simplelog"
API_URL="https://api.github.com/repos/${REPO}/releases/latest"

# ── Colors ────────────────────────────────────────────────────────────────────
if [ -t 1 ]; then
    RED='\033[0;31m'; GREEN='\033[0;32m'; BLUE='\033[0;34m'
    BOLD='\033[1m'; NC='\033[0m'
else
    RED=''; GREEN=''; BLUE=''; BOLD=''; NC=''
fi

err()  { echo -e "${RED}✗ $*${NC}" >&2; exit 1; }
info() { echo -e "${BLUE}→ $*${NC}"; }
ok()   { echo -e "${GREEN}✓ $*${NC}"; }
title(){ echo -e "${BOLD}$*${NC}"; }

# ── Detect platform ───────────────────────────────────────────────────────────
OS="$(uname -s)"
ARCH="$(uname -m)"

title ""
title "  SimpleLog installer"
title ""

if [ "$OS" = "Darwin" ]; then
    PLATFORM="macOS"
    ASSET_PATTERN="SimpleLog-macOS.dmg"
elif [ "$OS" = "Linux" ]; then
    PLATFORM="Linux"
    if command -v dpkg &>/dev/null && [ -f /etc/debian_version ]; then
        ASSET_PATTERN="simplelog_amd64.deb"
        INSTALL_METHOD="deb"
    else
        ASSET_PATTERN="simplelog-${ARCH}.AppImage"
        INSTALL_METHOD="appimage"
    fi
else
    err "Unsupported OS: $OS. Please download manually from https://github.com/${REPO}/releases"
fi

info "Detected: $OS / $ARCH"

# ── Fetch latest release ──────────────────────────────────────────────────────
info "Fetching latest release from GitHub…"

if command -v curl &>/dev/null; then
    RELEASE_JSON="$(curl -sf "$API_URL")"
elif command -v wget &>/dev/null; then
    RELEASE_JSON="$(wget -qO- "$API_URL")"
else
    err "curl or wget is required"
fi

DOWNLOAD_URL="$(echo "$RELEASE_JSON" \
    | grep '"browser_download_url"' \
    | grep "$ASSET_PATTERN" \
    | head -1 \
    | sed 's/.*"browser_download_url": *"\([^"]*\)".*/\1/')"

VERSION="$(echo "$RELEASE_JSON" \
    | grep '"tag_name"' \
    | head -1 \
    | sed 's/.*"tag_name": *"\([^"]*\)".*/\1/')"

[ -z "$DOWNLOAD_URL" ] && \
    err "No $ASSET_PATTERN found in release $VERSION. Check https://github.com/${REPO}/releases"

FILENAME="$(basename "$DOWNLOAD_URL")"
info "Version : $VERSION"
info "Asset   : $FILENAME"

# ── Download ──────────────────────────────────────────────────────────────────
TMP_FILE="/tmp/${FILENAME}"
info "Downloading…"

if command -v curl &>/dev/null; then
    curl -L --progress-bar -o "$TMP_FILE" "$DOWNLOAD_URL"
else
    wget -q --show-progress -O "$TMP_FILE" "$DOWNLOAD_URL"
fi

# ── Install ───────────────────────────────────────────────────────────────────
if [ "$PLATFORM" = "macOS" ]; then
    info "Mounting disk image…"
    hdiutil attach "$TMP_FILE" -mountpoint /Volumes/SimpleLog -quiet

    info "Copying SimpleLog.app to /Applications…"
    # Remove old version if present
    rm -rf /Applications/SimpleLog.app
    cp -r /Volumes/SimpleLog/SimpleLog.app /Applications/

    hdiutil detach /Volumes/SimpleLog -quiet
    rm -f "$TMP_FILE"

    ok "Installed: /Applications/SimpleLog.app"
    echo ""
    echo "  Open Launchpad or run:  open /Applications/SimpleLog.app"

elif [ "$INSTALL_METHOD" = "deb" ]; then
    info "Installing .deb package (requires sudo)…"
    sudo dpkg -i "$TMP_FILE"
    rm -f "$TMP_FILE"

    ok "Installed: /usr/bin/simplelog"
    echo ""
    echo "  Run: simplelog"

elif [ "$INSTALL_METHOD" = "appimage" ]; then
    INSTALL_DIR="${HOME}/.local/bin"
    mkdir -p "$INSTALL_DIR"

    DEST="${INSTALL_DIR}/simplelog"
    mv "$TMP_FILE" "$DEST"
    chmod +x "$DEST"

    ok "Installed: $DEST"
    echo ""

    # PATH check
    if ! echo "$PATH" | grep -qF "$INSTALL_DIR"; then
        echo -e "${BLUE}  Add to PATH — append to ~/.bashrc or ~/.zshrc:${NC}"
        echo "    export PATH=\"\$HOME/.local/bin:\$PATH\""
        echo ""
    fi
    echo "  Run: simplelog"
fi

echo ""
ok "SimpleLog $VERSION installed successfully."
