# Development

Dependencies are managed with [uv](https://docs.astral.sh/uv/):

```sh
uv sync                        # create .venv and install PySide6 + Heino Reader
uv run heino-reader file.md    # run from the synced environment
uv run python -m pytest        # run the test suite
```

## Dependencies

The app depends on `pyside6-essentials` only. QtWebEngine lives in
`pyside6-addons` and is exposed as the optional extra `web`
(`pip install "heino-reader[web]"`), so the plugin is imported on demand only.

The `dev` dependency group pulls in `pyside6-addons` so the test suite can
exercise both backends; the suite sets the headless Chromium flags itself.

## PySide6 pin

PySide6 is pinned to `<6.12`: 6.12.0 has a refcount crash in Qt's syntax
highlighter that triggers on scrolling, independent of this code. Background:
[upstream-bug-pyside6-6.12-none-dealloc.md](upstream-bug-pyside6-6.12-none-dealloc.md).
To check whether a newer version still has it:

```sh
uv run python scripts/check_pyside6_crash.py
```

## Project layout

```
src/HeinoReader/      the package
  __init__.py           entry point (main) and public re-exports
  __main__.py           enables python -m HeinoReader
  window.py             the viewer window: menus, toolbars, edit mode
  render.py             markdown to HTML, path helpers
  qtview.py             QTextEdit preview backend (default)
  webview.py            QtWebEngine preview backend (opt-in, lazy import)
  images.py             remote image loading for the Qt backend
  layout.py             text column geometry
  files.py              file validation (no binary/oversized files)
  settings.py           persistent settings in the XDG config directory
  icons.py              toolbar icons (Material SVGs, theme fallbacks)
  utils.py              small shared helpers
  preview.css           the preview theme (edit freely)
  icon.svg              the application icon
  icons/                bundled Material Symbols SVGs
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

The `editor/` subpackage is self-contained: it imports only Qt and its own
sibling modules, never the top-level package, so there are no circular imports.
`__init__.py` re-exports the editor pieces; the editor widget itself is only
built when edit mode is opened.

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
