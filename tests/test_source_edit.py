"""Tests for the source editor: Enter continuation and the quote bar."""

import pytest
from PySide6.QtCore import Qt

from HeinoReader.editor.source_edit import (
    MarkdownSourceEdit,
    enter_indent,
    enter_prefix,
    is_quote_line,
    split_markers,
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
    ("line", "prefix", "text"),
    [
        ("> quoted", "> ", "quoted"),
        (">quoted", ">", "quoted"),
        (">  quoted", ">  ", "quoted"),
        ("> > nested", "> > ", "nested"),
        ("- item", "- ", "item"),
        ("* item", "* ", "item"),
        ("+ item", "+ ", "item"),
        ("1. item", "1. ", "item"),
        ("12) item", "12) ", "item"),
        ("  - nested", "  - ", "nested"),
        ("    - nested", "    - ", "nested"),
        ("> - quoted list", "> - ", "quoted list"),
        ("plain text", "", "plain text"),
        ("    indented code", "", "    indented code"),
        ("-not-a-list", "", "-not-a-list"),
        ("", "", ""),
    ],
)
def test_split_markers_separates_prefix_and_text(line, prefix, text):
    assert split_markers(line) == (prefix, text)


@pytest.mark.parametrize(
    ("line", "prefix"),
    [
        # Quotes continue with their marker, nested ones too.
        ("> quoted", "> "),
        ("> > nested", "> > "),
        # Bullets keep the character the user typed.
        ("- item", "- "),
        ("* item", "* "),
        ("+ item", "+ "),
        # Ordered lists count up, keeping the delimiter.
        ("1. item", "2. "),
        ("9. item", "10. "),
        ("3) item", "4) "),
        # Indentation and marker order survive.
        ("  - nested", "  - "),
        ("    - nested", "    - "),
        ("> - quoted list", "> - "),
        ("> 1. quoted item", "> 2. "),
        # Lines without a marker keep their alignment instead.
        ("plain text", ""),
        ("    indented code", "    "),
        ("", ""),
    ],
)
def test_enter_prefix_continues_the_block(line, prefix):
    assert enter_prefix(line) == prefix


@pytest.mark.parametrize(
    "line",
    [
        ">",
        "> ",
        "- ",
        "* ",
        "+ ",
        "1. ",
        "  2) ",
        "  - ",
        "> - ",
    ],
)
def test_enter_prefix_ends_an_empty_item(line):
    """On an item without text, Enter closes the list or quote."""
    assert enter_prefix(line) == ""


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


def test_enter_after_quote_continues_the_quote(qtbot):
    editor = make_editor(qtbot, "> quoted")
    press_enter(qtbot, editor)
    assert editor.toPlainText() == "> quoted\n> "
    assert editor.textCursor().positionInBlock() == 2


def test_enter_after_bullet_item_continues_the_list(qtbot):
    editor = make_editor(qtbot, "- first")
    press_enter(qtbot, editor)
    assert editor.toPlainText() == "- first\n- "
    assert editor.textCursor().positionInBlock() == 2


def test_enter_after_ordered_item_counts_up(qtbot):
    editor = make_editor(qtbot, "1. first")
    press_enter(qtbot, editor)
    assert editor.toPlainText() == "1. first\n2. "
    assert editor.textCursor().positionInBlock() == 3


def test_enter_on_empty_item_leaves_the_list(qtbot):
    editor = make_editor(qtbot, "- ")
    press_enter(qtbot, editor)
    assert editor.toPlainText() == "\n"
    assert editor.textCursor().positionInBlock() == 0


def test_enter_on_empty_quote_leaves_the_quote(qtbot):
    editor = make_editor(qtbot, "> ")
    press_enter(qtbot, editor)
    assert editor.toPlainText() == "\n"


def test_enter_on_empty_nested_item_leaves_the_list(qtbot):
    editor = make_editor(qtbot, "  - ")
    press_enter(qtbot, editor)
    assert editor.toPlainText() == "\n"


def test_enter_on_plain_text_adds_no_indent(qtbot):
    editor = make_editor(qtbot, "plain")
    press_enter(qtbot, editor)
    assert editor.toPlainText() == "plain\n"
    assert editor.textCursor().positionInBlock() == 0
