"""Link handling in the Qt text backend: hover, click and URL resolution."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

import HeinoReader.viewer.qt as qt_backend
from HeinoReader.viewer.qt import QtMarkdownView


@pytest.fixture
def opened(monkeypatch):
    """Record every URL the backend hands to the system handler."""
    targets = []
    monkeypatch.setattr(qt_backend, "open_external", targets.append)
    return targets


def make_view(qtbot, markdown: str, base_dir=None) -> QtMarkdownView:
    view = QtMarkdownView()
    qtbot.addWidget(view)
    view.resize(600, 300)
    if base_dir is not None:
        view.set_base_dir(base_dir)
    view.set_markdown(markdown)
    view.show()
    QApplication.processEvents()
    return view


def link_point(view: QtMarkdownView, text: str = "target") -> QPoint:
    """Centre of the first character of the anchor text."""
    cursor = view.textCursor()
    cursor.setPosition(view.toPlainText().index(text))
    return view.cursorRect(cursor).center()


def click(view: QtMarkdownView, point: QPoint) -> None:
    QTest.mouseClick(
        view.viewport(), Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, point
    )
    QApplication.processEvents()


# ---------------------------------------------------------------- hovering


def test_hover_over_a_link_shows_target_and_pointing_hand(qtbot):
    view = make_view(qtbot, "see [target](https://example.org) here")

    QTest.mouseMove(view.viewport(), link_point(view))
    QApplication.processEvents()

    assert view.cursor().shape() == Qt.CursorShape.PointingHandCursor
    assert view.toolTip() == "https://example.org"


def test_hover_off_the_link_restores_the_text_cursor(qtbot):
    view = make_view(qtbot, "see [target](https://example.org) here")
    QTest.mouseMove(view.viewport(), link_point(view))

    QTest.mouseMove(view.viewport(), QPoint(560, 260))
    QApplication.processEvents()

    assert view.cursor().shape() == Qt.CursorShape.IBeamCursor
    assert view.toolTip() == ""


# ----------------------------------------------------------------- clicking


def test_click_on_a_link_opens_it(qtbot, opened):
    view = make_view(qtbot, "see [target](https://example.org) here")

    click(view, link_point(view))

    assert [url.toString() for url in opened] == ["https://example.org"]


def test_click_beside_the_link_opens_nothing(qtbot, opened):
    view = make_view(qtbot, "see [target](https://example.org) here")

    click(view, QPoint(560, 260))

    assert opened == []


def test_click_with_an_anchor_target_opens_nothing(qtbot, opened):
    view = make_view(qtbot, "jump to [target](#chapter)")

    click(view, link_point(view))

    assert opened == []


def test_click_on_a_relative_link_opens_the_file_next_to_the_document(
    qtbot, opened, tmp_path
):
    view = make_view(qtbot, "read [target](other.md)", base_dir=tmp_path)

    click(view, link_point(view))

    assert [url.toLocalFile() for url in opened] == [
        str((tmp_path / "other.md").resolve())
    ]


def test_dragging_across_a_link_does_not_open_it(qtbot, opened):
    """Selecting text starts on a link more often than one would think."""
    view = make_view(qtbot, "see [target](https://example.org) here")
    point = link_point(view)

    QTest.mousePress(
        view.viewport(), Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, point
    )
    QTest.mouseRelease(
        view.viewport(),
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
        point + QPoint(40, 0),
    )
    QApplication.processEvents()

    assert opened == []


def test_repeated_click_within_the_debounce_window_opens_once(qtbot, opened, monkeypatch):
    """A double click on a link must not start two browser windows."""
    now = [100.0]
    monkeypatch.setattr(qt_backend, "time", SimpleNamespace(monotonic=lambda: now[0]))
    view = make_view(qtbot, "see [target](https://example.org) here")
    point = link_point(view)

    click(view, point)
    click(view, point)

    assert [url.toString() for url in opened] == ["https://example.org"]

    now[0] += 1.0  # outside the window: a deliberate second click opens again
    click(view, point)
    assert len(opened) == 2


def test_click_with_another_button_opens_nothing(qtbot, opened):
    view = make_view(qtbot, "see [target](https://example.org) here")

    QTest.mouseClick(
        view.viewport(),
        Qt.MouseButton.RightButton,
        Qt.KeyboardModifier.NoModifier,
        link_point(view),
    )
    QApplication.processEvents()

    assert opened == []


# ----------------------------------------------------------- URL resolution


def test_scheme_links_are_handed_over_unchanged(qtbot):
    view = make_view(qtbot, "text")

    assert view._link_url("mailto:heino@example.org").toString() == (
        "mailto:heino@example.org"
    )


def test_relative_targets_resolve_against_the_base_directory(qtbot, tmp_path):
    view = make_view(qtbot, "text", base_dir=tmp_path)

    url = view._link_url("notes/other.md")

    assert url.toLocalFile() == str((tmp_path / "notes" / "other.md").resolve())


def test_absolute_paths_work_without_a_base_directory(qtbot):
    view = make_view(qtbot, "text")

    assert view._link_url("/tmp/other.md").toLocalFile() == "/tmp/other.md"


def test_bare_targets_without_a_base_directory_are_not_opened(qtbot):
    view = make_view(qtbot, "text")

    assert view._link_url("other.md") is None


def test_empty_and_anchor_targets_are_not_opened(qtbot):
    view = make_view(qtbot, "text")

    assert view._link_url("") is None
    assert view._link_url("#chapter") is None
