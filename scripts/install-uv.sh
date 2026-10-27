#!/usr/bin/env bash
# Install Heino Reader into the XDG home with uv.
#
# uv creates an isolated tool environment, so no manual virtualenv is needed.
# The launcher lands in ~/.local/bin (or $UV_TOOL_BIN_DIR); the desktop entry
# and icon are installed alongside it.
#
# The default install is the small one: Qt's base modules only
# (pyside6-essentials, ~240 MB installed). QtWebEngine comes with
# pyside6-addons (~440 MB) and is only pulled in with --web.
#
# Usage:
#   scripts/install-uv.sh              install (Qt renderer, no QtWebEngine)
#   scripts/install-uv.sh --web        install with QtWebEngine support
#   scripts/install-uv.sh --uninstall  remove everything again

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"

uninstall() {
    echo "Removing the Heino Reader uv tool"
    uv tool uninstall heino-reader || true
    rm -f "$DATA_HOME/applications/heino-reader.desktop"
    rm -f "$DATA_HOME/icons/hicolor/scalable/apps/heino-reader.svg"
    if command -v update-desktop-database >/dev/null 2>&1; then
        update-desktop-database "$DATA_HOME/applications" || true
    fi
    echo "Done."
}

ACTION="install"
WITH_WEB=0

usage() {
    cat >&2 <<'EOF'
Usage: scripts/install-uv.sh [install|--uninstall] [--web]

  --web        also install QtWebEngine (pyside6-addons, ~440 MB) for the
               optional Web Engine preview
  --uninstall  remove the tool, desktop entry and icon
EOF
}

for arg in "$@"; do
    case "$arg" in
        ""|install) ;;
        --web|web) WITH_WEB=1 ;;
        --uninstall|uninstall) ACTION="uninstall" ;;
        -h|--help) usage; exit 0 ;;
        *) echo "Unknown argument: $arg" >&2; usage; exit 2 ;;
    esac
done

if [ "$ACTION" = "uninstall" ]; then
    uninstall
    exit 0
fi

if ! command -v uv >/dev/null 2>&1; then
    echo "uv not found. Install it from https://docs.astral.sh/uv/" >&2
    exit 1
fi

if [ "$WITH_WEB" -eq 1 ]; then
    echo "Installing the Heino Reader tool from $ROOT (with QtWebEngine)"
    uv tool install --force "$ROOT" --with "PySide6-Addons>=6.6,<6.12"
else
    echo "Installing the Heino Reader tool from $ROOT (without QtWebEngine)"
    uv tool install --force "$ROOT"
fi

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
echo "  launcher: ${UV_TOOL_BIN_DIR:-$HOME/.local/bin}/heino-reader"
echo "  desktop:  $DATA_HOME/applications/heino-reader.desktop"
echo "  icon:     $DATA_HOME/icons/hicolor/scalable/apps/heino-reader.svg"
if [ "$WITH_WEB" -eq 0 ]; then
    echo
    echo "Note: QtWebEngine is not installed; View -> Web Engine Preview is"
    echo "      disabled. Add it later with: scripts/install-uv.sh --web"
fi
