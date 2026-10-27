"""QtWebEngine-based markdown preview (opt-in, full HTML/CSS fidelity).

This module is imported lazily: selecting the web preview is what loads
Chromium, so a Qt-rendered start never pays for it.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, QUrl
from PySide6.QtGui import QColor
from PySide6.QtWebEngineCore import (
    QWebEnginePage,
    QWebEngineProfile,
    QWebEngineSettings,
    QWebEngineUrlRequestInfo,
    QWebEngineUrlRequestInterceptor,
)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QWidget

from .render import render_html_document
from .utils import open_external


class MarkdownPage(QWebEnginePage):
    """Web page that sends link clicks to the system handler."""

    def acceptNavigationRequest(
        self, url, nav_type, is_main_frame
    ):
        if nav_type == QWebEnginePage.NavigationType.NavigationTypeLinkClicked:
            open_external(url)
            return False
        return super().acceptNavigationRequest(url, nav_type, is_main_frame)


class RemoteImageFilter(QWebEngineUrlRequestInterceptor):
    """Blocks http(s) image requests when remote images are disabled."""

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.enabled = True

    def interceptRequest(self, info) -> None:
        if self.enabled:
            return
        if (
            info.resourceType()
            == QWebEngineUrlRequestInfo.ResourceType.ResourceTypeImage
            and info.requestUrl().scheme() in ("http", "https")
        ):
            info.block(True)


class WebMarkdownView(QWebEngineView):
    """Render the markdown document as HTML in a real HTML engine.

    QTextDocument only supports a small CSS subset (borders and padding
    work on table cells only, and block backgrounds repeat per line), so a
    Chromium view is used for a faithful preview. The look lives in
    ``preview.css``.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._base_dir: Path | None = None
        self._profile = QWebEngineProfile(self)
        self._image_filter = RemoteImageFilter(self)
        self._profile.setUrlRequestInterceptor(self._image_filter)
        self._page = MarkdownPage(self._profile, self)
        self._page.setBackgroundColor(QColor("#ffffff"))
        self.setPage(self._page)

        settings = self._page.settings()
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True
        )
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True
        )
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.JavascriptEnabled, False
        )

    @property
    def base_dir(self) -> Path | None:
        return self._base_dir

    @property
    def remote_images_enabled(self) -> bool:
        return self._image_filter.enabled

    def set_base_dir(self, base_dir: Path | None) -> None:
        """Set the directory used to resolve relative links and images."""
        self._base_dir = base_dir

    def set_markdown(self, text: str) -> None:
        """Show a markdown document, rendered as HTML by the web engine."""
        base = (
            QUrl.fromLocalFile(str(self._base_dir) + "/")
            if self._base_dir is not None
            else QUrl("about:blank")
        )
        self.setHtml(render_html_document(text), base)

    def set_remote_images_enabled(self, enabled: bool) -> None:
        self._image_filter.enabled = enabled

    def set_zoom(self, scale: float) -> None:
        self.setZoomFactor(scale)
