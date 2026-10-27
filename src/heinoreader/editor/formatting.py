"""Markdown text-formatting operations for the source editor.

The functions here work on a QTextCursor only, so they can be unit-tested
without any window. Every public operation wraps its changes in a single
edit block, so one Ctrl+Z undoes the complete action.
"""

from __future__ import annotations

import re

from PySide6.QtGui import QTextCursor

HEADING_RE = re.compile(r"^(#{1,6}) ")
BULLET_RE = re.compile(r"^[-*+] ")
NUMBERED_RE = re.compile(r"^\d+[.)] ")
QUOTE_RE = re.compile(r"^>\s?")


def selected_blocks(cursor: QTextCursor) -> list:
    """Blocks touched by the selection.

    A selection ending at the very start of a block does not include that
    block.
    """
    document = cursor.document()
    first = document.findBlock(cursor.selectionStart()).blockNumber()
    last = document.findBlock(cursor.selectionEnd()).blockNumber()
    if last > first:
        last_block = document.findBlockByNumber(last)
        if cursor.selectionEnd() == last_block.position():
            last -= 1
    return [
        document.findBlockByNumber(number)
        for number in range(first, last + 1)
    ]


def _text(document, start: int, end: int) -> str:
    """Plain text of [start, end); empty when the range is invalid."""
    if start < 0 or end > document.characterCount():
        return ""
    cursor = QTextCursor(document)
    cursor.setPosition(start)
    cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
    return cursor.selectedText()


def _replace_block(block, text: str) -> None:
    """Replace one block's text, keeping the block (and its newline).

    BlockUnderCursor would also select the paragraph separator, so the
    range is built by hand: block start to the end of the block text.
    Lengths are counted in UTF-16 units, as Qt does.
    """
    cursor = QTextCursor(block)
    end = block.position() + len(block.text().encode("utf-16-le")) // 2
    cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
    cursor.insertText(text)


def toggle_wrap(cursor: QTextCursor, marker: str, closing: str | None = None) -> None:
    """Wrap the selection in markers, or unwrap it when already wrapped.

    Without a selection the marker pair is inserted around the cursor;
    pressing the same command again while sitting between the markers
    removes them again.
    """
    closing = marker if closing is None else closing
    document = cursor.document()
    start, end = cursor.selectionStart(), cursor.selectionEnd()
    cursor.beginEditBlock()

    if start == end:
        opening = _text(document, start - len(marker), start)
        tail = _text(document, end, end + len(closing))
        if opening == marker and tail == closing:
            # Sitting between an inserted pair: remove both halves.
            cursor.setPosition(start)
            cursor.setPosition(start + len(closing), QTextCursor.MoveMode.KeepAnchor)
            cursor.removeSelectedText()
            cursor.setPosition(start - len(marker))
            cursor.setPosition(start, QTextCursor.MoveMode.KeepAnchor)
            cursor.removeSelectedText()
            cursor.setPosition(start - len(marker))
        else:
            cursor.insertText(marker + closing)
            cursor.setPosition(start + len(marker))
        cursor.endEditBlock()
        return

    opening = _text(document, start - len(marker), start)
    tail = _text(document, end, end + len(closing))
    surrounded = opening == marker and tail == closing
    if surrounded and len(marker) == len(closing) == 1:
        # Do not read part of a longer run (** or ~~) as a single pair.
        outer_left = _text(document, start - len(marker) - 1, start - len(marker))
        outer_right = _text(document, end + len(closing), end + len(closing) + 1)
        surrounded = outer_left != marker and outer_right != closing

    if surrounded:
        # Unwrap: remove the closing half first (it sits at the higher position).
        cursor.setPosition(end)
        cursor.setPosition(end + len(closing), QTextCursor.MoveMode.KeepAnchor)
        cursor.removeSelectedText()
        cursor.setPosition(start - len(marker))
        cursor.setPosition(start, QTextCursor.MoveMode.KeepAnchor)
        cursor.removeSelectedText()
        cursor.setPosition(start - len(marker))
        cursor.setPosition(end - len(marker), QTextCursor.MoveMode.KeepAnchor)
    else:
        # Wrap: closing half first, so the start position stays valid.
        cursor.setPosition(end)
        cursor.insertText(closing)
        cursor.setPosition(start)
        cursor.insertText(marker)
        cursor.setPosition(start + len(marker))
        cursor.setPosition(end + len(marker), QTextCursor.MoveMode.KeepAnchor)
    cursor.endEditBlock()


def set_heading(cursor: QTextCursor, level: int) -> None:
    """Set the selected lines to heading level 1-6 (0 = plain paragraph).

    Lines that already carry exactly this level fall back to a paragraph,
    so pressing the same shortcut twice toggles the heading off.
    """
    blocks = selected_blocks(cursor)
    texts = [block.text() for block in blocks]

    if level:
        content = [text for text in texts if text.strip()]
        if content and all(
            (match := HEADING_RE.match(text)) and len(match.group(1)) == level
            for text in content
        ):
            level = 0  # everything is already at this level: toggle off

    cursor.beginEditBlock()
    for block, text in zip(blocks, texts):
        if not text.strip():
            continue
        plain = HEADING_RE.sub("", text, count=1)
        new = f"{'#' * level} {plain}" if level else plain
        if new != text:
            _replace_block(block, new)
    cursor.endEditBlock()


def toggle_list(cursor: QTextCursor, ordered: bool = False) -> None:
    """Toggle a bullet (- ) or numbered (1. ) list on the selected lines.

    Adding a list strips the other list flavor first, so switching between
    bullet and numbered lists replaces the markers instead of stacking them.
    """
    pattern = NUMBERED_RE if ordered else BULLET_RE
    other = BULLET_RE if ordered else NUMBERED_RE
    blocks = selected_blocks(cursor)
    texts = [block.text() for block in blocks]
    content = [text for text in texts if text.strip()]
    removing = bool(content) and all(pattern.match(text) for text in content)

    cursor.beginEditBlock()
    index = 0
    for block, text in zip(blocks, texts):
        if not text.strip():
            continue
        index += 1
        if removing:
            new = pattern.sub("", text, count=1)
        elif pattern.match(text):
            new = text  # already an item of this flavor
        else:
            stripped = other.sub("", text, count=1)
            new = f"{index}. {stripped}" if ordered else f"- {stripped}"
        if new != text:
            _replace_block(block, new)
    cursor.endEditBlock()


def toggle_quote(cursor: QTextCursor) -> None:
    """Toggle a "> " block quote prefix on the selected lines."""
    blocks = selected_blocks(cursor)
    texts = [block.text() for block in blocks]
    content = [text for text in texts if text.strip()]
    removing = bool(content) and all(QUOTE_RE.match(text) for text in content)

    cursor.beginEditBlock()
    for block, text in zip(blocks, texts):
        if not text.strip():
            continue
        if removing:
            new = QUOTE_RE.sub("", text, count=1)
        elif QUOTE_RE.match(text):
            new = text
        else:
            new = f"> {text}"
        if new != text:
            _replace_block(block, new)
    cursor.endEditBlock()


# --------------------------------------------------------- insert elements

def insert_link(cursor: QTextCursor, url: str, label: str | None = None) -> None:
    """Insert a markdown link; the selection becomes the label when present.

    Without a label the brackets stay empty and the cursor is placed
    between them, so the label can be typed right away.
    """
    if label is None:
        label = cursor.selectedText()
    cursor.beginEditBlock()
    if label:
        cursor.insertText(f"[{label}]({url})")
    else:
        cursor.insertText(f"[]({url})")
        # Step back over "](url)" so the cursor sits between the brackets.
        cursor.setPosition(cursor.position() - (len(url) + 3))
    cursor.endEditBlock()


def insert_image(cursor: QTextCursor, url: str, alt: str = "") -> None:
    """Insert an image reference ![alt](url), replacing the selection."""
    cursor.beginEditBlock()
    cursor.insertText(f"![{alt}]({url})")
    cursor.endEditBlock()


def table_markdown(rows: int, columns: int) -> str:
    """Markdown for an empty table skeleton.

    ``rows`` counts the header row, ``columns`` the cells per row. The
    first row carries "Col N" placeholders, the second row is the
    separator, the remaining rows are empty body lines. The text ends
    with a newline, so it can be inserted directly.
    """
    rows = max(2, rows)
    columns = max(1, columns)
    header = "| " + " | ".join(f"Col {n}" for n in range(1, columns + 1)) + " |"
    separator = "| " + " | ".join("---" for _ in range(columns)) + " |"
    body = "| " + " | ".join("" for _ in range(columns)) + " |"
    lines = [header, separator] + [body] * (rows - 1)
    return "\n".join(lines) + "\n"


def insert_table(cursor: QTextCursor, rows: int, columns: int) -> None:
    """Insert an empty table, leaving the first header cell selected."""
    text = table_markdown(rows, columns)
    start = cursor.position()
    cursor.beginEditBlock()
    cursor.insertText(text)
    # Leave "Col 1" of the header selected so it can be typed over.
    cursor.setPosition(start + 2)  # past the leading "| "
    cursor.setPosition(start + 2 + len("Col 1"), QTextCursor.MoveMode.KeepAnchor)
    cursor.endEditBlock()
