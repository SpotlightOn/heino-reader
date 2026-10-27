"""Tests for file validation: no binary data may be loaded as text."""

from __future__ import annotations

import pytest
from PySide6.QtCore import QMimeData, QPoint, Qt, QUrl
from PySide6.QtGui import QDragEnterEvent, QDropEvent

import HeinoReader
import HeinoReader.window
from HeinoReader.files import is_supported_path, looks_binary, rejection_reason


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("notes.md", True),
        ("notes.markdown", True),
        ("NOTES.MD", True),
        ("plain.txt", True),
        ("image.png", False),
        ("photo.jpg", False),
        ("archive.zip", False),
        ("document.pdf", False),
        ("noextension", False),
    ],
)
def test_is_supported_path(name, expected, tmp_path):
    assert is_supported_path(tmp_path / name) is expected


def test_looks_binary_detects_nul_bytes(tmp_path):
    text = tmp_path / "a.md"
    text.write_text("just text\n", encoding="utf-8")
    assert not looks_binary(text)

    binary = tmp_path / "b.md"
    binary.write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR")
    assert looks_binary(binary)


def test_rejection_reason_accepts_markdown(tmp_path):
    path = tmp_path / "ok.md"
    path.write_text("# fine\n", encoding="utf-8")
    assert rejection_reason(path) is None


def test_rejection_reason_rejects_binary_markdown(tmp_path):
    path = tmp_path / "fake.md"
    path.write_bytes(b"\x00\x01\x02binary")
    assert "binary" in rejection_reason(path)


def test_rejection_reason_rejects_unsupported_suffix(tmp_path):
    path = tmp_path / "picture.png"
    path.write_bytes(b"\x89PNG\r\n\x1a\n")
    assert "not a supported text format" in rejection_reason(path)


def test_rejection_reason_rejects_large_files(tmp_path):
    path = tmp_path / "big.md"
    path.write_text("x" * 100, encoding="utf-8")
    assert "MB" in rejection_reason(path, max_size=10)


def test_rejection_reason_rejects_missing_files(tmp_path):
    assert "does not exist" in rejection_reason(tmp_path / "missing.md")


def test_rejection_reason_rejects_directories(tmp_path):
    assert "not a regular file" in rejection_reason(tmp_path)


# ------------------------------------------------------------- window paths

@pytest.fixture
def window(qtbot, tmp_path):
    md = tmp_path / "notes.md"
    md.write_text("# Notes\n", encoding="utf-8")
    window = HeinoReader.ViewerWindow(md)
    qtbot.addWidget(window)
    window.show()
    from PySide6.QtWidgets import QApplication

    QApplication.processEvents()
    return window


def drop_url(window, path):
    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile(str(path))])
    event = QDropEvent(
        QPoint(10, 10),
        Qt.DropAction.CopyAction,
        mime,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    window.dropEvent(event)
    return event


def test_open_refuses_a_binary_file(window, tmp_path):
    png = tmp_path / "picture.png"
    png.write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00")
    before = window._markdown
    assert window.open(png) is False
    assert window._markdown == before


def test_dropping_an_image_is_rejected(window, tmp_path, monkeypatch):
    warnings = []
    monkeypatch.setattr(
        HeinoReader.window.QMessageBox, "warning", staticmethod(lambda *a, **k: warnings.append(a))
    )
    png = tmp_path / "picture.png"
    png.write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00")
    before = window._markdown

    event = drop_url(window, png)

    assert not event.isAccepted()
    assert window._markdown == before
    assert warnings, "the user should be told why the drop was rejected"


def test_dropping_markdown_is_accepted(window, tmp_path):
    other = tmp_path / "other.md"
    other.write_text("# Other\n", encoding="utf-8")
    event = drop_url(window, other)
    assert event.isAccepted()
    assert "Other" in window._markdown


@pytest.mark.parametrize(
    ("name", "accepted"),
    [("notes.md", True), ("picture.png", False)],
)
def test_drag_enter_only_accepts_text_files(window, tmp_path, name, accepted):
    path = tmp_path / name
    path.write_bytes(b"# x\n")
    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile(str(path))])
    event = QDragEnterEvent(
        QPoint(10, 10),
        Qt.DropAction.CopyAction,
        mime,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    window.dragEnterEvent(event)
    assert event.isAccepted() is accepted
