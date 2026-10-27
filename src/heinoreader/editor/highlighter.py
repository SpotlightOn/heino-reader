"""Lightweight markdown syntax highlighting for the source editor.

This module is self-contained: it depends only on Qt and the re module,
never on the rest of the heinoreader package.
"""

from __future__ import annotations

import re

from PySide6.QtGui import (
    QColor,
    QFont,
    QFontDatabase,
    QPalette,
    QSyntaxHighlighter,
    QTextCharFormat,
    QTextDocument,
)
from PySide6.QtWidgets import QApplication

_FACTORS = {1: 1.6, 2: 1.4, 3: 1.2, 4: 1.1, 5: 1.0, 6: 0.9}

# Per-block state marking "inside a fenced code block".
_STATE_CODE = 1

_FENCE_RE = re.compile(r"^\s*(`{3,}|~{3,})")
_INLINE_CODE_RE = re.compile(r"`[^`\n]+`")


def _blend(base: QColor, toward: QColor, amount: float) -> QColor:
    """Mix ``base`` toward ``toward`` by ``amount`` (0..1).

    Used to derive a code background that stays readable in both light
    and dark themes, instead of a hard-coded grey.
    """
    return QColor(
        round(base.red() * (1 - amount) + toward.red() * amount),
        round(base.green() * (1 - amount) + toward.green() * amount),
        round(base.blue() * (1 - amount) + toward.blue() * amount),
    )


class MarkdownHighlighter(QSyntaxHighlighter):
    """Highlight markdown syntax directly inside the plain-text editor."""

    def __init__(self, parent: QTextDocument) -> None:
        super().__init__(parent)
        app = QApplication.instance()
        base = app.palette() if app is not None else QPalette()
        text = base.color(QPalette.ColorRole.Text)
        dim = base.color(QPalette.ColorRole.PlaceholderText)
        accent = base.color(QPalette.ColorRole.Link)

        def fmt(color=None, *, bold=False, italic=False, background=None):
            result = QTextCharFormat()
            if color is not None:
                result.setForeground(color)
            if background is not None:
                result.setBackground(background)
            if bold:
                result.setFontWeight(QFont.Weight.Bold)
            if italic:
                result.setFontItalic(True)
            return result

        # Code (inline spans and fenced blocks): monospace on a subtly
        # tinted background derived from the palette.
        self._code_format = QTextCharFormat()
        self._code_format.setBackground(
            _blend(
                base.color(QPalette.ColorRole.Base),
                base.color(QPalette.ColorRole.Text),
                0.15,
            )
        )
        self._code_format.setFont(
            QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        )

        self._rules = [
            # ATX headings: larger bold text, size scaled by level.
            (r"^#{1,6} .+$", fmt(text, bold=True), 0),
            # Bold / italic / bold-italic.
            (r"\*\*[^*\n]+\*\*", fmt(text, bold=True), 0),
            (r"__[^_\n]+__", fmt(text, bold=True), 0),
            (r"\*[^*\n]+\*", fmt(italic=True), 0),
            (r"\[[^\]\n]*\]\([^)\n]+\)", fmt(accent), 0),
            (r"^\s*([-*+]|\d+\.) ", fmt(dim), 0),
            (r"^\s*> ", fmt(dim), 0),
        ]
        self._compiled = [(re.compile(p), f) for p, f, _ in self._rules]
        self._heading = re.compile(r"^(#{1,6}) ")

    def highlightBlock(self, text: str) -> None:
        inside = self.previousBlockState() == _STATE_CODE
        fence = _FENCE_RE.match(text)

        if fence:
            # A fence delimiter line is code and toggles the block state.
            self.setFormat(0, len(text), self._code_format)
            self.setCurrentBlockState(0 if inside else _STATE_CODE)
            return
        if inside:
            # Body of a fenced block: the whole line is code, and no
            # other rule (bold, list, ...) may fire inside it.
            self.setFormat(0, len(text), self._code_format)
            self.setCurrentBlockState(_STATE_CODE)
            return
        self.setCurrentBlockState(0)

        for pattern, fmt in self._compiled:
            for match in pattern.finditer(text):
                self.setFormat(match.start(), match.end() - match.start(), fmt)

        # Inline code last, so it wins over bold/italic within the span.
        for match in _INLINE_CODE_RE.finditer(text):
            self.setFormat(
                match.start(), match.end() - match.start(), self._code_format
            )

        heading = self._heading.match(text)
        if heading:
            # Scale the size with the heading level, like the preview does.
            size = QFontDatabase.systemFont(
                QFontDatabase.SystemFont.FixedFont
            ).pointSizeF()
            if size > 0:
                fmt = QTextCharFormat(self.format(0))
                fmt.setFontWeight(QFont.Weight.Bold)
                fmt.setFontPointSize(size * _FACTORS[len(heading.group(1))])
                self.setFormat(0, len(text), fmt)
