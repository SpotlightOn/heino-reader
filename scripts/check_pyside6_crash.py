"""Minimal reproducer for a PySide6 6.12.0 refcount crash.

Run it against a candidate PySide6 version to check whether the crash is
still present::

    uv run python scripts/check_pyside6_crash.py

Exit code 0 means the version is fine; a fatal interpreter crash
(``none_dealloc: deallocating None``) means it is still broken. The crash
needs a QSyntaxHighlighter that sets character formats plus scrolling; no
Heino Reader code is involved, so it is purely a PySide6/sh boken issue.

Pinned to ``<6.12`` because of this. See README, "Development".
"""

from __future__ import annotations

import sys

from PySide6 import __version__ as pyside_version
from PySide6.QtGui import QColor, QSyntaxHighlighter, QTextCharFormat
from PySide6.QtWidgets import QApplication, QPlainTextEdit


class _Highlighter(QSyntaxHighlighter):
    def highlightBlock(self, text: str) -> None:
        fmt = QTextCharFormat()
        fmt.setForeground(QColor("blue"))
        self.setFormat(0, min(3, len(text)), fmt)


def main() -> int:
    app = QApplication(sys.argv)
    edit = QPlainTextEdit()
    _Highlighter(edit.document())
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
