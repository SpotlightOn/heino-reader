"""Tests for choosing and switching renderers."""

from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication

import HeinoReader.viewer
from HeinoReader.viewer import (
    DEFAULT_RENDERER,
    RENDERER_QT,
    RENDERER_WEB,
    RENDERERS,
    chosen_renderer,
    create_markdown_view,
    web_engine_available,
)
from HeinoReader.viewer.qt import QtMarkdownView
from HeinoReader.viewer.render import markdown_to_html
from HeinoReader.viewer.web import WebMarkdownView
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
    assert window.viewer_area.kind == RENDERER_QT
    assert isinstance(window.viewer, QtMarkdownView)


def test_qt_renderer_can_be_chosen(qtbot, doc):
    window = make_window(qtbot, doc, RENDERER_QT)
    assert isinstance(window.viewer, QtMarkdownView)
    assert window.actions.web_renderer.isChecked() is False


def test_switching_renderer_replaces_the_view(qtbot, doc):
    window = make_window(qtbot, doc, RENDERER_WEB)
    assert isinstance(window.viewer, WebMarkdownView)

    # Wide code lines are one preference for both engines, so it has to follow
    # the view across a swap instead of resetting to the default.
    window.actions.wrap_code.setChecked(False)
    QApplication.processEvents()
    assert window.viewer._wrap_code is False

    window.actions.web_renderer.setChecked(False)
    QApplication.processEvents()
    assert isinstance(window.viewer, QtMarkdownView)
    assert window.viewer_area.kind == RENDERER_QT
    assert window.viewer.base_dir == doc.parent
    assert window.viewer._wrap_code is False

    window.actions.web_renderer.setChecked(True)
    QApplication.processEvents()
    assert isinstance(window.viewer, WebMarkdownView)
    assert window.viewer_area.kind == RENDERER_WEB
    assert window.viewer._wrap_code is False


def test_zoom_follows_the_view_across_a_backend_switch(qtbot, doc, monkeypatch):
    """A cached backend must not keep the zoom it had when it was parked."""
    # A second Qt view stands in for the web backend, so the test stays off
    # Chromium; the state handling in the window is what is under test.
    monkeypatch.setattr(
        HeinoReader.viewer,
        "create_markdown_view",
        lambda kind, parent: QtMarkdownView(parent),
    )
    window = make_window(qtbot, doc, RENDERER_QT)
    window.set_scale(1.2)
    window.actions.web_renderer.setChecked(True)
    QApplication.processEvents()
    assert window.viewer._scale == pytest.approx(1.2)

    window.set_scale(2.0)
    window.actions.web_renderer.setChecked(False)
    QApplication.processEvents()
    assert isinstance(window.viewer, QtMarkdownView)
    assert window.viewer._scale == pytest.approx(2.0)


def test_renderer_constants_are_consistent():
    assert DEFAULT_RENDERER in RENDERERS
    assert set(RENDERERS) == {"web", "qt"}


def test_web_engine_availability_probe_reports_the_installed_extra():
    assert web_engine_available() is True


def test_missing_web_engine_falls_back_to_qt(qtbot, doc, monkeypatch):
    """Without QtWebEngine the app must start, not crash."""
    monkeypatch.setattr(HeinoReader.viewer, "web_engine_available", lambda: False)
    window = make_window(qtbot, doc, RENDERER_WEB)

    assert window.viewer_area.kind == RENDERER_QT
    assert isinstance(window.viewer, QtMarkdownView)
    assert window.actions.web_renderer.isEnabled() is False
    assert "web" in window.actions.web_renderer.toolTip()


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


# --------------------------------------------------------- backend isolation

SRC = Path(__file__).resolve().parent.parent / "src"


def imported_modules(path):
    """Every module name a file imports, including lazy ones inside functions."""
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name
        elif isinstance(node, ast.ImportFrom) and node.module:
            yield node.module


def test_only_the_web_backend_imports_qtwebengine():
    """Chromium must stay behind one module, or a Qt start drags it in."""
    offenders = [
        str(path.relative_to(SRC))
        for path in (SRC / "HeinoReader").rglob("*.py")
        if path.parts[-2:] != ("viewer", "web.py")
        for module in imported_modules(path)
        if module.startswith("PySide6.QtWebEngine")
    ]

    assert offenders == []


def test_the_web_backend_is_not_imported_at_module_level():
    tree = ast.parse((SRC / "HeinoReader" / "viewer" / "__init__.py").read_text())

    module_level = [
        node.module or ""
        for node in tree.body
        if isinstance(node, ast.ImportFrom)
    ]

    assert "web" not in module_level


def test_a_qt_start_does_not_load_chromium():
    """Starting with the Qt renderer must not pay for the Chromium libraries."""
    code = (
        "import sys\n"
        f"sys.path.insert(0, {str(SRC)!r})\n"
        "from PySide6.QtWidgets import QApplication\n"
        "app = QApplication([])\n"
        "import HeinoReader.viewer as viewer\n"
        "viewer.create_markdown_view('qt')\n"
        "print([m for m in sys.modules if m.startswith('PySide6.QtWebEngine')])\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=True
    )
    assert result.stdout.strip() == "[]"


# --------------------------------------------------------------- switching

def test_switching_to_the_current_backend_changes_nothing(qtbot, doc):
    window = make_window(qtbot, doc, RENDERER_QT)
    view = window.viewer

    assert window.viewer_area.switch(RENDERER_QT) is True
    assert window.viewer is view


def test_switching_to_a_backend_that_cannot_be_created_reports_it(
    qtbot, doc, monkeypatch
):
    window = make_window(qtbot, doc, RENDERER_QT)
    create = HeinoReader.viewer.create_markdown_view

    def failing(kind, parent=None):
        if kind == RENDERER_WEB:
            raise ImportError("QtWebEngine is not installed")
        return create(kind, parent)

    monkeypatch.setattr(HeinoReader.viewer, "create_markdown_view", failing)

    assert window.viewer_area.switch(RENDERER_WEB) is False
    assert window.viewer_area.kind == RENDERER_QT


def test_an_unknown_renderer_name_falls_back_to_the_default():
    assert chosen_renderer("bogus", None) == DEFAULT_RENDERER


def test_the_web_backend_reports_the_remote_image_setting(qtbot, doc):
    window = make_window(qtbot, doc, RENDERER_WEB)

    assert window.viewer.remote_images_enabled is True
    window.viewer.set_remote_images_enabled(False)
    assert window.viewer.remote_images_enabled is False
