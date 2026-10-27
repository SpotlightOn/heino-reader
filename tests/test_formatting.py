"""Unit tests for the pure markdown formatting operations."""

import pytest
from PySide6.QtGui import QTextCursor, QTextDocument

from HeinoReader import formatting


@pytest.fixture
def doc():
    return QTextDocument()


def cursor_at(document, text, start, end):
    """Build a cursor on a document pre-filled with text."""
    document.setPlainText(text)
    cursor = QTextCursor(document)
    cursor.setPosition(start)
    cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
    return cursor


def plain(document):
    return document.toPlainText()


# ------------------------------------------------------------- toggle_wrap

def test_wrap_wraps_the_selection(doc):
    cursor = cursor_at(doc, "hello world", 0, 5)
    formatting.toggle_wrap(cursor, "**")
    assert plain(doc) == "**hello** world"
    assert cursor.selectedText() == "hello"


def test_wrap_unwraps_an_already_wrapped_selection(doc):
    cursor = cursor_at(doc, "**hello** world", 2, 7)
    formatting.toggle_wrap(cursor, "**")
    assert plain(doc) == "hello world"
    assert cursor.selectedText() == "hello"


def test_wrap_italic_inside_bold_does_not_misread_the_marker(doc):
    # "hello" sits inside "**hello**"; a single "*" must not be read as
    # part of that run, so the text gets wrapped, not unwrapped.
    cursor = cursor_at(doc, "**hello** world", 2, 7)
    formatting.toggle_wrap(cursor, "*")
    assert plain(doc) == "***hello*** world"


def test_wrap_without_selection_places_cursor_between_markers(doc):
    document = doc
    document.setPlainText("")
    cursor = QTextCursor(document)
    formatting.toggle_wrap(cursor, "**")
    assert plain(document) == "****"
    assert cursor.position() == 2


def test_wrap_between_markers_removes_them_again(doc):
    doc.setPlainText("****")
    cursor = QTextCursor(doc)
    cursor.setPosition(2)
    formatting.toggle_wrap(cursor, "**")
    assert plain(doc) == ""
    assert cursor.position() == 0


def test_wrap_is_a_single_undo_step(doc):
    cursor = cursor_at(doc, "hello world", 0, 5)
    formatting.toggle_wrap(cursor, "**")
    doc.undo()
    assert plain(doc) == "hello world"


def test_wrap_supports_asymmetric_markers(doc):
    cursor = cursor_at(doc, "click me", 0, 8)
    formatting.toggle_wrap(cursor, "<u>", "</u>")
    assert plain(doc) == "<u>click me</u>"
    doc.undo()
    assert plain(doc) == "click me"


# ------------------------------------------------------------- set_heading

def test_heading_promotes_a_line(doc):
    cursor = cursor_at(doc, "title", 0, 0)
    formatting.set_heading(cursor, 2)
    assert plain(doc) == "## title"


def test_heading_replaces_an_existing_level(doc):
    cursor = cursor_at(doc, "### title", 4, 4)
    formatting.set_heading(cursor, 1)
    assert plain(doc) == "# title"


def test_heading_same_level_toggles_off(doc):
    cursor = cursor_at(doc, "## title", 3, 3)
    formatting.set_heading(cursor, 2)
    assert plain(doc) == "title"


def test_heading_level_zero_clears(doc):
    cursor = cursor_at(doc, "# title", 2, 2)
    formatting.set_heading(cursor, 0)
    assert plain(doc) == "title"


def test_heading_applies_to_every_selected_line(doc):
    cursor = cursor_at(doc, "one\ntwo\nthree", 0, 13)
    formatting.set_heading(cursor, 2)
    assert plain(doc) == "## one\n## two\n## three"


def test_heading_is_a_single_undo_step(doc):
    cursor = cursor_at(doc, "one\ntwo", 0, 7)
    formatting.set_heading(cursor, 1)
    doc.undo()
    assert plain(doc) == "one\ntwo"


# ------------------------------------------------------------- toggle_list

def test_bullet_list_adds_markers(doc):
    cursor = cursor_at(doc, "one\ntwo", 0, 7)
    formatting.toggle_list(cursor)
    assert plain(doc) == "- one\n- two"


def test_bullet_list_removes_existing_markers(doc):
    cursor = cursor_at(doc, "- one\n- two", 0, 11)
    formatting.toggle_list(cursor)
    assert plain(doc) == "one\ntwo"


def test_numbered_list_numbers_the_lines(doc):
    cursor = cursor_at(doc, "one\ntwo\nthree", 0, 13)
    formatting.toggle_list(cursor, ordered=True)
    assert plain(doc) == "1. one\n2. two\n3. three"


def test_switching_to_numbered_replaces_bullets(doc):
    cursor = cursor_at(doc, "- one\n- two", 0, 11)
    formatting.toggle_list(cursor, ordered=True)
    assert plain(doc) == "1. one\n2. two"


def test_list_ignores_blank_lines_when_numbering(doc):
    cursor = cursor_at(doc, "one\n\ntwo", 0, 8)
    formatting.toggle_list(cursor, ordered=True)
    assert plain(doc) == "1. one\n\n2. two"


# ------------------------------------------- block commands on an empty line


def empty_line_cursor(document, text):
    """Cursor at the end of a document, i.e. on a fresh empty line."""
    document.setPlainText(text)
    cursor = QTextCursor(document)
    cursor.movePosition(QTextCursor.MoveOperation.End)
    return cursor


def test_bullet_list_on_an_empty_line_starts_the_list(doc):
    cursor = empty_line_cursor(doc, "")
    formatting.toggle_list(cursor)
    assert plain(doc) == "- "
    assert cursor.position() == 2


def test_numbered_list_on_an_empty_line_starts_at_one(doc):
    cursor = empty_line_cursor(doc, "")
    formatting.toggle_list(cursor, ordered=True)
    assert plain(doc) == "1. "
    assert cursor.position() == 3


def test_bullet_list_on_an_empty_line_continues_the_list_above(doc):
    cursor = empty_line_cursor(doc, "- one\n")
    formatting.toggle_list(cursor)
    assert plain(doc) == "- one\n- "


def test_numbered_list_on_an_empty_line_counts_up(doc):
    cursor = empty_line_cursor(doc, "1. one\n2. two\n")
    formatting.toggle_list(cursor, ordered=True)
    assert plain(doc) == "1. one\n2. two\n3. "


def test_nested_list_on_an_empty_line_keeps_indent_and_bullet(doc):
    cursor = empty_line_cursor(doc, "  * nested\n")
    formatting.toggle_list(cursor)
    assert plain(doc) == "  * nested\n  * "


def test_starting_a_list_twice_removes_the_marker(doc):
    cursor = empty_line_cursor(doc, "- ")
    formatting.toggle_list(cursor)
    assert plain(doc) == ""
    assert cursor.position() == 0


def test_quote_on_an_empty_line_starts_a_quote(doc):
    cursor = empty_line_cursor(doc, "")
    formatting.toggle_quote(cursor)
    assert plain(doc) == "> "
    assert cursor.position() == 2


def test_heading_on_an_empty_line_starts_a_heading(doc):
    cursor = empty_line_cursor(doc, "")
    formatting.set_heading(cursor, 3)
    assert plain(doc) == "### "
    assert cursor.position() == 4


def test_starting_a_block_on_an_empty_line_is_one_undo_step(doc):
    cursor = empty_line_cursor(doc, "text\n")
    formatting.toggle_list(cursor, ordered=True)
    doc.undo()
    assert plain(doc) == "text\n"


# ------------------------------------------------------------- toggle_quote

def test_quote_adds_the_prefix(doc):
    cursor = cursor_at(doc, "one\ntwo", 0, 7)
    formatting.toggle_quote(cursor)
    assert plain(doc) == "> one\n> two"


def test_quote_removes_existing_prefixes(doc):
    cursor = cursor_at(doc, "> one\n> two", 0, 11)
    formatting.toggle_quote(cursor)
    assert plain(doc) == "one\ntwo"


# --------------------------------------------------------- selected_blocks

def test_selection_ending_at_block_start_excludes_that_block(doc):
    cursor = cursor_at(doc, "one\ntwo\nthree", 0, 4)
    blocks = formatting.selected_blocks(cursor)
    assert [block.text() for block in blocks] == ["one"]


# ----------------------------------------------------------- insert_link

def test_link_uses_the_selection_as_label(doc):
    cursor = cursor_at(doc, "see the docs", 4, 7)  # "the"
    formatting.insert_link(cursor, "https://example.com")
    assert plain(doc) == "see [the](https://example.com) docs"


def test_link_without_selection_leaves_empty_brackets(doc):
    doc.setPlainText("")
    cursor = QTextCursor(doc)
    formatting.insert_link(cursor, "https://example.com")
    assert plain(doc) == "[](https://example.com)"
    assert cursor.position() == 1, "cursor should sit between the brackets"


def test_link_accepts_an_explicit_label(doc):
    cursor = cursor_at(doc, "", 0, 0)
    formatting.insert_link(cursor, "https://example.com", "Docs")
    assert plain(doc) == "[Docs](https://example.com)"


def test_link_is_a_single_undo_step(doc):
    cursor = cursor_at(doc, "hello", 0, 5)
    formatting.insert_link(cursor, "https://example.com")
    doc.undo()
    assert plain(doc) == "hello"


# ---------------------------------------------------------- insert_image

def test_image_inserts_a_reference(doc):
    doc.setPlainText("")
    cursor = QTextCursor(doc)
    formatting.insert_image(cursor, "img/pic.png", "A picture")
    assert plain(doc) == "![A picture](img/pic.png)"


def test_image_defaults_to_an_empty_alt(doc):
    doc.setPlainText("")
    cursor = QTextCursor(doc)
    formatting.insert_image(cursor, "img/pic.png")
    assert plain(doc) == "![](img/pic.png)"


# -------------------------------------------------------- table_markdown

def test_table_markdown_builds_header_separator_and_body(doc):
    text = formatting.table_markdown(3, 2)
    assert text.splitlines() == [
        "| Col 1 | Col 2 |",
        "| --- | --- |",
        "|  |  |",
        "|  |  |",
    ]
    assert text.endswith("\n")


def test_table_markdown_clamps_to_sensible_sizes(doc):
    text = formatting.table_markdown(1, 0)
    lines = text.splitlines()
    assert lines[0] == "| Col 1 |"
    assert len(lines) == 3, "at least header, separator and one body row"


# ----------------------------------------------------------- insert_table

def test_insert_table_places_a_skeleton_and_selects_the_first_cell(doc):
    doc.setPlainText("")
    cursor = QTextCursor(doc)
    formatting.insert_table(cursor, 2, 2)
    assert plain(doc) == (
        "| Col 1 | Col 2 |\n"
        "| --- | --- |\n"
        "|  |  |\n"
    )
    assert cursor.selectedText() == "Col 1"


def test_insert_table_is_a_single_undo_step(doc):
    doc.setPlainText("")
    cursor = QTextCursor(doc)
    formatting.insert_table(cursor, 2, 2)
    doc.undo()
    assert plain(doc) == ""
