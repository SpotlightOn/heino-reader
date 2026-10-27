"""Tests for choosing and switching the preview backend."""

from __future__ import annotations

import pytest
from PySide6.QtWidgets import QApplication

import HeinoReader
from HeinoReader import ViewerWindow
from HeinoReader.qtview import QtMarkdownView
from HeinoReader.webview import WebMarkdownView


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
        HeinoReader.create_markdown_view(HeinoReader.RENDERER_WEB), WebMarkdownView
    )
    assert isinstance(
        HeinoReader.create_markdown_view(HeinoReader.RENDERER_QT), QtMarkdownView
    )


def test_default_renderer_is_qt(qtbot, doc):
    window = make_window(qtbot, doc, HeinoReader.DEFAULT_RENDERER)
    assert HeinoReader.DEFAULT_RENDERER == HeinoReader.RENDERER_QT
    assert window._renderer == HeinoReader.RENDERER_QT
    assert isinstance(window.viewer, QtMarkdownView)


def test_qt_renderer_can_be_chosen(qtbot, doc):
    window = make_window(qtbot, doc, HeinoReader.RENDERER_QT)
    assert isinstance(window.viewer, QtMarkdownView)
    assert window._web_preview_action.isChecked() is False


def test_switching_renderer_replaces_the_view(qtbot, doc):
    window = make_window(qtbot, doc, HeinoReader.RENDERER_WEB)
    assert isinstance(window.viewer, WebMarkdownView)

    window._web_preview_action.setChecked(False)
    QApplication.processEvents()
    assert isinstance(window.viewer, QtMarkdownView)
    assert window._renderer == HeinoReader.RENDERER_QT
    assert window.viewer.base_dir == doc.parent

    window._web_preview_action.setChecked(True)
    QApplication.processEvents()
    assert isinstance(window.viewer, WebMarkdownView)
    assert window._renderer == HeinoReader.RENDERER_WEB


def test_renderer_constants_are_consistent():
    assert HeinoReader.DEFAULT_RENDERER in HeinoReader.RENDERERS
    assert set(HeinoReader.RENDERERS) == {"web", "qt"}


def test_web_engine_availability_probe_reports_the_installed_extra():
    assert HeinoReader.web_engine_available() is True


def test_missing_web_engine_falls_back_to_qt(qtbot, doc, monkeypatch):
    """Without pyside6-addons the app must start, not crash."""
    import HeinoReader.window as window_module

    monkeypatch.setattr(window_module, "web_engine_available", lambda: False)
    window = make_window(qtbot, doc, HeinoReader.RENDERER_WEB)

    assert window._renderer == HeinoReader.RENDERER_QT
    assert isinstance(window.viewer, QtMarkdownView)
    assert window._web_preview_action.isEnabled() is False
    assert "web" in window._web_preview_action.toolTip()


# --------------------------------------------------------------- markup

def test_qt_code_blocks_are_wrapped_in_a_padded_table():
    """Qt ignores padding on block elements, so code sits in a table cell."""
    html = HeinoReader.markdown_to_html("```python\nx = 1\n```\n", qt=True)
    assert '<table class="codeblock"' in html
    assert 'class="codebody"' in html
    assert "<pre" in html


def test_qt_indented_code_is_wrapped_the_same_way():
    html = HeinoReader.markdown_to_html("    indented\n", qt=True)
    assert '<table class="codeblock"' in html


def test_qt_indented_code_stays_in_one_text_block():
    """One block per code block, otherwise Qt paints a bar per line."""
    html = HeinoReader.markdown_to_html("    one\n    two\n", qt=True)
    assert "one<br>two" in html


def test_qt_blockquotes_are_wrapped_in_a_padded_table():
    html = HeinoReader.markdown_to_html("> quote\n", qt=True)
    assert '<table class="quote"' in html
    assert 'class="quotebody"' in html
    assert "<blockquote>" not in html


def test_web_markup_keeps_plain_block_elements():
    html = HeinoReader.markdown_to_html("> quote\n\n    code\n")
    assert "<blockquote>" in html
    assert 'class="codeblock"' not in html
    assert 'class="quote"' not in html
