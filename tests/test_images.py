"""Tests for image handling and the text column in both preview backends."""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import QByteArray
from PySide6.QtGui import QColor, QImage
from PySide6.QtNetwork import QNetworkReply
from PySide6.QtWidgets import QApplication

import heinoreader
from heinoreader import ViewerWindow
from heinoreader.images import RemoteImageLoader, svg_to_image


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
    return make_window(qtbot, image_doc, heinoreader.RENDERER_QT)


@pytest.fixture
def web_window(qtbot, image_doc):
    return make_window(qtbot, image_doc, heinoreader.RENDERER_WEB)


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
    content, _ = heinoreader.content_layout(window.viewer.viewport().width())
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
    assert "max-width: 100%" in heinoreader.PREVIEW_CSS


def test_web_document_keeps_the_relative_image_source(web_window):
    html = heinoreader.markdown_to_html(web_window._markdown)
    assert 'src="big.png"' in html


def test_web_preview_resolves_relative_images_via_the_base_dir(web_window, tmp_path):
    assert web_window.viewer.base_dir == tmp_path


def test_web_document_contains_the_theme(web_window):
    document = heinoreader.render_html_document(web_window._markdown)
    assert "<style>" in document
    assert "max-width: 100%" in document
    assert "<img" in document


# ------------------------------------------------------------ column width

def test_content_layout_caps_and_centres_wide_windows():
    content, margin = heinoreader.content_layout(1400)
    assert content == heinoreader.MAX_CONTENT_WIDTH
    assert margin > heinoreader.DOCUMENT_MARGIN


def test_content_layout_uses_full_width_on_narrow_windows():
    content, margin = heinoreader.content_layout(600)
    assert content == 600 - 2 * heinoreader.DOCUMENT_MARGIN
    assert margin == heinoreader.DOCUMENT_MARGIN


def test_content_layout_handles_zero_width():
    assert heinoreader.content_layout(0) == (0, int(heinoreader.DOCUMENT_MARGIN))


def test_qt_preview_sets_the_side_margin_from_the_layout(qt_window):
    _, margin = heinoreader.content_layout(qt_window.viewer.viewport().width())
    frame_format = qt_window.viewer.document().rootFrame().frameFormat()
    assert round(frame_format.leftMargin()) == margin
    assert round(frame_format.rightMargin()) == margin


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
