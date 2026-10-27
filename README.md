<p align="center">
  <img src="https://raw.githubusercontent.com/SpotlightOn/heino-reader/main/src/HeinoReader/icon.svg" width="112" alt="Heino Reader icon">
</p>

<h1 align="center">Heino Reader</h1>

<p align="center">
  <a href="https://github.com/SpotlightOn/heino-reader/actions/workflows/ci.yml"><img src="https://github.com/SpotlightOn/heino-reader/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://pypi.org/project/heino-reader/"><img src="https://img.shields.io/pypi/v/heino-reader?style=flat" alt="PyPI"></a>
  <a href="https://pypi.org/project/heino-reader/"><img src="https://img.shields.io/pypi/pyversions/heino-reader?style=flat" alt="Python versions"></a>
  <a href="https://doc.qt.io/qtforpython-6/"><img src="https://img.shields.io/badge/Qt_for_Python-PySide6-41cd52" alt="Qt for Python"></a>
  <a href="https://socket.dev/pypi/package/heino-reader"><img src="https://socket.dev/api/badge/pypi/package/heino-reader" alt="Socket: supply-chain score"></a>
  <a href="LICENSE"><img src="https://img.shields.io/github/license/SpotlightOn/heino-reader" alt="License: MIT"></a>
</p>

A fast document viewer for markdown files, built with PySide6.

Heino Reader is named after [Heino – Heinz Georg Kramm](https://de.wikipedia.org/wiki/Heino),
a German singer who turned his blond mane, black sunglasses and "Blau blüht der Enzian" into a
decades-long fixture of German television. Known for constantly reinventing
himself, he even [covered Rammstein songs](https://www.youtube.com/watch?v=uVZ__cDE0EI). Consider it an homage: dark glasses on, no fuss, just the text. 😎

Rendering is read-only: `markdown-it-py` turns CommonMark plus tables into
HTML, Pygments colors the code, a stylesheet theme sets the look. The optional
Web Engine backend is the better but slower renderer with full CSS fidelity
([details](docs/renderers.md)). Assign `.md` to Heino Reader in Dolphin and your
notes open with a double click.

```sh
heino-reader notes.md
```

## Install

```sh
uv tool install heino-reader     # or: pipx install heino-reader
```

No Python? Prebuilt AppImage, `.app` and `.exe` live on the
[latest release](https://github.com/SpotlightOn/heino-reader/releases) page.
Prefer everything local? `scripts/install.sh` drops a launcher in `~/.local/bin`
without touching your system Python. None of this needs root rights.
→ [Installation details](docs/installation.md)

## Why you might like it

- **Instant.** No Chromium in the default renderer — just Qt's text engine.
- **Read-only first.** Nothing changes by accident; edit mode is one click away.
- **Live reload.** Save in your editor, the preview follows.
- **Split editing when you want it.** Source on the left, live preview on the
  right — like Ghostwriter, with a formatting toolbar and shortcuts.
- **Light.** ~260 MB installed — no Electron, no bundled browser process.
- **Native desktop app.** Drag & drop, `.md` file association, links opened with
  xdg-open, toolbar icons in your system colors.

## Docs

| Page | What's in it |
| --- | --- |
| [Installation](docs/installation.md) | PyPI, local XDG install, web extra, uninstall, file association |
| [Usage](docs/usage.md) | Menus, edit mode, insert dialogs, all keyboard shortcuts |
| [Renderers](docs/renderers.md) | Qt text engine vs. Web Engine, feature by feature |
| [Development](docs/development.md) | Setup, tests, project layout, naming conventions |

## License

MIT, see [LICENSE](LICENSE). Copyright (c) 2026 SpotlightOn.
