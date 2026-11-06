# Development

Dependencies are managed with [uv](https://docs.astral.sh/uv/):

```sh
uv sync                        # create .venv and install PySide6 + Heino Reader
uv run heino-reader file.md    # run from the synced environment
uv run python -m pytest        # run the test suite
uv run python -m pytest --cov --cov-report=term-missing   # with coverage
```

## Dependencies

The app depends on `pyside6-essentials` only. QtWebEngine is the optional extra
`web` (`pip install "heino-reader[web]"`), so the plugin is imported on demand
only. PySide6 6.12 ships QtWebEngine as a separate `pyside6-webengine` wheel;
6.11 has it inside `pyside6-addons`. Environment markers in `pyproject.toml`
name whichever applies to the running interpreter.

The `dev` dependency group pulls in QtWebEngine so the test suite can exercise
both backends; the suite sets the headless Chromium flags itself.

## PySide6 versions

Python 3.12 and newer get PySide6 6.12, older interpreters stay on 6.11.3.

6.12.0 aborts on Python 3.10/3.11 once a `QTextCharFormat` is applied to a
document of more than a few dozen blocks — the syntax highlighter alone is
enough: it over-decrements the refcount of immortal objects, which those
interpreters still free. Upstream fixed it in 6.12.1 (PYSIDE-3474), which is not
released yet. Background and measurements:
[upstream-bug-pyside6-6.12-none-dealloc.md](upstream-bug-pyside6-6.12-none-dealloc.md).

The reproducer only fails on 3.10/3.11, so test a candidate version with that
interpreter:

```sh
uv run python scripts/check_pyside6_crash.py   # 3.12+: exits 0
uv sync --python 3.11 --group dev              # 6.11.3 leg, then run the suite
```

Once 6.12.1 is on PyPI, the markers collapse to a single requirement.

## Project layout

```
src/HeinoReader/      the package
  __init__.py           docstring and module map
  __main__.py           enables python -m HeinoReader
  cli.py                command line entry point, starts QApplication
  window.py             the main window: wiring, files, edit mode, zoom
  document.py           the open file: text, path, modified state (no widgets)
  editpane.py           source editor, gutter and typing delay
  chrome.py             menu bar and toolbars
  actions.py            every action: icon, shortcut, tooltip, handler
  texts.py              about text, start screen, toolbar style
  layout.py             text column geometry
  files.py              file validation (no binary/oversized files)
  settings.py           persistent settings in the XDG config directory
  icons.py              toolbar icons (Material SVGs, theme fallbacks)
  utils.py              small shared helpers
  icon.svg              the application icon
  icons/                bundled Material Symbols SVGs
  viewer/               the document display subsystem
    __init__.py           the two backends and the one on screen
    qt.py                 QTextEdit backend (default)
    web.py                QtWebEngine backend (opt-in, lazy import)
    render.py             markdown to HTML, path helpers
    highlighting.py       Pygments colors for fenced code
    images.py             remote image loading for the Qt backend
    document.css          the document theme (edit freely)
  editor/               the source markdown editor subsystem
    __init__.py           public API of the subpackage
    source_edit.py        plain-text editor, Tab indent, quote bar
    highlighter.py        markdown syntax highlighting
    formatting.py         GUI-free formatting operations on a cursor
    line_numbers.py       optional line-number gutter (View menu)
    dialogs.py            insert dialogs (link, image, table)
tests/                pytest + pytest-qt suite
scripts/              install scripts and the PySide6 crash check
main.py               entry point for PyInstaller builds
```

`window.py` is a composition root: it wires `document.py`, `editpane.py`,
`viewer/` and `chrome.py` together and owns the file lifecycle. Actions are
defined once in `actions.py`; `chrome.py` only decides where they appear. The
`viewer/` subpackage holds everything that paints the document: the Qt and the
QtWebEngine backend share `render.py` and differ only in where the HTML goes.
`web.py` is the only module that imports `PySide6.QtWebEngine*`, and it is
imported lazily from `viewer/__init__.py`, so a Qt-rendered start never loads
Chromium. The `editor/` subpackage is self-contained: it imports only Qt and
its own sibling modules, never the top-level package, so there are no circular
imports. Tests import a name from the module that owns it, not from the
package root.

## Naming

- **Heino Reader** — the product name, with a space: prose, UI text, window
  title, About dialog, `Name=` in the desktop entry.
- **heino-reader** — machine names that cannot hold spaces or capitals: the
  repository, the PyPI project, the console script, the `.desktop` file name,
  the XDG directories (`~/.config/heino-reader`), the icon name and
  `StartupWMClass`.
- **HeinoReader** — the Python package and import name only, because a hyphen is
  not legal in an identifier.
- **HEINO_READER_CONFIG_DIR** — the environment variable.

## Icons

Toolbar icons are bundled Material Symbols Outlined SVGs (`icons/*.svg`,
Apache License 2.0, © Google).
