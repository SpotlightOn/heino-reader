"""Tests for settings persisted in the XDG config directory."""

from __future__ import annotations

from PySide6.QtWidgets import QApplication

from HeinoReader.preview import RENDERER_QT, RENDERER_WEB
from HeinoReader.settings import (
    LINE_NUMBERS_KEY,
    RENDERER_KEY,
    Settings,
    config_dir,
)
from HeinoReader.webview import WebMarkdownView
from HeinoReader.window import ViewerWindow


def test_settings_file_lives_in_the_config_directory(tmp_path):
    settings = Settings()
    settings.set_string(RENDERER_KEY, "qt")

    assert settings.path == tmp_path / "config" / "settings.ini"
    assert settings.path.is_file()
    assert config_dir() == tmp_path / "config"
    assert Settings().get_string(RENDERER_KEY) == "qt"


def test_boolean_settings_round_trip(tmp_path):
    settings = Settings()
    settings.set_bool(LINE_NUMBERS_KEY, True)
    assert Settings().get_bool(LINE_NUMBERS_KEY) is True
    settings.set_bool(LINE_NUMBERS_KEY, False)
    assert Settings().get_bool(LINE_NUMBERS_KEY) is False


def test_renderer_choice_is_remembered(qtbot, tmp_path):
    doc = tmp_path / "doc.md"
    doc.write_text("# Title\n", encoding="utf-8")

    first = ViewerWindow(doc)
    qtbot.addWidget(first)
    assert first.preview.kind == RENDERER_QT
    first.actions.web_preview.setChecked(True)
    QApplication.processEvents()
    assert first.preview.kind == RENDERER_WEB

    second = ViewerWindow(doc)
    qtbot.addWidget(second)
    assert second.preview.kind == RENDERER_WEB
    assert isinstance(second.viewer, WebMarkdownView)


def test_view_toggles_are_remembered(qtbot, tmp_path):
    doc = tmp_path / "doc.md"
    doc.write_text("# Title\n", encoding="utf-8")

    first = ViewerWindow(doc)
    qtbot.addWidget(first)
    first.actions.line_numbers.setChecked(True)
    first.actions.remote_images.setChecked(False)
    first.actions.wrap_code.setChecked(False)
    QApplication.processEvents()

    second = ViewerWindow(doc)
    qtbot.addWidget(second)
    assert second.actions.line_numbers.isChecked()
    assert not second.actions.remote_images.isChecked()
    assert not second.viewer.remote_images_enabled
    assert not second.actions.wrap_code.isChecked()
    assert not second.viewer._wrap_code
