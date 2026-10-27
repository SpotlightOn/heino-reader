"""Test-wide setup: force the offscreen platform before PySide6 loads."""

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_API", "pyside6")
# QtWebEngine needs these in headless/container environments.
os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--no-sandbox --disable-gpu")
os.environ.setdefault("QTWEBENGINE_DISABLE_SANDBOX", "1")


@pytest.fixture(autouse=True)
def isolated_settings(tmp_path, monkeypatch):
    """Keep the user's real ~/.config/heinoreader out of the test suite."""
    monkeypatch.setenv("HEINOREADER_CONFIG_DIR", str(tmp_path / "config"))
