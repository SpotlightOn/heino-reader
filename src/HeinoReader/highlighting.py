"""Syntax highlighting for fenced code, isolated behind one seam.

Pygments is a heavy import that most documents never need: a markdown file
without code stays a plain-markdown render. It is therefore imported on first
use instead of at module level, and the highlighted body is cached by content,
so re-rendering an unchanged block — which the live preview does on every
keystroke — costs nothing.
"""

from __future__ import annotations

from functools import cache, lru_cache
from html import escape

# Pygments token colors for fenced code, matched by preview.css.
_STYLE = "friendly"


def highlight_body(code: str, info: str) -> str:
    """Return the HTML body of one code block, without wrapper markup.

    ``info`` is the fence's info string (``"python"``), so a fence without a
    language is escaped rather than handed to a lexer.
    """
    words = info.strip().split()
    if not words:
        return _plain_body(code)
    return _highlighted_body(code, words[0])


def _plain_body(code: str) -> str:
    """Code escaped exactly the way Pygments' TextLexer escapes it.

    ``quote=False`` is the whole difference: Pygments escapes ``&``, ``<``
    and ``>`` but leaves quotes alone, while ``html.escape`` would turn them
    into entities. tests/test_highlighting.py pins that equality.
    """
    return escape(code.rstrip("\n"), quote=False)


@lru_cache(maxsize=128)
def _highlighted_body(code: str, language: str) -> str:
    """Highlighted body for one block, cached by content and language."""
    from pygments import highlight
    from pygments.lexers import get_lexer_by_name
    from pygments.util import ClassNotFound

    try:
        lexer = get_lexer_by_name(language)
    except ClassNotFound:
        return _plain_body(code)
    return highlight(code, lexer, _formatter()).rstrip("\n")


@cache
def _formatter():
    """The Pygments formatter, built once and only when it is first needed."""
    from pygments.formatters import HtmlFormatter

    return HtmlFormatter(nowrap=True, cssclass="codehilite", style=_STYLE)
