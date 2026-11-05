"""Tests for choosing and switching the preview backend."""

from __future__ import annotations

import pytest
from PySide6.QtWidgets import QApplication

import HeinoReader.preview
from HeinoReader.preview import (
    DEFAULT_RENDERER,
    RENDERER_QT,
    RENDERER_WEB,
    RENDERERS,
    create_markdown_view,
    web_engine_available,
)
from HeinoReader.qtview import QtMarkdownView
from HeinoReader.render import markdown_to_html
from HeinoReader.webview import WebMarkdownView
from HeinoReader.window import ViewerWindow


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


@pytest.mark.usefixtures("qapp")
def test_factory_returns_the_requested_backend():
    assert isinstance(
        create_markdown_view(RENDERER_WEB), WebMarkdownView
    )
    assert isinstance(
        create_markdown_view(RENDERER_QT), QtMarkdownView
    )


def test_default_renderer_is_qt(qtbot, doc):
    window = make_window(qtbot, doc, DEFAULT_RENDERER)
    assert DEFAULT_RENDERER == RENDERER_QT
    assert window.preview.kind == RENDERER_QT
    assert isinstance(window.viewer, QtMarkdownView)


def test_qt_renderer_can_be_chosen(qtbot, doc):
    window = make_window(qtbot, doc, RENDERER_QT)
    assert isinstance(window.viewer, QtMarkdownView)
    assert window.actions.web_preview.isChecked() is False


def test_switching_renderer_replaces_the_view(qtbot, doc):
    window = make_window(qtbot, doc, RENDERER_WEB)
    assert isinstance(window.viewer, WebMarkdownView)

    # Wide code lines are one preference for both engines, so it has to follow
    # the view across a swap instead of resetting to the default.
    window.actions.wrap_code.setChecked(False)
    QApplication.processEvents()
    assert window.viewer._wrap_code is False

    window.actions.web_preview.setChecked(False)
    QApplication.processEvents()
    assert isinstance(window.viewer, QtMarkdownView)
    assert window.preview.kind == RENDERER_QT
    assert window.viewer.base_dir == doc.parent
    assert window.viewer._wrap_code is False

    window.actions.web_preview.setChecked(True)
    QApplication.processEvents()
    assert isinstance(window.viewer, WebMarkdownView)
    assert window.preview.kind == RENDERER_WEB
    assert window.viewer._wrap_code is False


def test_zoom_follows_the_view_across_a_backend_switch(qtbot, doc, monkeypatch):
    """A cached backend must not keep the zoom it had when it was parked."""
    # A second Qt view stands in for the web backend, so the test stays off
    # Chromium; the state handling in the window is what is under test.
    monkeypatch.setattr(
        HeinoReader.preview,
        "create_markdown_view",
        lambda kind, parent: QtMarkdownView(parent),
    )
    window = make_window(qtbot, doc, RENDERER_QT)
    window.set_scale(1.2)
    window.actions.web_preview.setChecked(True)
    QApplication.processEvents()
    assert window.viewer._scale == pytest.approx(1.2)

    window.set_scale(2.0)
    window.actions.web_preview.setChecked(False)
    QApplication.processEvents()
    assert isinstance(window.viewer, QtMarkdownView)
    assert window.viewer._scale == pytest.approx(2.0)


def test_renderer_constants_are_consistent():
    assert DEFAULT_RENDERER in RENDERERS
    assert set(RENDERERS) == {"web", "qt"}


def test_web_engine_availability_probe_reports_the_installed_extra():
    assert web_engine_available() is True


def test_missing_web_engine_falls_back_to_qt(qtbot, doc, monkeypatch):
    """Without pyside6-addons the app must start, not crash."""
    monkeypatch.setattr(HeinoReader.preview, "web_engine_available", lambda: False)
    window = make_window(qtbot, doc, RENDERER_WEB)

    assert window.preview.kind == RENDERER_QT
    assert isinstance(window.viewer, QtMarkdownView)
    assert window.actions.web_preview.isEnabled() is False
    assert "web" in window.actions.web_preview.toolTip()


def test_both_backends_implement_the_view_contract():
    """The window relies on this method set, whatever the backend."""
    for view_class in (QtMarkdownView, WebMarkdownView):
        for name in (
            "set_markdown",
            "set_zoom",
            "set_base_dir",
            "set_code_wrap",
            "set_remote_images_enabled",
        ):
            assert callable(getattr(view_class, name)), name


# --------------------------------------------------------------- markup

def test_qt_code_blocks_are_wrapped_in_a_padded_table():
    """Qt ignores padding on block elements, so code sits in a table cell."""
    html = markdown_to_html("```python\nx = 1\n```\n", qt=True)
    assert '<table class="codeblock"' in html
    assert 'class="codebody"' in html
    assert "<pre" in html


def test_qt_indented_code_is_wrapped_the_same_way():
    html = markdown_to_html("    indented\n", qt=True)
    assert '<table class="codeblock"' in html


def test_qt_indented_code_stays_in_one_text_block():
    """One block per code block, otherwise Qt paints a bar per line."""
    html = markdown_to_html("    one\n    two\n", qt=True)
    assert "one<br>two" in html


def test_qt_blockquotes_are_wrapped_in_a_padded_table():
    html = markdown_to_html("> quote\n", qt=True)
    assert '<table class="quote"' in html
    assert 'class="quotebody"' in html
    assert "<blockquote>" not in html


def test_web_markup_keeps_plain_block_elements():
    html = markdown_to_html("> quote\n\n    code\n")
    assert "<blockquote>" in html
    assert 'class="codeblock"' not in html
    assert 'class="quote"' not in html
