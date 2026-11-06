# Workarounds

The Qt text renderer works around the limits of `QTextDocument`'s rich text
engine in a handful of places. Each entry states what the code does, why the
obvious alternative does not work, and where it lives, so it can be deleted
once the engine (or PySide6) catches up.

Measurements were taken against Qt 6.11.3 in an 800 px wide window: the
viewport is 784 px there (the scrollbar is always visible) and the text column
752 px. The test suite asserts the same geometry on PySide6 6.11 and 6.12.

## Qt text renderer

| Workaround | Why Qt needs it | Where |
| --- | --- | --- |
| The vertical scrollbar is always visible | The column width is derived from the viewport width. A scrollbar that appears later narrows the viewport without a `resizeEvent`, so the document stays laid out for the wider viewport and Qt adds a horizontal scrollbar. A constant viewport width removes the second layout pass. | `viewer/qt.py`, `QtMarkdownView.__init__` |
| Markdown tables get an explicit `QTextTableFormat` width | Qt draws the outer cell borders outside the table width, so a table that fills the column ends up 2 px too wide. `box-sizing` is not supported. | `viewer/qt.py`, `_fit_tables()` |
| Images are scaled by rewriting every `QTextImageFormat` | `max-width: 100%` from the theme is not enough: without the manual fit the document is 24 px wider than the viewport. | `viewer/qt.py`, `_fit_images()` |
| The text column is centred with root frame margins | Qt has no `body { max-width: …; margin: 0 auto }`; the document always spans the whole viewport. | `viewer/qt.py`, `_apply_content_width()` |
| Fenced and indented code blocks are one-cell tables | Padding, border and background are ignored on block elements, so a `<pre>` would sit flush against its surroundings. | `viewer/render.py`, `_code_block_qt()` |
| Code lines are joined with `<br>` | Qt creates one text block per newline and paints a separate background for each, which looks like one grey bar per line. | `viewer/render.py`, `_highlighted_fence_qt()`, `_indented_code_qt()` |
| Block quotes are one-cell tables | Same reason as code blocks: the padding and the left bar need a cell. | `viewer/render.py`, `_quote_open_qt()` |
| Those wrappers use the HTML attribute `width="100%"` | Qt ignores `table { width: 100% }` from a stylesheet; the attribute is honoured (and yields a percentage-width table). | `viewer/render.py`, `_code_block_qt()`, `_quote_open_qt()` |
| Code lines are wrapped with `white-space: pre-wrap` | Qt can scroll a document but not a single block, so one wide line widens the whole document. `overflow-x`, `word-wrap` and `word-break` are unsupported. | `viewer/render.py`, `_PRE_WRAP_RULE` |
| The body line height is applied with `* { line-height: … }` | `setHtml()` parses a fragment without a `<body>` element, so a `body { … }` rule never matches. Wrapping the fragment in `<body>` makes the rule apply, but Qt then paints an empty body line: measured 70 → 97 px for a two-block document. The universal selector reaches every element and leaves the more specific heading and `pre` rules intact. | `viewer/render.py`, `qt_stylesheet()` |
| Every `line-height` is rewritten to a percentage | Qt reads the number as a share of the font's natural line height; CSS means a multiple of the font size. | `viewer/render.py`, `qt_stylesheet()` |
| The body font size is converted from px to pt | Qt sizes fonts in points and scales them with the screen DPI, while CSS pixel sizes are DPI blind inside `QTextDocument`. | `viewer/render.py`, `viewer_body_point_size()` |
| Relative image and link targets are rewritten to absolute paths | Qt resolves relative paths against the process working directory, not the document's directory. | `viewer/render.py`, `_resolve_relative_paths()` |

## Verification status

Measured with numbers, in this repository:

- always-visible scrollbar — without it the document is 14 px wider than the viewport
- table width — without it a table that fills the column is 2 px too wide
- image fit — without it the document is 24 px wider than the viewport
- body line height — a `<body>` wrapper works but adds a 27 px empty line

Taken from the code's own comments and the commit history, **not re-measured**:

- code blocks and quotes as table cells
- `<br>` joining of code lines
- `width="100%"` on those wrappers
- `white-space: pre-wrap` for code
- px → pt font size conversion
- relative path rewriting

Each of those needs its own measurement before it can be called justified.

## Dependency pins

| Workaround | Why | Where |
| --- | --- | --- |
| Python 3.10/3.11 get PySide6 6.11.3, 3.12+ get 6.12 | 6.12.0 over-decrements the refcount of immortal objects such as `None`, which those interpreters still free: a 43-line document aborts with `none_dealloc` (exit 134), while 3.12 and 3.14 stay clean. PYSIDE-3474, fixed in 6.12.1. | `pyproject.toml`, [report](upstream-bug-pyside6-6.12-none-dealloc.md) |

## Test harness

| Workaround | Why | Where |
| --- | --- | --- |
| Test windows are deleted before pytest-qt closes them | Closing a window that holds a WebEngine view before the Chromium page is gone crashes inside Qt. | `tests/conftest.py` |
| pytest-qt's Qt log capture is disabled (`--no-qt-log`) | pytest-qt installs a Python `qInstallMessageHandler` before every test and restores the previous one afterwards. A QtWebEngine warning emitted from a Chromium thread during that swap makes PySide6 call a NULL handler: measured 2 crashes in 30 runs, and the core shows `PyObject_CallObject(NULL, …)` under `QMessageLogger::warning()` from `libQt6WebEngineCore`. With the capture disabled: 0 crashes in 90 runs, while the same warning ("GPUInfo not initialized on GpuInfoUpdate") appears in about 70 % of them. No test reads the captured messages. | `pyproject.toml` |

## Removed

- **Reflow when the viewport resizes** — recomputed the whole layout when the
  viewport width changed. Gone: the always-visible scrollbar keeps the viewport
  width constant, so the extra pass is unnecessary. The commit is not part of
  the history.

## Not present

Checked, so that a future change does not reintroduce them unnoticed:

- no timers or deferred layout passes in the render path — the only `QTimer`
  is the 200 ms typing debounce in `editpane.py`
- no `QApplication.processEvents()` while rendering
- no monkeypatched Qt internals
- no forced repaints or explicit `update()` calls to make layout settle
