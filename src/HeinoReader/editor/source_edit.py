"""The plain-text markdown source editor with indenting and a quote bar.

This module is self-contained: it depends only on Qt and the sibling
highlighter module, never on the rest of the Heino Reader package.

Line numbers are *not* built in. They live in ``line_numbers.py`` as an
optional add-on that can be attached and detached at runtime.
"""

from __future__ import annotations

import re

from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QPalette, QTextCursor
from PySide6.QtWidgets import QPlainTextEdit, QWidget

from .highlighter import MarkdownHighlighter

QUOTE_BAR_WIDTH = 3

# Leading whitespace plus any quote and list markers, e.g. "  > - ".
_PREFIX_RE = re.compile(r"[ \t]*(?:>[ ]?|[-*+][ ]+|\d+[.)][ ]+)*")
# Lines shown with the quote bar: real blockquotes, i.e. a ">" after at most
# three spaces. Indented lines are code blocks in markdown, not quotes.
_QUOTE_LINE_RE = re.compile(r" {0,3}>")


def enter_indent(line: str) -> str:
    """Spaces that put the cursor under the first character of the text.

    Pressing Enter at the end of a line continues it at the column where
    its text begins, so indented blocks, quotes and list items keep their
    alignment.
    """
    match = _PREFIX_RE.match(line)
    prefix = match.group(0) if match else ""
    return " " * len(prefix.expandtabs(4))


def is_quote_line(line: str) -> bool:
    """True for blockquote lines (``>``), which get the left quote bar."""
    return bool(line.strip()) and _QUOTE_LINE_RE.match(line) is not None


class MarkdownSourceEdit(QPlainTextEdit):
    """Plain-text markdown editor with tab indenting and a quote bar.

    Tab / Shift+Tab indent or unindent the selected lines (all lines the
    selection touches). Without a selection Tab just moves the cursor.
    Line numbers are optional; see ``HeinoReader.editor.line_numbers``.
    """

    INDENT = "    "  # spaces, so files stay portable

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setTabStopDistance(
            self.fontMetrics().horizontalAdvance(self.INDENT)
        )
        self._highlighter = MarkdownHighlighter(self.document())

    @property
    def highlighter(self) -> MarkdownHighlighter:
        return self._highlighter

    # --------------------------------------------------------- quote bar

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        # Left quote bar on blockquote lines only.
        color = self.palette().color(QPalette.ColorRole.Mid)
        with QPainter(self.viewport()) as painter:
            block = self.firstVisibleBlock()
            top = round(self.blockBoundingGeometry(block).translated(
                self.contentOffset()).top())
            while block.isValid() and top <= self.viewport().height():
                height = round(self.blockBoundingRect(block).height())
                if block.isVisible() and is_quote_line(block.text()):
                    painter.fillRect(0, top, QUOTE_BAR_WIDTH, height, color)
                top += height
                block = block.next()

    # ------------------------------------------------------------- tabbing

    def keyPressEvent(self, event) -> None:
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            cursor = self.textCursor()
            cursor.insertText("\n" + enter_indent(cursor.block().text()))
            self.setTextCursor(cursor)
            return
        if event.key() in (Qt.Key.Key_Tab, Qt.Key.Key_Backtab):
            cursor = self.textCursor()
            if not cursor.hasSelection():
                if event.key() == Qt.Key.Key_Tab:
                    cursor.insertText(self.INDENT)
                    self.setTextCursor(cursor)
                return
            self._change_indent(
                cursor,
                unindent=event.key() == Qt.Key.Key_Backtab
                or bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier),
            )
            return
        super().keyPressEvent(event)

    def _change_indent(self, cursor: QTextCursor, unindent: bool) -> None:
        document = self.document()
        # findBlock() takes a position, findBlockByNumber() a block number.
        first = document.findBlock(cursor.selectionStart()).blockNumber()
        last = document.findBlock(cursor.selectionEnd()).blockNumber()
        # Rebuild the selection blockwise so no EOL characters get shifted.
        cursor.beginEditBlock()
        cursor.setPosition(document.findBlockByNumber(first).position())
        cursor.movePosition(
            QTextCursor.MoveOperation.EndOfBlock, QTextCursor.MoveMode.KeepAnchor
        )
        for number in range(first, last + 1):
            block = document.findBlockByNumber(number)
            if not block.isValid():
                break
            if unindent:
                text = block.text()
                strip = (
                    self.INDENT
                    if text.startswith(self.INDENT)
                    else " " * (len(text) - len(text.lstrip(" ")))
                )
                if strip:
                    edit = QTextCursor(block)
                    edit.movePosition(
                        QTextCursor.MoveOperation.Right,
                        QTextCursor.MoveMode.KeepAnchor,
                        len(strip),
                    )
                    edit.removeSelectedText()
            else:
                edit = QTextCursor(block)
                edit.insertText(self.INDENT)
            if number != last:
                cursor.movePosition(
                    QTextCursor.MoveOperation.NextBlock,
                    QTextCursor.MoveMode.KeepAnchor,
                )
        cursor.endEditBlock()
        self.setTextCursor(cursor)
