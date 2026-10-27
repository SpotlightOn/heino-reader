#!/usr/bin/env bash
# Install Heino Reader into the XDG home without uv.
#
# Creates a private virtualenv under $XDG_DATA_HOME/heino-reader/venv, installs the
# package there, links the launcher into ~/.local/bin and installs the desktop
# entry and icon. No root rights are needed.
#
# The default install is the small one: Qt's base modules only
# (pyside6-essentials, ~240 MB installed). QtWebEngine comes with
# pyside6-addons (~440 MB) and is only pulled in with --web.
#
# Usage:
#   scripts/install.sh              install (Qt renderer, no QtWebEngine)
#   scripts/install.sh --web        install with QtWebEngine support
#   scripts/install.sh --uninstall  remove everything again

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
BIN_HOME="${XDG_BIN_HOME:-$HOME/.local/bin}"
VENV="$DATA_HOME/heino-reader/venv"
PYTHON="${PYTHON:-python3}"
ACTION="install"
EXTRA=""

usage() {
    cat >&2 <<'EOF'
Usage: scripts/install.sh [install|--uninstall] [--web]

  --web        also install QtWebEngine (pyside6-addons, ~440 MB) for the
               optional Web Engine preview
  --uninstall  remove the virtualenv, launcher, desktop entry and icon
EOF
}

for arg in "$@"; do
    case "$arg" in
        ""|install) ;;
        --web|web) EXTRA="[web]" ;;
        --uninstall|uninstall) ACTION="uninstall" ;;
        -h|--help) usage; exit 0 ;;
        *) echo "Unknown argument: $arg" >&2; usage; exit 2 ;;
    esac
done

uninstall() {
    echo "Removing Heino Reader from $DATA_HOME and $BIN_HOME"
    rm -f "$BIN_HOME/heino-reader"
    rm -rf "$DATA_HOME/heino-reader"
    rm -f "$DATA_HOME/applications/heino-reader.desktop"
    rm -f "$DATA_HOME/icons/hicolor/scalable/apps/heino-reader.svg"
    if command -v update-desktop-database >/dev/null 2>&1; then
        update-desktop-database "$DATA_HOME/applications" || true
    fi
    echo "Done."
}

if [ "$ACTION" = "uninstall" ]; then
    uninstall
    exit 0
fi

if ! command -v "$PYTHON" >/dev/null 2>&1; then
    echo "$PYTHON not found; install Python 3.10 or newer." >&2
    exit 1
fi

echo "Creating virtualenv: $VENV"
"$PYTHON" -m venv "$VENV"
"$VENV/bin/python" -m pip install --upgrade pip >/dev/null
if [ -n "$EXTRA" ]; then
    echo "Installing Heino Reader from $ROOT (with QtWebEngine)"
else
    echo "Installing Heino Reader from $ROOT (without QtWebEngine)"
fi
"$VENV/bin/python" -m pip install "$ROOT$EXTRA"

echo "Linking launcher into $BIN_HOME"
mkdir -p "$BIN_HOME"
ln -sf "$VENV/bin/heino-reader" "$BIN_HOME/heino-reader"

echo "Installing desktop entry and icon"
mkdir -p "$DATA_HOME/applications" \
         "$DATA_HOME/icons/hicolor/scalable/apps"
install -m 0644 "$ROOT/heino-reader.desktop" \
    "$DATA_HOME/applications/heino-reader.desktop"
install -m 0644 "$ROOT/src/HeinoReader/icon.svg" \
    "$DATA_HOME/icons/hicolor/scalable/apps/heino-reader.svg"

if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$DATA_HOME/applications" || true
fi

echo
echo "Installed:"
echo "  launcher: $BIN_HOME/heino-reader"
echo "  desktop:  $DATA_HOME/applications/heino-reader.desktop"
echo "  icon:     $DATA_HOME/icons/hicolor/scalable/apps/heino-reader.svg"
if [ -z "$EXTRA" ]; then
    echo
    echo "Note: QtWebEngine is not installed; View -> Web Engine Preview is"
    echo "      disabled. Add it later with: scripts/install.sh --web"
fi

case ":$PATH:" in
    *":$BIN_HOME:"*) ;;
    *)
        echo
        echo "Note: $BIN_HOME is not on PATH; add it to run 'heino-reader'."
        ;;
esac
