"""The source markdown editor subsystem.

This subpackage groups everything that makes up the editable code pane:
the plain-text editor widget with its line-number gutter, the syntax
highlighter, and the GUI-free formatting operations that rewrite markdown
at the cursor. The viewer window imports these pieces from here; nothing
in this package depends back on the top-level Heino Reader module.
"""

from __future__ import annotations

from . import formatting
from .dialogs import ask_image, ask_link_url, ask_table_size
from .highlighter import MarkdownHighlighter
from .line_numbers import LineNumberArea, LineNumberGutter
from .source_edit import MarkdownSourceEdit

__all__ = [
    "LineNumberArea",
    "LineNumberGutter",
    "MarkdownHighlighter",
    "MarkdownSourceEdit",
    "ask_image",
    "ask_link_url",
    "ask_table_size",
    "formatting",
]
