"""The source pane: markdown editor, line-number gutter and typing delay."""

from __future__ import annotations

from PySide6.QtCore import QTimer
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QSplitter

from .editor import LineNumberGutter, MarkdownSourceEdit
from .layout import DOCUMENT_MARGIN
from .render import preview_body_point_size

# Wait this long after the last keystroke before the preview re-renders. One
# render per short note is cheap, but a long document costs real time and
# typing does not need a fresh preview per character.
LIVE_PREVIEW_DELAY_MS = 200


class EditorPane:
    """The raw markdown editor, created on first use.

    A plain preview start never builds the editor, its syntax highlighter or
    its gutter; they appear with the first switch to edit mode.
    """

    def __init__(self, splitter: QSplitter, on_edited, on_history) -> None:
        self._splitter = splitter
        self._on_edited = on_edited
        self._on_history = on_history
        self.source: MarkdownSourceEdit | None = None
        self.gutter: LineNumberGutter | None = None
        self._scale = 1.0
        self.timer = QTimer()
        self.timer.setSingleShot(True)
        self.timer.setInterval(LIVE_PREVIEW_DELAY_MS)

    def ensure(self) -> MarkdownSourceEdit:
        """Create the editor and its gutter on first use."""
        if self.source is not None:
            return self.source
        source = MarkdownSourceEdit(self._splitter)
        source.setFont(
            QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        )
        source.document().setDocumentMargin(DOCUMENT_MARGIN)
        source.textChanged.connect(self._edited)
        source.undoAvailable.connect(self._on_history)
        source.redoAvailable.connect(self._on_history)
        self.gutter = LineNumberGutter(source)
        self._splitter.insertWidget(0, source)
        self.source = source
        # Follow the zoom that was set before the editor existed.
        source.set_text_point_size(preview_body_point_size() * self._scale)
        return source

    @property
    def text(self) -> str:
        """The current buffer, or an empty string before the editor exists."""
        return self.source.toPlainText() if self.source is not None else ""

    def set_text(self, text: str) -> None:
        """Replace the buffer without treating it as an edit."""
        if self.source is None:
            return
        self.source.blockSignals(True)
        self.source.setPlainText(text)
        self.source.blockSignals(False)

    def set_visible(self, visible: bool) -> None:
        if self.source is not None:
            self.source.setVisible(visible)

    def set_zoom(self, scale: float) -> None:
        """Give the source pane the preview's text size in its own font."""
        self._scale = scale
        if self.source is not None:
            self.source.set_text_point_size(preview_body_point_size() * scale)

    def apply_line_numbers(self, enabled: bool) -> None:
        """Show or hide the gutter; a no-op before the editor exists."""
        if self.gutter is None:
            return
        if enabled:
            self.gutter.install()
        else:
            self.gutter.uninstall()

    @property
    def can_undo(self) -> bool:
        return self.source is not None and self.source.document().isUndoAvailable()

    @property
    def can_redo(self) -> bool:
        return self.source is not None and self.source.document().isRedoAvailable()

    def undo(self) -> None:
        if self.source is not None:
            self.source.undo()

    def redo(self) -> None:
        if self.source is not None:
            self.source.redo()

    def clear_history(self) -> None:
        """Drop the undo stack, so a save does not undo into an older file."""
        if self.source is not None:
            self.source.document().clearUndoRedoStacks()

    def _edited(self) -> None:
        self._on_edited()
        self.timer.start()
