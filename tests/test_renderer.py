"""Tests for choosing and switching the preview backend."""

from __future__ import annotations

import pytest
from PySide6.QtWidgets import QApplication

import heinoreader
from heinoreader import ViewerWindow
from heinoreader.qtview import QtMarkdownView
from heinoreader.webview import WebMarkdownView


@pytest.fixture
def doc(tmp_path):
    path = tmp_path / "doc.md"
    path.write_text(
        "# Title\n\n> quote\n\n```js\nlet x = 1\n```\n", encoding="utf-8"
    )
    return path


def make_window(qtbot, path, renderer):
    window = ViewerWindow(path, renderer=renderer)
    qtbot.addWidget(window)
    window.show()
    QApplication.processEvents()
    return window


def test_factory_returns_the_requested_backend():
    assert isinstance(
        heinoreader.create_markdown_view(heinoreader.RENDERER_WEB), WebMarkdownView
    )
    assert isinstance(
        heinoreader.create_markdown_view(heinoreader.RENDERER_QT), QtMarkdownView
    )


def test_default_renderer_is_qt(qtbot, doc):
    window = make_window(qtbot, doc, heinoreader.DEFAULT_RENDERER)
    assert heinoreader.DEFAULT_RENDERER == heinoreader.RENDERER_QT
    assert window._renderer == heinoreader.RENDERER_QT
    assert isinstance(window.viewer, QtMarkdownView)


def test_qt_renderer_can_be_chosen(qtbot, doc):
    window = make_window(qtbot, doc, heinoreader.RENDERER_QT)
    assert isinstance(window.viewer, QtMarkdownView)
    assert window._web_preview_action.isChecked() is False


def test_switching_renderer_replaces_the_view(qtbot, doc):
    window = make_window(qtbot, doc, heinoreader.RENDERER_WEB)
    assert isinstance(window.viewer, WebMarkdownView)

    window._web_preview_action.setChecked(False)
    QApplication.processEvents()
    assert isinstance(window.viewer, QtMarkdownView)
    assert window._renderer == heinoreader.RENDERER_QT
    assert window.viewer.base_dir == doc.parent

    window._web_preview_action.setChecked(True)
    QApplication.processEvents()
    assert isinstance(window.viewer, WebMarkdownView)
    assert window._renderer == heinoreader.RENDERER_WEB


def test_renderer_constants_are_consistent():
    assert heinoreader.DEFAULT_RENDERER in heinoreader.RENDERERS
    assert set(heinoreader.RENDERERS) == {"web", "qt"}


# --------------------------------------------------------------- markup

def test_qt_code_blocks_are_wrapped_in_a_padded_table():
    """Qt ignores padding on block elements, so code sits in a table cell."""
    html = heinoreader.markdown_to_html("```python\nx = 1\n```\n", qt=True)
    assert '<table class="codeblock"' in html
    assert 'class="codebody"' in html
    assert "<pre" in html


def test_qt_indented_code_is_wrapped_the_same_way():
    html = heinoreader.markdown_to_html("    indented\n", qt=True)
    assert '<table class="codeblock"' in html


def test_qt_indented_code_stays_in_one_text_block():
    """One block per code block, otherwise Qt paints a bar per line."""
    html = heinoreader.markdown_to_html("    one\n    two\n", qt=True)
    assert "one<br>two" in html


def test_qt_blockquotes_are_wrapped_in_a_padded_table():
    html = heinoreader.markdown_to_html("> quote\n", qt=True)
    assert '<table class="quote"' in html
    assert 'class="quotebody"' in html
    assert "<blockquote>" not in html


def test_web_markup_keeps_plain_block_elements():
    html = heinoreader.markdown_to_html("> quote\n\n    code\n")
    assert "<blockquote>" in html
    assert 'class="codeblock"' not in html
    assert 'class="quote"' not in html
