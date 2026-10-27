# Installation

Heino Reader is a Python/Qt application. Pick whichever route fits your setup;
none of them need root rights.

## From PyPI

```sh
uv tool install heino-reader          # isolated tool environment
# or
pipx install heino-reader
```

The tool then lives on your `PATH` as `heino-reader`. Add the optional Web
Engine renderer with:

```sh
uv tool install "heino-reader[web]"
```

## Local XDG install

The install scripts in `scripts/` create a private environment under
`$XDG_DATA_HOME/heino-reader/venv`, put the launcher in `~/.local/bin`, the
desktop entry in `$XDG_DATA_HOME/applications` and the icon into the XDG icon
theme.

With **uv** (no manual virtualenv):

```sh
scripts/install-uv.sh              # Qt renderer only, ~260 MB installed
scripts/install-uv.sh --web        # plus QtWebEngine, ~700 MB installed
```

Without uv (plain virtualenv):

```sh
scripts/install.sh                 # Qt renderer only, ~260 MB installed
scripts/install.sh --web           # plus QtWebEngine, ~700 MB installed
```

Both scripts accept `--uninstall`.

## Why the default install is small

The app itself only needs Qt's base modules, all of which ship in
`pyside6-essentials`: `QtCore`, `QtGui`, `QtWidgets`, `QtSvg`, `QtNetwork`.

The Web Engine renderer needs `pyside6-addons`, which is 439 MB installed —
195 MB of that is `libQt6WebEngineCore.so` alone. So `--web` stays an explicit
choice. Without it, **View → Web Engine Preview** is greyed out and the app
falls back to the Qt renderer with a note on stderr: no crash, no hidden
download.

## Open `.md` files from your file manager

After installing, `heino-reader` is on your `PATH` (assuming `~/.local/bin` is).
In Dolphin: right-click a `.md` file → *Open With* → *Other Application* →
*Heino Reader*, and optionally set it as the default. Heino Reader accepts a
file path on the command line, so it also works in any desktop entry or script.

## Prebuilt binaries (no Python needed)

Every tagged release carries ready-made builds on the
[releases page](https://github.com/SpotlightOn/heino-reader/releases):

| Platform | File | Notes |
| --- | --- | --- |
| Linux | `heino-reader-<version>-x86_64.AppImage` | `chmod +x`, then run |
| macOS | `heino-reader-<version>-macos-arm64.zip` / `-x86_64.zip` | contains the `.app` bundle |
| Windows | `heino-reader-<version>-windows-x86_64.exe` | single executable, no installer |

Releases up to 0.2.1 ship the Windows build unversioned as `heino-reader.exe`;
from 0.2.2 on all three artifacts carry the version in the file name.

The macOS and Windows builds are unsigned, so the OS will ask for confirmation
on first start. The test suite only runs on Linux — the macOS and Windows builds
come out of CI but are not covered by the test matrix, so treat them as
best-effort.
