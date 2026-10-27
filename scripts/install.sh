#!/usr/bin/env bash
# Install heinoreader into the XDG home without uv.
#
# Creates a private virtualenv under $XDG_DATA_HOME/heinoreader/venv, installs the
# package there, links the launcher into ~/.local/bin and installs the desktop
# entry and icon. No root rights are needed.
#
# Usage:
#   scripts/install.sh              install
#   scripts/install.sh --uninstall  remove everything again

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
BIN_HOME="${XDG_BIN_HOME:-$HOME/.local/bin}"
VENV="$DATA_HOME/heinoreader/venv"
PYTHON="${PYTHON:-python3}"

uninstall() {
    echo "Removing heinoreader from $DATA_HOME and $BIN_HOME"
    rm -f "$BIN_HOME/heinoreader"
    rm -rf "$DATA_HOME/heinoreader"
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

if ! command -v "$PYTHON" >/dev/null 2>&1; then
    echo "$PYTHON not found; install Python 3.10 or newer." >&2
    exit 1
fi

echo "Creating virtualenv: $VENV"
"$PYTHON" -m venv "$VENV"
"$VENV/bin/python" -m pip install --upgrade pip >/dev/null
echo "Installing heinoreader from $ROOT"
"$VENV/bin/python" -m pip install "$ROOT"

echo "Linking launcher into $BIN_HOME"
mkdir -p "$BIN_HOME"
ln -sf "$VENV/bin/heinoreader" "$BIN_HOME/heinoreader"

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
echo "  launcher: $BIN_HOME/heinoreader"
echo "  desktop:  $DATA_HOME/applications/heinoreader.desktop"
echo "  icon:     $DATA_HOME/icons/hicolor/scalable/apps/heinoreader.svg"

case ":$PATH:" in
    *":$BIN_HOME:"*) ;;
    *)
        echo
        echo "Note: $BIN_HOME is not on PATH; add it to run 'heinoreader'."
        ;;
esac
