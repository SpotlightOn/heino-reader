# PySide6 6.12.0 on Python ≤ 3.11: `none_dealloc: deallocating None` after many `QSyntaxHighlighter.setFormat()` calls

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

The interpreter version decides: **6.12.0 is clean on Python 3.12 and newer**
and aborts on 3.10/3.11. `None` and `True` have been immortal since Python 3.12
(PEP 683); on older interpreters an over-decrement frees them and the next
deallocation aborts. See [Root cause](#root-cause).

No painting, line numbers or third-party code are involved — a bare
`QPlainTextEdit` plus `QSyntaxHighlighter` is enough.

## Environment

- PySide6 **6.12.0** (crash) / 6.11.2, 6.8.3 (OK)
- Qt 6.12.0
- Python 3.11.16 (crash), 3.12.x and 3.14.7 (no crash, same PySide6)
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
| 43-line markdown document, Python 3.11 | crash |
| same, Python 3.12 / 3.14 | no crash |
| Python 3.14, 4400-line document in an editor | no crash |
| 6.11.2 / 6.8.3, same script | no crash |

Conclusions:

- Triggered by `QSyntaxHighlighter.setFormat(int, int, QTextCharFormat)`
  being called many times, i.e. once per document block.
- Limited to Python 3.10/3.11. The same wheel on 3.12+ survives the identical
  script, so it is neither a Qt nor a platform problem.
- Independent of painting: the crash also occurs when the widget is never
  shown, so `QPainter`/line-number gutters are not involved.
- Independent of the concrete widget class.
- The error surfaces at object deallocation (`tp_dealloc` with `ob_type ==
  NULL`) after an over-decrement freed an object that must never be freed.

## Root cause

Upstream reports the same failure signature for a different API:
**PYSIDE-3474** ("6.12.0: Signal.emit() decrements the refcount of Py_True:
Python 3.10/3.11 abort after a few hundred emissions", resolved, fix version
**6.12.1**) and **PYSIDE-3477** (same for `bool_dealloc`, closed as duplicate).
Both describe PySide6 6.12.0 over-decrementing the refcount of a borrowed
immortal object.

That matches every observation here: the abort only happens on interpreters
where `None` is not immortal, and the value that dies is a temporary wrapper
the caller never owned — `setFormat()` takes `const QTextCharFormat &`, so the
Python wrapper is only needed for the duration of the call.

Whether 6.12.1 also clears this reproducer has to be measured, not assumed:
6.12.1 is not on PyPI yet.

## Workaround

Run on Python 3.12 or newer, or pin to a release below 6.12:

```
PySide6>=6.6,<6.12   # Python 3.10/3.11
PySide6>=6.12,<6.13  # Python 3.12+
```

Heino Reader does exactly that in `pyproject.toml`. Once 6.12.1 is out, drop
the marker.

## Self-check

A reproducer lives at `scripts/check_pyside6_crash.py` in the reporting
project; it exits 0 when the crash is gone. Run it with a Python 3.10/3.11
interpreter — on 3.12+ it never fires.
