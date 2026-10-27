"""QTextEdit-based markdown preview (the default backend).

Qt's rich text engine supports only a small HTML/CSS subset: borders and
padding apply to table cells only, and block backgrounds repeat per line.
This backend is therefore a faster, lighter default; the WebEngine backend
in ``webview.py`` can be switched on for faithful rendering.
"""

from __future__ import annotations

import time
from pathlib import Path

from PySide6.QtCore import QPoint, Qt, QUrl
from PySide6.QtGui import (
    QFont,
    QFontInfo,
    QFontMetricsF,
    QImage,
    QPixmap,
    QTextBlockFormat,
    QTextCursor,
    QTextDocument,
    QTextImageFormat,
)
from PySide6.QtWidgets import QTextEdit, QWidget

from .images import RemoteImageLoader, is_remote, placeholder_image
from .layout import content_layout
from .render import (
    PREVIEW_CSS,
    _resolve_relative_paths,
    markdown_to_html,
    preview_body_point_size,
    preview_font_families,
    preview_line_height,
)
from .utils import open_external

_LINE_HEIGHT_PROPORTIONAL = QTextBlockFormat.LineHeightTypes.ProportionalHeight.value


def preview_font(scale: float = 1.0) -> QFont:
    """The document font for the preview at the given zoom level.

    A point size, not a pixel size: Qt scales points with the screen DPI, so
    the preview follows the desktop like every other Qt widget. Heading and
    inline sizes are left to Qt's own HTML scale, which is relative to this
    font and therefore scales with it.
    """
    font = QFont()
    families = preview_font_families()
    if families:
        font.setFamilies(families)
    font.setPointSizeF(preview_body_point_size() * scale)
    return font


class QtMarkdownView(QTextEdit):
    """Markdown preview rendered by Qt's rich-text engine."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setReadOnly(True)
        self.setMouseTracking(True)
        self.viewport().setMouseTracking(True)
        self._base_dir: Path | None = None
        self._press_pos: QPoint | None = None
        self._last_open: tuple[str, float] | None = None
        self._has_images = False
        self._fit_width = -1
        self._scale = 1.0
        self._remote_enabled = True
        self._remote = RemoteImageLoader(self)
        self._remote.loaded.connect(self._on_remote_loaded)
        self._remote.failed.connect(self._on_remote_failed)
        # preview.css styles colors, spacing and structure. Its typography
        # cannot come from a body rule here: setDefaultStyleSheet() never
        # matches one, because setHtml() parses a fragment without <body>.
        # The base font is therefore the document font, and the relative
        # heading sizes are Qt's own HTML scale.
        self.setFont(preview_font(self._scale))
        self.document().setDefaultFont(preview_font(self._scale))
        self.document().setDefaultStyleSheet(PREVIEW_CSS)

    # --------------------------------------------------------------- API

    @property
    def base_dir(self) -> Path | None:
        return self._base_dir

    @property
    def remote_images_enabled(self) -> bool:
        return self._remote_enabled

    def set_base_dir(self, base_dir: Path | None) -> None:
        self._base_dir = base_dir

    def set_markdown(self, text: str) -> None:
        """Show a markdown document, rendered by the rich-text engine."""
        if self._base_dir is not None:
            text = _resolve_relative_paths(text, self._base_dir)
        html = markdown_to_html(text, qt=True)
        self._has_images = "<img" in html
        self._fit_width = -1  # force a refit for the new content
        self.setHtml(html)
        self._apply_line_heights()
        self._apply_content_width()
        self._apply_remote_images()
        self._fit_images()

    def _apply_line_heights(self) -> None:
        """Give every block the line height its CSS rule asks for.

        Qt parses ``line-height`` into the block format but reads the value as
        a percentage of the font's *natural* line height, while CSS means it
        relative to the font *size*. The conversion factor between both comes
        from Qt's own metrics, so the same rule ends up at the same visual
        spacing as in the Web Engine backend.

        Blocks with no rule of their own — paragraphs, because a ``body`` rule
        never matches — fall back to the body line height. Qt ignores block
        line heights for single-line blocks, so the effect shows on wrapped
        paragraphs, which is where spacing matters.
        """
        document = self.document()
        font = document.defaultFont()
        natural = QFontMetricsF(font).height()
        pixel = QFontInfo(font).pixelSize()
        if natural <= 0 or pixel <= 0:
            return
        body = preview_line_height()
        heading = preview_line_height(heading=True)

        cursor = QTextCursor(document)
        cursor.beginEditBlock()
        while True:
            block_format = cursor.blockFormat()
            ratio = self._css_line_height(block_format, body, heading)
            if ratio is not None:
                percent = ratio * pixel / natural * 100
                block_format.setLineHeight(percent, _LINE_HEIGHT_PROPORTIONAL)
                cursor.setBlockFormat(block_format)
            if not cursor.movePosition(QTextCursor.MoveOperation.NextBlock):
                break
        cursor.endEditBlock()

    @staticmethod
    def _css_line_height(
        block_format: QTextBlockFormat,
        body: float | None,
        heading: float | None,
    ) -> float | None:
        """CSS line-height for a block: its own if it has one, else the body's."""
        if (
            int(block_format.lineHeightType()) == _LINE_HEIGHT_PROPORTIONAL
            and block_format.lineHeight() > 0
        ):
            return block_format.lineHeight() / 100
        return heading if block_format.headingLevel() else body

    def set_remote_images_enabled(self, enabled: bool) -> None:
        self._remote_enabled = enabled

    def set_zoom(self, scale: float) -> None:
        self._scale = scale
        font = preview_font(scale)
        self.setFont(font)
        self.document().setDefaultFont(font)
        self._refit()

    # ------------------------------------------------------------ layout

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._apply_content_width()
        self._fit_images()

    def _apply_content_width(self) -> int:
        """Centre the text column at MAX_CONTENT_WIDTH on wide windows."""
        content, margin = content_layout(self.viewport().width())
        if content <= 0:
            return 0
        frame = self.document().rootFrame()
        fmt = frame.frameFormat()
        if (
            round(fmt.leftMargin()) != margin
            or round(fmt.rightMargin()) != margin
        ):
            fmt.setLeftMargin(margin)
            fmt.setRightMargin(margin)
            frame.setFrameFormat(fmt)
        return content

    # ------------------------------------------------------ remote images

    def _apply_remote_images(self) -> None:
        """Attach cached, placeholder or in-flight resources for remote images."""
        document = self.document()
        block = document.begin()
        while block.isValid():
            iterator = block.begin()
            while not iterator.atEnd():
                fragment = iterator.fragment()
                if fragment.isValid() and fragment.charFormat().isImageFormat():
                    url = fragment.charFormat().toImageFormat().name()
                    if is_remote(url):
                        self._apply_remote_resource(url)
                iterator += 1
            block = block.next()

    def _apply_remote_resource(self, url: str) -> None:
        document = self.document()
        image = self._remote.cached(url)
        if image is not None:
            document.addResource(
                QTextDocument.ResourceType.ImageResource, QUrl(url), image
            )
            return
        document.addResource(
            QTextDocument.ResourceType.ImageResource,
            QUrl(url),
            placeholder_image(url),
        )
        if self._remote_enabled:
            self._remote.fetch(url)

    def _on_remote_loaded(self, url: str, image: QImage) -> None:
        self.document().addResource(
            QTextDocument.ResourceType.ImageResource, QUrl(url), image
        )
        self._refit()

    def _on_remote_failed(self, url: str) -> None:
        self.document().addResource(
            QTextDocument.ResourceType.ImageResource,
            QUrl(url),
            placeholder_image(url),
        )
        self._refit()

    # ------------------------------------------------------------- images

    def _refit(self) -> None:
        self._fit_width = -1
        self._fit_images()

    def _fit_images(self) -> None:
        """Scale oversized images down to the text column width."""
        if not self._has_images:
            return
        content, _ = content_layout(self.viewport().width())
        if content <= 0 or content == self._fit_width:
            return
        self._fit_width = content
        document = self.document()

        scroll = self.verticalScrollBar().value()
        changed = False
        block = document.begin()
        while block.isValid():
            iterator = block.begin()
            while not iterator.atEnd():
                fragment = iterator.fragment()
                if fragment.isValid() and fragment.charFormat().isImageFormat():
                    image = fragment.charFormat().toImageFormat()
                    if self._fit_image(document, image, content):
                        cursor = QTextCursor(document)
                        cursor.setPosition(fragment.position())
                        cursor.setPosition(
                            fragment.position() + fragment.length(),
                            QTextCursor.MoveMode.KeepAnchor,
                        )
                        cursor.setCharFormat(image)
                        changed = True
                iterator += 1
            block = block.next()
        if changed:
            self.verticalScrollBar().setValue(scroll)

    @staticmethod
    def _fit_image(
        document: QTextDocument, image: QTextImageFormat, available: int
    ) -> bool:
        """Give an oversized image a width that fits; return True if changed."""
        resource = document.resource(
            QTextDocument.ResourceType.ImageResource, QUrl(image.name())
        )
        if not isinstance(resource, (QPixmap, QImage)) or resource.isNull():
            return False
        width, height = resource.width(), resource.height()
        if width <= 0 or height <= 0:
            return False
        target = min(width, available)
        new_height = round(height * target / width)
        if (
            round(image.width()) == target
            and round(image.height()) == new_height
        ):
            return False
        image.setWidth(target)
        image.setHeight(new_height)
        return True

    # -------------------------------------------------------------- links

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._press_pos = event.position().toPoint()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        position = event.position().toPoint()
        super().mouseMoveEvent(event)
        href = self._anchor_href(position)
        if href:
            self.setCursor(Qt.CursorShape.PointingHandCursor)
            self.setToolTip(href)
        else:
            self.setCursor(Qt.CursorShape.IBeamCursor)
            self.setToolTip("")

    def mouseReleaseEvent(self, event) -> None:
        super().mouseReleaseEvent(event)
        if event.button() != Qt.MouseButton.LeftButton or self._press_pos is None:
            return
        release_pos = event.position().toPoint()
        moved = (release_pos - self._press_pos).manhattanLength()
        self._press_pos = None
        if moved > 4:  # a selection drag, not a click
            return
        url = self._link_url(self._anchor_href(release_pos))
        if url is None:
            return
        now = time.monotonic()
        if (
            self._last_open is not None
            and self._last_open[0] == url.toString()
            and now - self._last_open[1] < 0.4
        ):
            return
        self._last_open = (url.toString(), now)
        open_external(url)

    def _anchor_href(self, position: QPoint) -> str:
        """Return the link target under the given position, or an empty string."""
        cursor = self.cursorForPosition(position)
        href = cursor.charFormat().anchorHref()
        if not href:
            neighbor = QTextCursor(cursor)
            neighbor.movePosition(QTextCursor.MoveOperation.Right)
            href = neighbor.charFormat().anchorHref()
        return href

    def _link_url(self, href: str) -> QUrl | None:
        """Turn an anchor target into a URL that xdg-open can handle."""
        if not href or href.startswith("#"):
            return None
        url = QUrl(href)
        if url.scheme():
            return url
        if self._base_dir is not None:
            return QUrl.fromLocalFile(str((self._base_dir / href).resolve()))
        if href.startswith("/"):
            return QUrl.fromLocalFile(href)
        return None
