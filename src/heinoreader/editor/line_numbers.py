"""Optional line-number gutter for the markdown source editor.

Line numbers are an add-on, not a built-in feature: the editor works
without them. Attach the gutter with ``LineNumberGutter(editor).install()``
and remove it again with ``uninstall()``. This keeps the core editor
simple and lets the line numbers be switched on or off at runtime.

Self-contained: depends only on Qt.
"""

from __future__ import annotations

from PySide6.QtCore import QEvent, QObject, QRect, QSize, Qt
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QPlainTextEdit, QWidget


class LineNumberArea(QWidget):
    """Gutter that paints the line numbers of a QPlainTextEdit."""

    def __init__(self, gutter: LineNumberGutter) -> None:
        super().__init__(gutter.editor)
        self._gutter = gutter

    def sizeHint(self) -> QSize:
        return QSize(self._gutter.area_width(), 0)

    def paintEvent(self, event) -> None:
        self._gutter.paint(event)


class LineNumberGutter(QObject):
    """Manage the optional line-number gutter of an editor.

    The gutter owns the state and the signal connections, so removing it
    leaves the editor exactly as it was before installation.
    """

    def __init__(self, editor: QPlainTextEdit) -> None:
        super().__init__(editor)
        self._editor = editor
        self._area = LineNumberArea(self)
        self._area.hide()
        self._installed = False

    @property
    def editor(self) -> QPlainTextEdit:
        return self._editor

    @property
    def area(self) -> LineNumberArea:
        return self._area

    @property
    def installed(self) -> bool:
        return self._installed

    # --------------------------------------------------------- lifecycle

    def install(self) -> None:
        """Show the gutter and keep it in sync with the editor."""
        if self._installed:
            return
        self._installed = True
        self._area.show()
        self._editor.blockCountChanged.connect(self._update_margin)
        self._editor.updateRequest.connect(self._on_update_request)
        self._editor.destroyed.connect(self._on_editor_destroyed)
        self._editor.installEventFilter(self)
        self._update_margin()
        self._update_geometry()

    def uninstall(self) -> None:
        """Hide the gutter and disconnect every signal again."""
        if not self._installed:
            return
        self._installed = False
        self._editor.blockCountChanged.disconnect(self._update_margin)
        self._editor.updateRequest.disconnect(self._on_update_request)
        self._editor.destroyed.disconnect(self._on_editor_destroyed)
        self._editor.removeEventFilter(self)
        self._area.hide()
        self._editor.setViewportMargins(0, 0, 0, 0)

    def eventFilter(self, watched, event) -> bool:
        if watched is self._editor and event.type() == QEvent.Type.Resize:
            self._update_geometry()
        return False

    def toggle(self) -> bool:
        """Flip the gutter and return whether it is now installed."""
        self.uninstall() if self._installed else self.install()
        return self._installed

    # ------------------------------------------------------------- width

    def area_width(self) -> int:
        digits = len(str(max(self._editor.blockCount(), 1)))
        return 8 + self._editor.fontMetrics().horizontalAdvance("9") * digits

    # ------------------------------------------------------------ update

    def _update_margin(self) -> None:
        self._editor.setViewportMargins(self.area_width(), 0, 0, 0)

    def _update_geometry(self) -> None:
        cr = self._editor.contentsRect()
        self._area.setGeometry(
            QRect(cr.left(), cr.top(), self.area_width(), cr.height())
        )

    def _on_update_request(self, rect: QRect, dy: int) -> None:
        if dy:
            self._area.scroll(0, dy)
        else:
            self._area.update(0, rect.y(), self._area.width(), rect.height())
        if rect.contains(self._editor.viewport().rect()):
            self._update_margin()
            self._update_geometry()

    def _on_editor_destroyed(self) -> None:
        self._installed = False

    # -------------------------------------------------------------- paint

    def paint(self, event) -> None:
        editor = self._editor
        painter = QPainter(self._area)
        painter.fillRect(event.rect(), editor.palette().alternateBase().color())
        block = editor.firstVisibleBlock()
        number = block.blockNumber()
        top = round(editor.blockBoundingGeometry(block).translated(
            editor.contentOffset()).top())
        bottom = top + round(editor.blockBoundingRect(block).height())
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                painter.setPen(editor.palette().placeholderText().color())
                painter.drawText(
                    0,
                    top,
                    self._area.width() - 4,
                    editor.fontMetrics().height(),
                    Qt.AlignmentFlag.AlignRight,
                    str(number + 1),
                )
            block = block.next()
            top = bottom
            bottom = top + round(editor.blockBoundingRect(block).height())
            number += 1
