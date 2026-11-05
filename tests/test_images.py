"""Tests for image handling and the text column in both renderers."""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import QByteArray, QObject, QUrl, Signal
from PySide6.QtGui import QColor, QImage, QTextDocument, QTextImageFormat
from PySide6.QtNetwork import QNetworkReply
from PySide6.QtWebEngineCore import QWebEngineUrlRequestInfo
from PySide6.QtWidgets import QApplication

from HeinoReader.layout import (
    DOCUMENT_MARGIN,
    MAX_CONTENT_WIDTH,
    VERTICAL_MARGIN_MAX,
    VERTICAL_MARGIN_MIN,
    content_layout,
    vertical_margins,
)
from HeinoReader.viewer import RENDERER_QT, RENDERER_WEB
from HeinoReader.viewer.images import RemoteImageLoader, placeholder_image, svg_to_image
from HeinoReader.viewer.qt import QtMarkdownView
from HeinoReader.viewer.render import (
    DOCUMENT_CSS,
    markdown_to_html,
    render_html_document,
)
from HeinoReader.viewer.web import RemoteImageFilter
from HeinoReader.window import ViewerWindow


def make_image(path, width, height):
    image = QImage(width, height, QImage.Format.Format_RGB32)
    image.fill(QColor("#336699"))
    assert image.save(str(path))


@pytest.fixture
def image_doc(tmp_path):
    make_image(tmp_path / "big.png", 1600, 800)
    make_image(tmp_path / "small.png", 120, 60)
    doc = tmp_path / "doc.md"
    doc.write_text(
        "# Images\n\n"
        "Before.\n\n"
        "![big](big.png)\n\n"
        "![small](small.png)\n\n"
        "After.\n",
        encoding="utf-8",
    )
    return doc


def make_window(qtbot, doc, renderer):
    window = ViewerWindow(doc, renderer=renderer)
    qtbot.addWidget(window)
    window.show()
    QApplication.processEvents()
    return window


@pytest.fixture
def qt_window(qtbot, image_doc):
    return make_window(qtbot, image_doc, RENDERER_QT)


@pytest.fixture
def web_window(qtbot, image_doc):
    return make_window(qtbot, image_doc, RENDERER_WEB)


# ------------------------------------------------------- QTextEdit backend

def image_formats(window):
    """Map image file name -> (width, height) for every image in the document."""
    found = {}
    block = window.viewer.document().begin()
    while block.isValid():
        it = block.begin()
        while not it.atEnd():
            fragment = it.fragment()
            if fragment.isValid() and fragment.charFormat().isImageFormat():
                image = fragment.charFormat().toImageFormat()
                found[Path(image.name()).name] = (image.width(), image.height())
            it += 1
        block = block.next()
    return found


def available_width(window):
    content, _ = content_layout(window.viewer.viewport().width())
    return content


def test_qt_oversized_image_is_scaled_to_the_available_width(qt_window):
    width, height = image_formats(qt_window)["big.png"]
    assert 0 < width <= available_width(qt_window)
    assert abs(height - width / 2) <= 1  # 1600x800 source keeps 2:1


def test_qt_small_image_is_not_upscaled(qt_window):
    assert image_formats(qt_window)["small.png"] == (120, 60)


def test_qt_document_does_not_overflow_the_viewport(qt_window):
    document = qt_window.viewer.document()
    assert document.size().width() <= qt_window.viewer.viewport().width() + 1
    assert qt_window.viewer.horizontalScrollBar().maximum() == 0


def test_qt_images_refit_when_the_window_shrinks(qtbot, qt_window):
    before, _ = image_formats(qt_window)["big.png"]
    qt_window.resize(420, 700)
    QApplication.processEvents()
    after, height = image_formats(qt_window)["big.png"]
    assert after < before
    assert 0 < after <= available_width(qt_window)
    assert abs(height - after / 2) <= 1


# ------------------------------------------------------- WebEngine backend

def test_theme_limits_image_width():
    assert "max-width: 100%" in DOCUMENT_CSS


def test_web_document_keeps_the_relative_image_source(web_window):
    html = markdown_to_html(web_window.document.markdown)
    assert 'src="big.png"' in html


def test_web_renderer_resolves_relative_images_via_the_base_dir(web_window, tmp_path):
    assert web_window.viewer.base_dir == tmp_path


def test_web_document_contains_the_theme(web_window):
    document = render_html_document(web_window.document.markdown)
    assert "<style>" in document
    assert "max-width: 100%" in document
    assert "<img" in document


# ------------------------------------------------------------ column width

def test_content_layout_caps_and_centres_wide_windows():
    content, margin = content_layout(1400)
    assert content == MAX_CONTENT_WIDTH
    assert margin > DOCUMENT_MARGIN


def test_content_layout_uses_full_width_on_narrow_windows():
    content, margin = content_layout(600)
    assert content == 600 - 2 * DOCUMENT_MARGIN
    assert margin == DOCUMENT_MARGIN


def test_content_layout_handles_zero_width():
    assert content_layout(0) == (0, int(DOCUMENT_MARGIN))


def test_vertical_margins_grow_with_the_window_height():
    small, _ = vertical_margins(400)
    large, _ = vertical_margins(1400)
    assert small == VERTICAL_MARGIN_MIN
    assert large > small


def test_vertical_margins_stop_at_their_maximum():
    assert vertical_margins(10000) == (VERTICAL_MARGIN_MAX, VERTICAL_MARGIN_MAX)


def test_vertical_margins_are_larger_than_the_side_margin():
    top, bottom = vertical_margins(600)
    assert top > DOCUMENT_MARGIN
    assert bottom == top


def test_vertical_margins_handle_zero_height():
    assert vertical_margins(0) == (VERTICAL_MARGIN_MIN, VERTICAL_MARGIN_MIN)


def test_web_theme_scales_its_vertical_padding_with_the_viewport():
    assert "max(32px, 6vh)" in DOCUMENT_CSS


def test_qt_viewer_sets_the_side_margin_from_the_layout(qt_window):
    _, margin = content_layout(qt_window.viewer.viewport().width())
    frame_format = qt_window.viewer.document().rootFrame().frameFormat()
    assert round(frame_format.leftMargin()) == margin
    assert round(frame_format.rightMargin()) == margin


def test_qt_viewer_leaves_more_room_above_and_below_than_at_the_sides(
    qt_window,
):
    """The first and last line must not touch the window edge."""
    view = qt_window.viewer
    top, bottom = vertical_margins(view.viewport().height())
    frame_format = view.document().rootFrame().frameFormat()
    assert round(frame_format.topMargin()) == top
    assert round(frame_format.bottomMargin()) == bottom
    assert top > DOCUMENT_MARGIN


def test_qt_vertical_margin_follows_the_window_height(qtbot, image_doc):
    """A taller window gets more air above and below the text."""
    window = ViewerWindow(image_doc, renderer=RENDERER_QT)
    qtbot.addWidget(window)
    window.resize(700, 400)
    window.show()
    QApplication.processEvents()
    small = window.viewer.document().rootFrame().frameFormat().topMargin()

    window.resize(700, 1200)
    QApplication.processEvents()
    large = window.viewer.document().rootFrame().frameFormat().topMargin()

    assert large > small


# ------------------------------------------------------------ remote images

SVG_BADGE = (
    b'<svg xmlns="http://www.w3.org/2000/svg" width="120" height="20">'
    b'<rect width="120" height="20" fill="#00aa00"/></svg>'
)


def test_svg_bytes_are_rendered_to_an_image(qapp):
    image = svg_to_image(SVG_BADGE)
    assert not image.isNull()
    assert (image.width(), image.height()) == (120, 20)


def test_svg_without_intrinsic_size_uses_its_viewbox(qapp):
    svg = (
        b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 80 24">'
        b'<rect width="80" height="24"/></svg>'
    )
    image = svg_to_image(svg)
    assert (image.width(), image.height()) == (80, 24)


def test_broken_svg_yields_no_image(qapp):
    assert svg_to_image(b"not an svg").isNull()


class FakeSvgReply:
    """Minimal QNetworkReply stand-in for a downloaded SVG badge."""

    def error(self):
        return QNetworkReply.NetworkError.NoError

    def readAll(self):
        return QByteArray(SVG_BADGE)

    def deleteLater(self):
        pass


def test_remote_svg_is_decoded_and_cached(qapp):
    loader = RemoteImageLoader()
    url = "https://example.org/badge.svg"
    loader._pending.add(url)

    loader._finished(FakeSvgReply(), url)

    cached = loader.cached(url)
    assert cached is not None and not cached.isNull()
    assert (cached.width(), cached.height()) == (120, 20)


def test_svg_without_any_size_yields_no_image(qapp):
    svg = b'<svg xmlns="http://www.w3.org/2000/svg"></svg>'
    assert svg_to_image(svg).isNull()


# ------------------------------------------------------------- placeholders

def test_placeholder_image_is_a_visible_box(qapp):
    image = placeholder_image("https://example.org/big.png")
    assert not image.isNull()
    assert (image.width(), image.height()) == (420, 96)


def test_placeholder_image_without_a_source(qapp):
    assert not placeholder_image("").isNull()


class FakeReply(QObject):
    """Stand-in for QNetworkReply: only the signal and lifetime are needed."""

    finished = Signal()

    def error(self):
        return QNetworkReply.NetworkError.NoError

    def readAll(self):
        return QByteArray(b"not an image")

    def deleteLater(self):
        pass


class FakeManager:
    def __init__(self) -> None:
        self.urls = []

    def get(self, request):
        self.urls.append(request.url().toString())
        return FakeReply()


def test_fetch_requests_each_url_once(qapp):
    loader = RemoteImageLoader()
    manager = FakeManager()
    loader._manager = manager
    url = "https://example.org/badge.svg"

    loader.fetch(url)
    loader.fetch(url)

    assert manager.urls == [url]
    assert loader.is_pending(url) is True
    assert loader.cached(url) is None


def test_undecodable_download_emits_failure(qapp):
    loader = RemoteImageLoader()
    url = "https://example.org/broken.png"
    loader._pending.add(url)
    failures = []
    loader.failed.connect(failures.append)

    loader._finished(FakeReply(), url)

    assert failures == [url]
    assert loader.cached(url) is None


# ------------------------------------------- Qt backend: remote image state

class RecordingLoader:
    """Stand-in for RemoteImageLoader: no network, records requests."""

    def __init__(self, cached=None):
        self.fetched = []
        self.store = dict(cached or {})

    def cached(self, url):
        return self.store.get(url)

    def fetch(self, url):
        self.fetched.append(url)


def make_remote_view(qtbot, url, loader, *, enabled=True):
    view = QtMarkdownView()
    qtbot.addWidget(view)
    view.resize(500, 300)
    view._remote = loader
    view.set_remote_images_enabled(enabled)
    view.set_markdown(f"![alt]({url})")
    view.show()
    QApplication.processEvents()
    return view


def image_resource(view, url):
    return view.document().resource(
        QTextDocument.ResourceType.ImageResource, QUrl(url)
    )


def test_qt_remote_image_shows_a_placeholder_and_requests_it(qtbot):
    url = "https://example.org/badge.png"
    loader = RecordingLoader()

    view = make_remote_view(qtbot, url, loader)

    placeholder = image_resource(view, url)
    assert isinstance(placeholder, QImage) and not placeholder.isNull()
    assert loader.fetched == [url]


def test_qt_remote_image_from_the_cache_is_not_requested_again(qtbot):
    url = "https://example.org/badge.png"
    cached = QImage(20, 10, QImage.Format.Format_ARGB32)
    loader = RecordingLoader({url: cached})

    view = make_remote_view(qtbot, url, loader)

    assert loader.fetched == []
    assert image_resource(view, url).size() == cached.size()


def test_qt_remote_image_is_not_requested_while_disabled(qtbot):
    url = "https://example.org/badge.png"
    loader = RecordingLoader()

    view = make_remote_view(qtbot, url, loader, enabled=False)

    assert loader.fetched == []
    assert not image_resource(view, url).isNull()


def test_qt_remote_image_replaces_the_placeholder_when_it_arrives(qtbot):
    url = "https://example.org/badge.png"
    loader = RecordingLoader()
    view = make_remote_view(qtbot, url, loader)
    downloaded = QImage(40, 20, QImage.Format.Format_ARGB32)

    view._on_remote_loaded(url, downloaded)
    QApplication.processEvents()

    assert image_resource(view, url).size() == downloaded.size()


def test_qt_remote_image_falls_back_to_the_placeholder_on_failure(qtbot):
    url = "https://example.org/badge.png"
    loader = RecordingLoader()
    view = make_remote_view(qtbot, url, loader)

    view._on_remote_failed(url)
    QApplication.processEvents()

    assert not image_resource(view, url).isNull()


def test_qt_image_without_a_resource_is_not_scaled(qtbot, image_doc):
    window = ViewerWindow(image_doc)
    qtbot.addWidget(window)
    view = window.viewer
    image = QTextImageFormat()
    image.setName("missing.png")

    assert view._fit_image(view.document(), image, 100) is False


# -------------------------------------------------- WebEngine: image filter

class FakeRequestInfo:
    """Duck-typed QWebEngineUrlRequestInfo; the real one cannot be built."""

    def __init__(self, resource_type, url):
        self._type = resource_type
        self._url = QUrl(url)
        self.blocked = None

    def resourceType(self):
        return self._type

    def requestUrl(self):
        return self._url

    def block(self, flag):
        self.blocked = flag


def request_info(resource_type, url):
    return FakeRequestInfo(resource_type, url)


IMAGE = QWebEngineUrlRequestInfo.ResourceType.ResourceTypeImage
STYLESHEET = QWebEngineUrlRequestInfo.ResourceType.ResourceTypeStylesheet


def test_web_image_filter_blocks_remote_images_only_when_disabled():
    filter_ = RemoteImageFilter()
    info = request_info(IMAGE, "https://example.org/badge.png")

    filter_.interceptRequest(info)
    assert info.blocked is None  # enabled by default

    filter_.enabled = False
    filter_.interceptRequest(info)
    assert info.blocked is True


def test_web_image_filter_leaves_local_images_and_other_requests_alone():
    filter_ = RemoteImageFilter()
    filter_.enabled = False
    local = request_info(IMAGE, "file:///tmp/badge.png")
    stylesheet = request_info(STYLESHEET, "https://example.org/theme.css")

    filter_.interceptRequest(local)
    filter_.interceptRequest(stylesheet)

    assert local.blocked is None
    assert stylesheet.blocked is None
