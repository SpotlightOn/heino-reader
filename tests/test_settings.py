"""Tests for settings persisted in the XDG config directory."""

from __future__ import annotations

from PySide6.QtWidgets import QApplication

import heinoreader
from heinoreader.settings import (
    LINE_NUMBERS_KEY,
    RENDERER_KEY,
    Settings,
    config_dir,
)
from heinoreader.webview import WebMarkdownView


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

    first = heinoreader.ViewerWindow(doc)
    qtbot.addWidget(first)
    assert first._renderer == heinoreader.RENDERER_QT
    first._web_preview_action.setChecked(True)
    QApplication.processEvents()
    assert first._renderer == heinoreader.RENDERER_WEB

    second = heinoreader.ViewerWindow(doc)
    qtbot.addWidget(second)
    assert second._renderer == heinoreader.RENDERER_WEB
    assert isinstance(second.viewer, WebMarkdownView)


def test_view_toggles_are_remembered(qtbot, tmp_path):
    doc = tmp_path / "doc.md"
    doc.write_text("# Title\n", encoding="utf-8")

    first = heinoreader.ViewerWindow(doc)
    qtbot.addWidget(first)
    first._line_numbers_action.setChecked(True)
    first._remote_images_action.setChecked(False)
    QApplication.processEvents()

    second = heinoreader.ViewerWindow(doc)
    qtbot.addWidget(second)
    assert second._line_numbers_action.isChecked()
    assert not second._remote_images_action.isChecked()
    assert not second.viewer.remote_images_enabled
