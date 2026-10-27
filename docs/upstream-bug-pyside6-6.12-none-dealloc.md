# PySide6 6.12.0: `none_dealloc: deallocating None` after many `QSyntaxHighlighter.setFormat()` calls

## Summary

On PySide6 **6.12.0**, running a `QSyntaxHighlighter` whose `highlightBlock()`
calls `setFormat()` with a `QTextCharFormat` on a document with many blocks
crashes the interpreter with a shiboken refcount error:

```
Fatal Python error: none_dealloc: deallocating None: bug likely caused by a
refcount error in a C extension
Python runtime state: initialized
```

The crash is nondeterministic in *when* it happens (during the event loop or
during interpreter shutdown) but reproduces reliably for the steps below.
PySide6 **6.11.2** and **6.8.3** are unaffected with identical code.

No painting, line numbers or third-party code are involved — a bare
`QPlainTextEdit` plus `QSyntaxHighlighter` is enough.

## Environment

- PySide6 **6.12.0** (crash) / 6.11.2, 6.8.3 (OK)
- Qt 6.12.0
- Python 3.11.16 (CPython, standard build)
- Linux 7.2.3 x86_64 (Manjaro), glibc 2.44
- Qt platform plugin: `offscreen` and `xcb` both reproduce

## Steps to reproduce

Save the file below and run it with an affected PySide6 version:

```sh
python reproduce.py
```

```python
"""Minimal reproducer: PySide6 6.12.0 refcount crash with QSyntaxHighlighter."""

import sys

from PySide6 import __version__ as pyside_version
from PySide6.QtGui import QColor, QSyntaxHighlighter, QTextCharFormat
from PySide6.QtWidgets import QApplication, QPlainTextEdit


class Highlighter(QSyntaxHighlighter):
    def highlightBlock(self, text: str) -> None:  # noqa: N802 - Qt virtual
        fmt = QTextCharFormat()
        fmt.setForeground(QColor("blue"))
        self.setFormat(0, min(3, len(text)), fmt)


def main() -> int:
    app = QApplication(sys.argv)
    edit = QPlainTextEdit()
    Highlighter(edit.document())
    edit.resize(400, 300)
    edit.setPlainText("\n".join(f"line {i} with some text" for i in range(1500)))
    edit.show()
    app.processEvents()
    for i in range(1500):
        edit.verticalScrollBar().setValue(
            (i * 37) % edit.verticalScrollBar().maximum()
        )
        app.processEvents()
    print(f"PySide6 {pyside_version}: no crash")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

## Actual behavior

The process aborts with `SIGABRT` (exit code 134):

```
Fatal Python error: none_dealloc: deallocating None: bug likely caused by a
refcount error in a C extension
Python runtime state: initialized

Current thread 0x... (most recent call first):
  File "reproduce.py", line 27 in <module>

Extension modules: shiboken6.Shiboken, PySide6.QtCore, PySide6.QtGui,
PySide6.QtWidgets (total: 4)
```

Depending on garbage-collection timing the abort happens either inside the
loop or during interpreter finalization; in the latter case `no crash` is
printed first and the process still aborts with 134.

## Expected behavior

The script prints `PySide6 6.12.0: no crash` and exits with code 0, as it
does on 6.11.2 and 6.8.3.

## Characterization

Measured on 6.12.0 by varying one factor at a time:

| Variant | Result |
| --- | --- |
| fresh `QTextCharFormat()` per `highlightBlock` | crash |
| one shared `QTextCharFormat` reused | no crash in the loop, crash at exit |
| `highlightBlock` without `setFormat` | no crash |
| no highlighter at all | no crash |
| `QTextEdit` instead of `QPlainTextEdit` | crash |
| widget never shown (no painting at all) | crash |
| 20-line document instead of 1500 | no crash |
| 6.11.2 / 6.8.3, same script | no crash |

Conclusions:

- Triggered by `QSyntaxHighlighter.setFormat(int, int, QTextCharFormat)`
  being called many times, i.e. once per document block.
- Independent of painting: the crash also occurs when the widget is never
  shown, so `QPainter`/line-number gutters are not involved.
- Independent of the concrete widget class.
- The error surfaces at object deallocation (`tp_dealloc` with `ob_type ==
  NULL`), which points at a refcount/ownership error for value-type
  wrappers rather than a logic error in user code.

## Workaround

Pin to a release below 6.12 until this is fixed:

```
PySide6>=6.6,<6.12
```

## Analysis hints

- Prime suspect for a bisect is commit
  `8d33ddd7a4868365295fd0501e84e2b6435b70d6`
  ("libshiboken: Avoid allocating an array for the C++ instance pointers",
  2026-09-26, released in 6.12.0). It reworked `SbkObjectPrivate` storage
  into `SbkObjectPrivate1` / `SbkObjectMultiInheritancePrivate`, added the
  `is_multicpp` bit, and rewrote `deallocData()`, `destroy()`,
  `cppPointer(s)` and `setCppPointer()` — i.e. exactly the wrapper
  lifetime/deallocation paths where a `none_dealloc` would surface.
- The `<value-type name="QTextCharFormat">` entry in
  `sources/pyside6/PySide6/QtGui/typesystem_gui_common.xml` has no special
  modifications, so the regression is unlikely to be in the type system
  description.
- `setFormat()` takes `const QTextCharFormat &`, so the Python wrapper is
  only needed for the duration of the call. An over-decref of that
  temporary wrapper is consistent with the observed `none_dealloc`.
- Once the offending commit is known, running the reproducer against a
  build with `PYTHONMALLOC=debug` and `gc.set_debug()` should make the
  affected wrapper visible.

A self-check script lives at `scripts/check_pyside6_crash.py` in the
reporting project; it exits 0 when the crash is gone.
