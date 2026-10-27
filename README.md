# Heino Reader

[![CI](https://github.com/SpotlightOn/heino-reader/actions/workflows/ci.yml/badge.svg)](https://github.com/SpotlightOn/heino-reader/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/heino-reader)](https://pypi.org/project/heino-reader/)
[![Python versions](https://img.shields.io/pypi/pyversions/heino-reader)](https://pypi.org/project/heino-reader/)
[![Qt for Python](https://img.shields.io/badge/Qt_for_Python-PySide6-41cd52)](https://doc.qt.io/qtforpython-6/)

A fast document viewer for markdown files, built with PySide6.

Heino Reader is named after Heino – Heinz Georg Kramm, a German singer who
turned his blond mane, black sunglasses and "Blau blüht der Enzian" into a
decades-long fixture of German television. Known for constantly reinventing
himself, he even covered Rammstein songs. Consider it an homage: dark glasses
on, no fuss, just the text.

Heino Reader renders markdown read-only: `markdown-it-py` (CommonMark plus
tables) converts it to HTML, Pygments highlights code blocks, and Qt's rich
text engine paints the result with a stylesheet theme. A QtWebEngine backend
is available as an opt-in for full HTML/CSS fidelity. It can be started with
a file path, so it can be bound to the `.md` extension in file managers like
Dolphin.

## Features

- CommonMark rendering with a GitHub-style theme: headings, nested lists,
  tables, block quotes, inline and fenced code with Pygments syntax colors.
  The theme is a plain stylesheet: `src/heinoreader/preview.css`
- Code blocks and quotes are framed with a border, a background and real
  inner padding; blocks keep their distance to the text above and below
- Two preview backends, switchable at runtime (**View → Web Engine
  Preview**) or via `--renderer qt|web` (default `qt`). The `qt` backend
  uses QTextEdit, starts instantly and is limited by Qt's small CSS subset;
  QtWebEngine is the faithful renderer and is loaded only when it is
  actually selected
- Fast start: only what is needed is loaded. The Qt preview starts without
  Chromium, and the whole editor stack (source pane, syntax highlighter,
  line-number gutter) is created on the first click on **Edit mode**
- The start screen shows the app icon and a short guide: open, edit, zoom,
  remote images and the WebEngine switch
- Top toolbar with button-style icons: `text_decrease` and
  `text_increase` scale the font size, `edit` toggles edit mode,
  `exit_to_app` closes the window, plus a zoom level indicator (e.g.
  `130%`) that is always visible in the right corner
- Content is inset and the text column is capped at 760 px and centred,
  so it never touches the window edges and lines stay readable
- Standard menu bar: **File → Open… / Save / Save As… / Close**,
  **View → …**, **Help → About**; saving is enabled in edit mode only
- Edit mode toggle: splits the window with the markdown source on the
  left and a live preview on the right (like Ghostwriter); clicking the
  button again returns to the default preview-only view. Entering edit
  mode widens the window up to 1200 px (clamped to the usable screen
  width, so it never grows beyond the display) and leaving it restores
  the previous size and position
- Markdown formatting in edit mode: a second toolbar row (bold, italic,
  underline, strikethrough, inline code, heading dropdown, block quote,
  bullet and numbered list) appears only while editing; every command
  also has a keyboard shortcut
- Insert elements from dialogs: **Link** (`Ctrl+K`) wraps the selection
  in `[label](url)`, **Image** (`Ctrl+Shift+I`) picks a file via a
  chooser and stores it relative to the document, **Table**
  (`Ctrl+Shift+T`) asks for rows and columns and inserts a ready-made
  skeleton with the first header cell selected
- The source pane is a real code editor: markdown syntax highlighting,
  Tab / Shift+Tab indent whole lines, and Enter continues at the text's
  indentation (so quotes, lists and indented blocks stay aligned); a
  block quote bar marks lines that start with `>`
- Line numbers are optional: **View → Line Numbers** attaches a gutter
  on demand; the editor works fine without it
- Links open with the system default application (xdg-open)
- Live reload when the opened file changes on disk
- Relative image and link paths resolve against the markdown file's
  directory (code blocks stay untouched)
- Images scale down to the available width (aspect ratio preserved) and
  refit when the window is resized, so wide images never break the layout
- Remote images (`http(s)`) are downloaded asynchronously and cached;
  **View → Load Remote Images** turns the network access off, and any
  image that is disabled or fails to load shows a visible placeholder
- Drag & drop a markdown file onto the window
- Only markdown/text files are opened: an image, archive or any other
  binary dropped on the window is refused with a message instead of being
  loaded as text (same check for the Open dialog, the command line and a
  file larger than 10 MB)

## Keyboard shortcuts

Viewing:

| Shortcut | Action |
| --- | --- |
| `Ctrl++` / `Ctrl+-` | Zoom in / out |
| `Ctrl+0` | Reset zoom to 100 % |
| `Ctrl+Q` | Quit |
| `Ctrl+O` | Open a file |
| `Ctrl+S` | Save (edit mode) |
| `Ctrl+Shift+S` | Save as… (edit mode) |
| `Ctrl+W` | Close the file |

Formatting (edit mode only):

| Shortcut | Action | Markdown |
| --- | --- | --- |
| `Ctrl+B` | Bold | `**…**` |
| `Ctrl+I` | Italic | `*…*` |
| `Ctrl+U` | Underline | `<u>…</u>` |
| `Ctrl+Shift+X` | Strikethrough | `~~…~~` |
| `Ctrl+E` | Inline code | `` `…` `` |
| `Ctrl+1` … `Ctrl+6` | Heading level 1–6 | `#` … `######` |
| `Ctrl+Shift+0` | Plain paragraph | (clears the heading) |
| `Ctrl+Shift+Q` | Block quote | `> ` |
| `Ctrl+Shift+L` | Bullet list | `- ` |
| `Ctrl+Shift+N` | Numbered list | `1. ` |

Insert (edit mode only, each opens a dialog):

| Shortcut | Action | Result |
| --- | --- | --- |
| `Ctrl+K` | Link… | `[label](url)` |
| `Ctrl+Shift+I` | Image… | `![alt](path)` |
| `Ctrl+Shift+T` | Table… | ready-made table skeleton |

Every formatting command is a toggle: applying it to text that already
carries the marker removes it again, and each command is a single undo
step.

## Icons

Toolbar icons are bundled Material Symbols Outlined SVGs (`icons/*.svg`,
Apache License 2.0, © Google) and are rendered with the palette text color,
so they stay readable in light and dark themes. If a file is missing, the
app falls back to the desktop theme icons.

## Usage

```sh
uv run heinoreader path/to/notes.md
uv run heinoreader --renderer web path/to/notes.md   # opt in to QtWebEngine
```

`uv run python -m heinoreader path/to/notes.md` works as well. No argument
opens the viewer with a short guide.

## Install locally (XDG)

Both scripts install into the XDG home and need no root rights. They put
the launcher in `~/.local/bin`, the desktop entry in
`$XDG_DATA_HOME/applications` and the icon in the XDG icon theme.

With **uv** (isolated tool environment, no manual virtualenv):

```sh
scripts/install-uv.sh
```

Without uv (private virtualenv under `$XDG_DATA_HOME/heinoreader/venv`):

```sh
scripts/install.sh
```

Both accept `--uninstall`. Afterwards `heinoreader` is available on your
PATH (when `~/.local/bin` is), and you can associate `.md` files in Dolphin:
right-click → *Open With* → *Other Application* → *Heino Reader*, optionally
as the default.

## Development

Dependencies are managed with [uv](https://docs.astral.sh/uv/):

```sh
uv sync                        # create .venv and install PySide6 + Heino Reader
uv run heinoreader file.md     # run from the synced environment
uv run pytest                  # run the test suite
```

QtWebEngine comes with `pyside6-addons` (installed by the `PySide6`
meta-package). It is imported on demand only, so the default Qt preview
also runs without it; the test suite sets the headless Chromium flags
itself.

PySide6 is pinned to `<6.12`: 6.12.0 has a refcount crash in Qt's
syntax highlighter that triggers on scrolling, independent of this code.
To check whether a newer version still has it, run:

```sh
uv run python scripts/check_pyside6_crash.py
```

## Project layout

```
src/heinoreader/      the package
  __init__.py           entry point (main) and public re-exports
  window.py             the viewer window: menus, toolbars, edit mode
  icons.py              toolbar icons (Material SVGs, theme fallbacks)
  __main__.py           enables python -m heinoreader
  preview.css           the preview theme (edit freely)
  render.py             markdown to HTML, path helpers
  webview.py            QtWebEngine preview backend (opt-in, lazy import)
  qtview.py             QTextEdit preview backend (default)
  layout.py             text column geometry
  images.py             remote image loading for the Qt backend
  files.py              file validation (no binary/oversized files)
  settings.py           persistent settings in the XDG config directory
  utils.py              small shared helpers
  editor/               the source markdown editor subsystem
    __init__.py           public API of the subpackage
    source_edit.py        plain-text editor, Tab indent, quote bar
    highlighter.py        markdown syntax highlighting
    line_numbers.py       optional line-number gutter (View menu)
    formatting.py         GUI-free formatting operations on a cursor
    dialogs.py            insert dialogs (link, image, table)
  icons/                bundled Material Symbols SVGs
tests/                pytest + pytest-qt suite
scripts/              install scripts and the PySide6 crash check
main.py               entry point for PyInstaller builds
```

The `editor/` subpackage is self-contained: it imports only Qt and its
own sibling modules, never the top-level `heinoreader` module, so there are
no circular imports. `__init__.py` re-exports the editor pieces; the editor
widget itself is only built when edit mode is opened.
