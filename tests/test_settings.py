"""Tests for settings persisted in the XDG config directory."""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import QStandardPaths
from PySide6.QtWidgets import QApplication

import HeinoReader.settings
from HeinoReader.settings import (
    LINE_NUMBERS_KEY,
    RENDERER_KEY,
    SCALE_KEY,
    Settings,
    config_dir,
)
from HeinoReader.viewer import RENDERER_QT, RENDERER_WEB
from HeinoReader.viewer.web import WebMarkdownView
from HeinoReader.window import MAX_SCALE, MIN_SCALE, ViewerWindow


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
    assert first.viewer_area.kind == RENDERER_QT
    first.actions.web_renderer.setChecked(True)
    QApplication.processEvents()
    assert first.viewer_area.kind == RENDERER_WEB

    second = ViewerWindow(doc)
    qtbot.addWidget(second)
    assert second.viewer_area.kind == RENDERER_WEB
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


def test_config_dir_falls_back_to_the_home_folder(monkeypatch):
    """Without a platform config location, XDG's default is still used."""

    class NoPlatformPath:
        StandardLocation = QStandardPaths.StandardLocation

        @staticmethod
        def writableLocation(location):
            return ""

    monkeypatch.delenv("HEINO_READER_CONFIG_DIR")
    monkeypatch.setattr(HeinoReader.settings, "QStandardPaths", NoPlatformPath)

    assert config_dir() == Path.home() / ".config" / "heino-reader"


def test_numeric_settings_round_trip_and_ignore_garbage():
    settings = Settings()

    settings.set_string(SCALE_KEY, "1.25")
    assert Settings().get_float(SCALE_KEY) == pytest.approx(1.25)

    settings.set_string(SCALE_KEY, "not a number")
    assert Settings().get_float(SCALE_KEY, 1.0) == pytest.approx(1.0)


def test_zoom_and_line_numbers_survive_a_restart(qtbot, tmp_path):
    """A restart is: write through one window, then build a new one."""
    doc = tmp_path / "doc.md"
    doc.write_text("# Title\n", encoding="utf-8")

    first = ViewerWindow(doc)
    qtbot.addWidget(first)
    first.set_scale(1.4)
    first.actions.line_numbers.setChecked(True)
    QApplication.processEvents()

    second = ViewerWindow(doc)
    qtbot.addWidget(second)
    second.actions.edit_mode.setChecked(True)
    QApplication.processEvents()

    assert second.scale == pytest.approx(1.4)
    assert second.zoom_label.text() == "140%"
    assert second.viewer._scale == pytest.approx(1.4)
    assert second.actions.line_numbers.isChecked()
    assert second.editor.gutter.installed


@pytest.mark.parametrize(
    ("stored", "expected"),
    [("99", MAX_SCALE), ("0.01", MIN_SCALE)],
)
def test_a_stored_zoom_outside_the_range_is_clamped(
    qtbot, tmp_path, stored, expected
):
    """A hand-edited or corrupted config must not make the text unusable."""
    Settings().set_string(SCALE_KEY, stored)
    doc = tmp_path / "doc.md"
    doc.write_text("# Title\n", encoding="utf-8")

    window = ViewerWindow(doc)
    qtbot.addWidget(window)

    assert window.scale == pytest.approx(expected)
