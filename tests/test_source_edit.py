"""Tests for the source editor: Enter indentation and the quote bar."""

import pytest
from PySide6.QtCore import Qt

from heinoreader.editor.source_edit import (
    MarkdownSourceEdit,
    enter_indent,
    is_quote_line,
)


@pytest.mark.parametrize(
    ("line", "indent"),
    [
        ("plain text", ""),
        ("    indented block", "    "),
        ("\tTab indented", "    "),
        ("> quoted", "  "),
        ("> > nested quote", "    "),
        ("- list item", "  "),
        ("1. ordered item", "   "),
        ("  - nested item", "    "),
        ("> - quoted list", "    "),
    ],
)
def test_enter_indent_aligns_to_the_text_column(line, indent):
    assert enter_indent(line) == indent


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        ("> quote", True),
        ("   > quote", True),
        ("> > nested", True),
        ("    indented", False),
        ("\tindented", False),
        ("plain", False),
        ("  two spaces", False),
        ("    ", False),
        ("", False),
    ],
)
def test_quote_bar_applies_to_blockquotes_only(line, expected):
    assert is_quote_line(line) is expected


def make_editor(qtbot, text):
    editor = MarkdownSourceEdit()
    qtbot.addWidget(editor)
    editor.setPlainText(text)
    cursor = editor.textCursor()
    cursor.movePosition(cursor.MoveOperation.End)
    editor.setTextCursor(cursor)
    return editor


def press_enter(qtbot, editor):
    qtbot.keyClick(editor, Qt.Key.Key_Return)


def test_enter_at_end_of_indented_line_keeps_the_indent(qtbot):
    editor = make_editor(qtbot, "    code line")
    press_enter(qtbot, editor)
    assert editor.toPlainText() == "    code line\n    "
    assert editor.textCursor().positionInBlock() == 4


def test_enter_after_list_item_aligns_under_the_text(qtbot):
    editor = make_editor(qtbot, "- first")
    press_enter(qtbot, editor)
    assert editor.toPlainText() == "- first\n  "
    assert editor.textCursor().positionInBlock() == 2


def test_enter_after_quote_aligns_under_the_text(qtbot):
    editor = make_editor(qtbot, "> quoted")
    press_enter(qtbot, editor)
    assert editor.toPlainText() == "> quoted\n  "


def test_enter_on_plain_text_adds_no_indent(qtbot):
    editor = make_editor(qtbot, "plain")
    press_enter(qtbot, editor)
    assert editor.toPlainText() == "plain\n"
    assert editor.textCursor().positionInBlock() == 0
