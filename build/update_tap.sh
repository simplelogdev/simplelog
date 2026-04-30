#!/usr/bin/env bash
# build/update_tap.sh — Update the Homebrew cask after a release
# Usage:  ./build/update_tap.sh <version>   e.g.  ./build/update_tap.sh 2.3.0
# Env:    GH_PAT   — GitHub token with write access to simplelogdev/homebrew-tap
set -euo pipefail

VERSION=${1:?Usage: $0 <version>  e.g. $0 2.3.0}
OWNER="simplelogdev"
REPO="simplelog"
TAP_REPO="homebrew-tap"
DMG_URL="https://github.com/${OWNER}/${REPO}/releases/download/v${VERSION}/SimpleLog-macOS.dmg"

log() { echo "▶ $*"; }
ok()  { echo "✓ $*"; }

log "Computing sha256 for v${VERSION}…"
if command -v sha256sum &>/dev/null; then
    SHA256=$(curl -fsSL "$DMG_URL" | sha256sum | awk '{print $1}')
else
    SHA256=$(curl -fsSL "$DMG_URL" | shasum -a 256 | awk '{print $1}')
fi
ok "sha256: ${SHA256}"

TMPDIR=$(mktemp -d)
trap 'rm -rf "$TMPDIR"' EXIT

log "Cloning tap…"
if [[ -n "${GH_PAT:-}" ]]; then
    git clone --quiet "https://x-access-token:${GH_PAT}@github.com/${OWNER}/${TAP_REPO}.git" "$TMPDIR"
else
    git clone --quiet "https://github.com/${OWNER}/${TAP_REPO}.git" "$TMPDIR"
fi

CASK="$TMPDIR/Casks/simplelog.rb"

sed -i.bak "s|version \".*\"|version \"${VERSION}\"|" "$CASK"
sed -i.bak "s|sha256 .*|sha256 \"${SHA256}\"|"        "$CASK"
rm -f "${CASK}.bak"

git -C "$TMPDIR" config user.name  "GitHub Actions"
git -C "$TMPDIR" config user.email "actions@github.com"
git -C "$TMPDIR" add Casks/simplelog.rb
git -C "$TMPDIR" commit -m "chore: update SimpleLog cask to v${VERSION}"
git -C "$TMPDIR" push origin master

ok "Tap updated → v${VERSION}"
