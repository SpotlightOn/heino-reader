"""Tests for the Qt backend's typography.

preview.css is shared with the WebEngine backend, so its body rule keeps CSS
pixels. The Qt backend converts that one value to points, because Qt scales
points with the screen DPI while CSS pixel sizes stay DPI blind inside
QTextDocument. Everything else (heading scale, emphasis) is Qt's own.
"""

from __future__ import annotations

import pytest
from PySide6.QtGui import QFontMetricsF
from PySide6.QtWidgets import QApplication

import HeinoReader
from HeinoReader.qtview import QtMarkdownView, preview_font


@pytest.fixture
def view(qtbot):
    view = QtMarkdownView()
    qtbot.addWidget(view)
    view.resize(700, 600)
    view.set_markdown("# Title\n\nBody text.\n\n## Sub\n")
    QApplication.processEvents()
    return view


# ------------------------------------------------------------ the stylesheet


def test_body_size_is_converted_from_the_stylesheet():
    """16 px in the stylesheet is 12 pt for Qt."""
    assert HeinoReader.preview_body_point_size() == pytest.approx(12.0)


def test_families_come_from_the_stylesheet():
    families = HeinoReader.preview_font_families()
    assert families[0] == "Noto Sans"
    assert all('"' not in family for family in families)


def test_stylesheet_keeps_its_css_pixels_for_the_web_backend():
    """The Qt conversion must not be pushed into the shared file."""
    assert "font-size: 16px" in HeinoReader.PREVIEW_CSS


@pytest.mark.parametrize(
    "css, expected",
    [
        ('body { font-size: 16px; }', 12.0),
        ('body { font-size: 12pt; }', 12.0),
        ('html, body { margin: 0; }\nbody { font-size: 18px; }', 13.5),
        # No usable declaration: fall back instead of raising.
        ('html, body { margin: 0; padding: 0; }', 12.0),
        ('body { font-size: 1.2em; }', 12.0),
    ],
)
def test_body_size_parsing(css, expected):
    assert HeinoReader.preview_body_point_size(css) == pytest.approx(expected)


# ------------------------------------------------------------ the Qt document


def test_default_font_is_point_sized(view):
    """Points scale with the DPI; pixel sizes would not."""
    font = view.document().defaultFont()
    assert font.pointSizeF() == pytest.approx(12.0)
    assert font.pixelSize() == -1


def test_preview_font_follows_the_zoom_level():
    assert preview_font(1.0).pointSizeF() == pytest.approx(12.0)
    assert preview_font(1.3).pointSizeF() == pytest.approx(15.6)
    assert preview_font(1.0).pixelSize() == -1


def test_zoom_rescales_the_document_font(view):
    view.set_zoom(1.3)
    assert view.document().defaultFont().pointSizeF() == pytest.approx(15.6)

    view.set_zoom(1.0)
    assert view.document().defaultFont().pointSizeF() == pytest.approx(12.0)


def test_no_pixel_size_leaks_into_the_document(view):
    """Each fragment inherits the document font instead of a CSS pixel size."""
    document = view.document()
    block = document.begin()
    while block.isValid():
        iterator = block.begin()
        while not iterator.atEnd():
            format_ = iterator.fragment().charFormat()
            assert format_.font().pixelSize() == -1
            iterator += 1
        block = block.next()


def test_headings_stay_larger_than_body_text(view):
    """Qt's HTML scale provides the hierarchy, relative to the base font."""
    document = view.document()
    document.setTextWidth(600)
    heights = {}
    block = document.begin()
    while block.isValid():
        text = block.text().strip()
        if text:
            heights[text] = document.documentLayout().blockBoundingRect(block).height()
        block = block.next()

    assert heights["Title"] > heights["Sub"] > heights["Body text."]


# ------------------------------------------------------------- line spacing


def _block_formats(view) -> dict:
    """Block format per non-empty block text, for the tiny fixture document."""
    formats = {}
    block = view.document().begin()
    while block.isValid():
        text = block.text().strip()
        if text:
            formats[text] = block.blockFormat()
        block = block.next()
    return formats


def test_stylesheet_declares_the_css_line_heights():
    assert HeinoReader.preview_line_height() == pytest.approx(1.55)
    assert HeinoReader.preview_line_height(heading=True) == pytest.approx(1.25)


@pytest.mark.parametrize(
    "css, expected_body, expected_heading",
    [
        ("body { line-height: 1.4; } h1 { line-height: 120%; }", 1.4, 1.2),
        ("body { line-height: 150%; }", 1.5, None),
        # A fixed length does not scale with the font; Qt gets no value.
        ("body { line-height: 20px; }", None, None),
        ("body { margin: 0; }", None, None),
    ],
)
def test_line_height_parsing(css, expected_body, expected_heading):
    assert HeinoReader.preview_line_height(css=css) == expected_body
    assert HeinoReader.preview_line_height(heading=True, css=css) == expected_heading


def test_body_blocks_use_the_css_line_height(view):
    """Qt's percentage is re-referenced to the font size, not used as parsed.

    Qt reads ``line-height: 1.55`` as 155 % of the font's natural line height;
    the block format therefore holds a converted value well below 155.
    """
    percent = _block_formats(view)["Body text."].lineHeight()
    assert 100 < percent < 130


def test_heading_line_height_differs_from_the_body_one(view):
    formats = _block_formats(view)
    assert formats["Title"].lineHeight() < formats["Body text."].lineHeight()


def test_wrapped_paragraph_lines_are_further_apart(qtbot):
    view = QtMarkdownView()
    qtbot.addWidget(view)
    view.resize(400, 600)
    view.set_markdown("word " * 120)

    document = view.document()
    document.setTextWidth(380)
    block = document.begin()
    # Building the block rect lays the block out, so lineCount() is valid after.
    per_line = document.documentLayout().blockBoundingRect(block).height()
    lines = block.layout().lineCount()
    assert lines > 1
    per_line /= lines
    natural = QFontMetricsF(document.defaultFont()).height()
    assert per_line > natural * 1.05
