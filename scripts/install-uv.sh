#!/usr/bin/env bash
# Install heinoreader into the XDG home with uv.
#
# uv creates an isolated tool environment, so no manual virtualenv is needed.
# The launcher lands in ~/.local/bin (or $UV_TOOL_BIN_DIR); the desktop entry
# and icon are installed alongside it.
#
# Usage:
#   scripts/install-uv.sh              install
#   scripts/install-uv.sh --uninstall  remove everything again

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"

uninstall() {
    echo "Removing the heinoreader uv tool"
    uv tool uninstall heinoreader || true
    rm -f "$DATA_HOME/applications/heinoreader.desktop"
    rm -f "$DATA_HOME/icons/hicolor/scalable/apps/heinoreader.svg"
    if command -v update-desktop-database >/dev/null 2>&1; then
        update-desktop-database "$DATA_HOME/applications" || true
    fi
    echo "Done."
}

case "${1:-install}" in
    --uninstall|uninstall)
        uninstall
        exit 0
        ;;
    install|"")
        ;;
    *)
        echo "Usage: $0 [install|--uninstall]" >&2
        exit 2
        ;;
esac

if ! command -v uv >/dev/null 2>&1; then
    echo "uv not found. Install it from https://docs.astral.sh/uv/" >&2
    exit 1
fi

echo "Installing the heinoreader tool from $ROOT"
uv tool install --force "$ROOT"

echo "Installing desktop entry and icon"
mkdir -p "$DATA_HOME/applications" \
         "$DATA_HOME/icons/hicolor/scalable/apps"
install -m 0644 "$ROOT/heinoreader.desktop" \
    "$DATA_HOME/applications/heinoreader.desktop"
install -m 0644 "$ROOT/src/heinoreader/icon.svg" \
    "$DATA_HOME/icons/hicolor/scalable/apps/heinoreader.svg"

if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$DATA_HOME/applications" || true
fi

echo
echo "Installed:"
echo "  launcher: ${UV_TOOL_BIN_DIR:-$HOME/.local/bin}/heinoreader"
echo "  desktop:  $DATA_HOME/applications/heinoreader.desktop"
echo "  icon:     $DATA_HOME/icons/hicolor/scalable/apps/heinoreader.svg"
