"""Remote image loading and a visible placeholder for unavailable images.

Used by the QTextEdit backend: Qt's text engine never fetches ``http(s)``
images on its own, so they are downloaded asynchronously and a placeholder
is drawn when loading is disabled or fails. The WebEngine backend loads
images natively and does not need this module.
"""

from __future__ import annotations

from PySide6.QtCore import QByteArray, QObject, QRect, Qt, QUrl, Signal
from PySide6.QtGui import QColor, QFont, QFontMetrics, QImage, QPainter, QPen
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest
from PySide6.QtSvg import QSvgRenderer

REMOTE_SCHEMES = ("http://", "https://")


def is_remote(url: str) -> bool:
    """True for image URLs that have to be downloaded."""
    return url.startswith(REMOTE_SCHEMES)


def svg_to_image(data: bytes) -> QImage:
    """Render SVG bytes to an image; QImage cannot decode SVG on its own.

    Badges (shields.io and friends) are SVG, so without this fallback the
    Qt backend could only ever show their "image unavailable" placeholder.
    QSvgRenderer draws statically, so remote SVGs cannot run scripts.
    """
    renderer = QSvgRenderer(QByteArray(data))
    if not renderer.isValid():
        return QImage()
    size = renderer.defaultSize()
    if size.isEmpty():
        size = renderer.viewBoxF().size().toSize()
    if size.isEmpty():
        return QImage()
    image = QImage(size, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    renderer.render(painter)
    painter.end()
    return image


def placeholder_image(url: str, width: int = 420, height: int = 96) -> QImage:
    """A visible "image unavailable" box used in place of a missing image."""
    image = QImage(width, height, QImage.Format.Format_ARGB32)
    image.fill(QColor("#f2f2f2"))

    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    border = QPen(QColor("#c8c8c8"))
    border.setStyle(Qt.PenStyle.DashLine)
    painter.setPen(border)
    painter.drawRect(1, 1, width - 3, height - 3)

    icon = QRect(16, 26, 44, 44)
    painter.setPen(QColor("#9a9a9a"))
    painter.drawRect(icon)
    painter.drawLine(icon.topLeft(), icon.bottomRight())
    painter.drawLine(icon.topRight(), icon.bottomLeft())

    text_left = icon.right() + 16
    title = QFont(painter.font())
    title.setPointSize(11)
    title.setBold(True)
    painter.setFont(title)
    painter.setPen(QColor("#555555"))
    painter.drawText(
        QRect(text_left, 16, width - text_left - 16, 24),
        Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
        "Image unavailable",
    )

    detail = QFont(painter.font())
    detail.setPointSize(9)
    detail.setBold(False)
    painter.setFont(detail)
    painter.setPen(QColor("#808080"))
    metrics = QFontMetrics(detail)
    source = metrics.elidedText(
        url or "unknown source", Qt.TextElideMode.ElideMiddle, width - text_left - 32
    )
    painter.drawText(
        QRect(text_left, 44, width - text_left - 16, 20),
        Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
        source,
    )
    painter.end()
    return image


class RemoteImageLoader(QObject):
    """Download remote images asynchronously and cache them in memory."""

    loaded = Signal(str, QImage)
    failed = Signal(str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._manager = QNetworkAccessManager(self)
        self._cache: dict[str, QImage] = {}
        self._pending: set[str] = set()

    def cached(self, url: str) -> QImage | None:
        return self._cache.get(url)

    def is_pending(self, url: str) -> bool:
        return url in self._pending

    def fetch(self, url: str) -> None:
        """Start downloading ``url`` unless cached or already in flight."""
        if url in self._cache or url in self._pending:
            return
        self._pending.add(url)
        request = QNetworkRequest(QUrl(url))
        request.setAttribute(
            QNetworkRequest.Attribute.RedirectPolicyAttribute,
            QNetworkRequest.RedirectPolicy.NoLessSafeRedirectPolicy,
        )
        request.setHeader(QNetworkRequest.KnownHeaders.UserAgentHeader, "heinoreader")
        reply = self._manager.get(request)
        reply.finished.connect(lambda r=reply, u=url: self._finished(r, u))

    def _finished(self, reply: QNetworkReply, url: str) -> None:
        self._pending.discard(url)
        ok = reply.error() == QNetworkReply.NetworkError.NoError
        data = bytes(reply.readAll()) if ok else b""
        reply.deleteLater()
        image = QImage()
        if data and not image.loadFromData(data):
            image = svg_to_image(data)
        if image.isNull():
            self.failed.emit(url)
        else:
            self._cache[url] = image
            self.loaded.emit(url, image)
