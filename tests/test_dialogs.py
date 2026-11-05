"""Tests for the insert dialogs and the window's own dialogs."""

from __future__ import annotations

import pytest
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QMessageBox

import HeinoReader.window
from HeinoReader.editor.dialogs import (
    ImageDialog,
    LinkDialog,
    TableDialog,
    ask_image,
    ask_link_url,
    ask_table_size,
)
from HeinoReader.window import (
    ask_discard_changes,
    ask_open_file,
    ask_save_file,
    show_about,
)


def answer_dialog(monkeypatch, dialog_class, fill, accepted=True):
    """Run a modal dialog without blocking: fill it, then answer it."""

    def fake_exec(self):
        fill(self)
        return int(accepted)

    monkeypatch.setattr(dialog_class, "exec", fake_exec)


def click(dialog, button):
    box = dialog._button_box
    box.button(button).click()


# ------------------------------------------------------------ insert dialogs


def test_link_dialog_starts_with_the_selection_selected(qtbot):
    dialog = LinkDialog(None, "https://example.org")
    qtbot.addWidget(dialog)

    assert dialog._url.selectedText() == "https://example.org"
    dialog._url.setText("  notes/other.md  ")
    assert dialog.url() == "notes/other.md"


def test_link_dialog_buttons_accept_and_reject(qtbot):
    dialog = LinkDialog()
    qtbot.addWidget(dialog)
    click(dialog, QDialogButtonBox.StandardButton.Ok)
    assert dialog.result() == QDialog.DialogCode.Accepted

    dialog = LinkDialog()
    qtbot.addWidget(dialog)
    click(dialog, QDialogButtonBox.StandardButton.Cancel)
    assert dialog.result() == QDialog.DialogCode.Rejected


def test_image_dialog_reads_path_and_alternative_text(qtbot):
    dialog = ImageDialog(None, start_dir="/tmp", alt="Start")
    qtbot.addWidget(dialog)

    assert dialog.alternative_text() == "Start"
    dialog._path.setText("  pics/a.png  ")
    dialog._alt.setText("  A picture  ")
    assert dialog.image_path() == "pics/a.png"
    assert dialog.alternative_text() == "A picture"


def test_image_dialog_browse_fills_the_path(qtbot, monkeypatch, tmp_path):
    dialog = ImageDialog(None, start_dir=str(tmp_path))
    qtbot.addWidget(dialog)
    monkeypatch.setattr(
        "HeinoReader.editor.dialogs.QFileDialog.getOpenFileName",
        lambda *args, **kwargs: (str(tmp_path / "photo.png"), ""),
    )

    dialog._browse()

    assert dialog.image_path() == str(tmp_path / "photo.png")


def test_image_dialog_browse_cancelled_keeps_the_path(qtbot, monkeypatch):
    dialog = ImageDialog()
    qtbot.addWidget(dialog)
    dialog._path.setText("keep.png")
    monkeypatch.setattr(
        "HeinoReader.editor.dialogs.QFileDialog.getOpenFileName",
        lambda *args, **kwargs: ("", ""),
    )

    dialog._browse()

    assert dialog.image_path() == "keep.png"


def test_table_dialog_clamps_to_its_ranges(qtbot):
    dialog = TableDialog(None, rows=3, columns=3)
    qtbot.addWidget(dialog)

    assert (dialog.rows(), dialog.columns()) == (3, 3)
    dialog._rows.setValue(1)
    dialog._columns.setValue(500)
    assert (dialog.rows(), dialog.columns()) == (2, 50)


def test_ask_link_url_returns_the_target_and_none_when_cancelled(
    monkeypatch, qapp
):
    answer_dialog(
        monkeypatch, LinkDialog, lambda self: self._url.setText("notes.md")
    )
    assert ask_link_url(None) == "notes.md"

    answer_dialog(monkeypatch, LinkDialog, lambda self: None, accepted=False)
    assert ask_link_url(None) is None


def test_ask_image_needs_a_path(monkeypatch, qapp):
    def fill(self):
        self._path.setText("pics/a.png")
        self._alt.setText("A")

    answer_dialog(monkeypatch, ImageDialog, fill)
    assert ask_image(None) == ("pics/a.png", "A")

    answer_dialog(monkeypatch, ImageDialog, lambda self: None)
    assert ask_image(None) is None

    answer_dialog(monkeypatch, ImageDialog, lambda self: self._path.setText("  "))
    assert ask_image(None) is None


def test_ask_table_size_returns_the_chosen_size(monkeypatch, qapp):
    answer_dialog(monkeypatch, TableDialog, lambda self: None)
    assert ask_table_size(None) == (3, 3)

    answer_dialog(monkeypatch, TableDialog, lambda self: None, accepted=False)
    assert ask_table_size(None) is None


# ----------------------------------------------------------- window dialogs


def test_ask_open_file_returns_the_chosen_path(monkeypatch, qapp, tmp_path):
    monkeypatch.setattr(
        HeinoReader.window.QFileDialog,
        "getOpenFileName",
        lambda *args, **kwargs: (str(tmp_path / "notes.md"), ""),
    )
    assert ask_open_file(None, str(tmp_path)) == tmp_path / "notes.md"


def test_ask_open_file_returns_none_when_cancelled(monkeypatch, qapp):
    monkeypatch.setattr(
        HeinoReader.window.QFileDialog,
        "getOpenFileName",
        lambda *args, **kwargs: ("", ""),
    )
    assert ask_open_file(None, "") is None


def test_ask_save_file_returns_the_chosen_path(monkeypatch, qapp, tmp_path):
    monkeypatch.setattr(
        HeinoReader.window.QFileDialog,
        "getSaveFileName",
        lambda *args, **kwargs: (str(tmp_path / "out.md"), ""),
    )
    assert ask_save_file(None, str(tmp_path)) == tmp_path / "out.md"


def test_ask_save_file_returns_none_when_cancelled(monkeypatch, qapp):
    monkeypatch.setattr(
        HeinoReader.window.QFileDialog,
        "getSaveFileName",
        lambda *args, **kwargs: ("", ""),
    )
    assert ask_save_file(None, "") is None


def test_show_about_passes_the_parent(monkeypatch, qapp):
    shown = []
    monkeypatch.setattr(
        HeinoReader.window.QMessageBox,
        "about",
        lambda parent, title, text: shown.append((parent, title, text)),
    )

    show_about(None)

    assert shown and "Heino Reader" in shown[0][1]


class FakeMessageBox:
    """Stand-in for QMessageBox that answers with a chosen button."""

    Icon = QMessageBox.Icon
    ButtonRole = QMessageBox.ButtonRole

    answer = "Discard"

    def __init__(self, parent=None) -> None:
        self._buttons = []

    def setWindowTitle(self, *args) -> None:
        pass

    def setText(self, *args) -> None:
        pass

    def setInformativeText(self, *args) -> None:
        pass

    def setIcon(self, *args) -> None:
        pass

    def addButton(self, label, role):
        button = object()
        self._buttons.append((label, button))
        return button

    def setDefaultButton(self, button) -> None:
        pass

    def exec(self) -> int:
        return 0

    def clickedButton(self):
        return next(
            button for label, button in self._buttons if label == self.answer
        )


@pytest.mark.parametrize(
    ("answer", "expected"),
    [("Discard", "discard"), ("Cancel", "cancel")],
)
def test_ask_discard_changes_maps_the_button(
    monkeypatch, qapp, answer, expected
):
    box = FakeMessageBox()
    box.answer = answer

    def make_box(parent=None):
        return box

    make_box.Icon = QMessageBox.Icon
    make_box.ButtonRole = QMessageBox.ButtonRole
    monkeypatch.setattr(HeinoReader.window, "QMessageBox", make_box)

    assert ask_discard_changes(None, "notes.md") is expected
