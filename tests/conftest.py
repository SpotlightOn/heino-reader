"""Test-wide setup: force the offscreen platform before PySide6 loads."""

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_API", "pyside6")
# QtWebEngine needs these in headless/container environments.
os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--no-sandbox --disable-gpu")
os.environ.setdefault("QTWEBENGINE_DISABLE_SANDBOX", "1")


@pytest.hookimpl(wrapper=True)
def pytest_runtest_teardown(item, nextitem):
    """Drain deferred deletes while Qt is still alive.

    pytest-qt closes the widgets with ``deleteLater()``, and the queue is only
    drained by a running event loop. After the last test nothing does that any
    more: the QtWebEngine page outlives the ``QApplication`` and Qt crashes in
    the interpreter's shutdown.
    """
    result = yield
    from PySide6.QtCore import QCoreApplication, QEvent
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is not None:
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        app.processEvents()
    return result


@pytest.fixture(autouse=True)
def isolated_settings(tmp_path, monkeypatch):
    """Keep the user's real ~/.config/heino-reader out of the test suite."""
    monkeypatch.setenv("HEINO_READER_CONFIG_DIR", str(tmp_path / "config"))


@pytest.fixture(autouse=True)
def no_modal_prompts(monkeypatch):
    """Never let a window-close teardown block on the unsaved-changes dialog.

    Tests that care about the prompt patch ``ask_discard_changes`` themselves,
    which overrides this default.
    """
    monkeypatch.setattr(
        "HeinoReader.window.ask_discard_changes",
        lambda parent, name: "discard",
    )
