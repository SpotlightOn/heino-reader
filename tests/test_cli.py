"""The command line entry point: argument checks and application setup."""

from __future__ import annotations

import subprocess
import sys
from typing import ClassVar

import pytest

from HeinoReader import cli


class FakeApplication:
    """Stand-in for QApplication: records setup, never enters the event loop."""

    created: ClassVar[list[FakeApplication]] = []

    def __init__(self, argv):
        self.argv = argv
        self.executed = False
        self.window_icon = None
        FakeApplication.created.append(self)

    def setApplicationName(self, name):
        self.application_name = name

    def setApplicationDisplayName(self, name):
        self.display_name = name

    def setDesktopFileName(self, name):
        self.desktop_file = name

    def setWindowIcon(self, icon):
        self.window_icon = icon

    def exec(self):
        self.executed = True
        return 0


class FakeWindow:
    """Stand-in for ViewerWindow: records how it was created."""

    created: ClassVar[list[FakeWindow]] = []

    def __init__(self, path, renderer=None):
        self.path = path
        self.renderer = renderer
        self.shown = False
        FakeWindow.created.append(self)

    def show(self):
        self.shown = True


@pytest.fixture
def fake_qt(monkeypatch):
    FakeApplication.created = []
    FakeWindow.created = []
    monkeypatch.setattr(cli, "QApplication", FakeApplication)
    monkeypatch.setattr(cli, "ViewerWindow", FakeWindow)
    return FakeApplication


@pytest.fixture
def markdown_file(tmp_path):
    path = tmp_path / "notes.md"
    path.write_text("# Title\n", encoding="utf-8")
    return path


def test_main_sets_up_the_application_and_shows_the_window(fake_qt, markdown_file):
    assert cli.main([str(markdown_file)]) == 0

    app = FakeApplication.created[0]
    assert app.application_name == "heino-reader"
    assert app.display_name == "Heino Reader"
    assert app.desktop_file == "heino-reader"
    assert app.window_icon is not None
    assert app.executed is True

    window = FakeWindow.created[0]
    assert window.path == markdown_file
    assert window.renderer is None
    assert window.shown is True


def test_main_passes_the_requested_renderer_through(fake_qt, markdown_file):
    assert cli.main(["--renderer", "web", str(markdown_file)]) == 0

    assert FakeWindow.created[0].renderer == "web"


def test_main_starts_without_a_file(fake_qt):
    assert cli.main([]) == 0

    assert FakeWindow.created[0].path is None


def test_main_refuses_a_missing_file_before_starting_qt(fake_qt):
    assert cli.main(["/does/not/exist.md"]) == 2

    assert FakeApplication.created == []
    assert FakeWindow.created == []


def test_the_module_entry_point_prints_the_usage():
    """`python -m HeinoReader` is a documented way to start the app."""
    result = subprocess.run(
        [sys.executable, "-m", "HeinoReader", "--help"],
        capture_output=True,
        text=True,
        check=True,
    )

    assert "heino-reader" in result.stdout
    assert "--renderer" in result.stdout
