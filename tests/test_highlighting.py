"""Tests for the Pygments seam and the debounced live preview."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from HeinoReader.highlighting import highlight_body

SRC = Path(__file__).resolve().parent.parent / "src"


@pytest.mark.parametrize(
    "code",
    [
        "plain text\n",
        "if a < b && c == \"x\":  # 'quoted'\n",
        "unicode äöü <tag> & \n\n",
        "  indented first line\n",
    ],
)
def test_plain_body_matches_pygments_text_lexer(code):
    """The escape path is not an approximation, it is the same output."""
    from pygments import highlight
    from pygments.formatters import HtmlFormatter
    from pygments.lexers import TextLexer

    formatter = HtmlFormatter(nowrap=True, cssclass="codehilite", style="friendly")
    expected = highlight(code, TextLexer(), formatter).rstrip("\n")
    assert highlight_body(code, "") == expected


def test_unknown_language_falls_back_to_plain_text():
    assert highlight_body("hello <world>", "no-such-language") == (
        "hello &lt;world&gt;"
    )


def test_known_language_is_highlighted():
    body = highlight_body("x = 1", "python")
    assert "class=" in body and "x" in body


def test_identical_blocks_are_served_from_the_cache():
    """Typing elsewhere re-renders unchanged blocks for free."""
    first = highlight_body("print(1)", "python")
    assert highlight_body("print(1)", "python") is first


def test_render_does_not_import_pygments():
    """Rendering markdown must not pay for Pygments unless there is code."""
    code = (
        "import sys\n"
        f"sys.path.insert(0, {str(SRC)!r})\n"
        "import HeinoReader.render as render\n"
        "render.markdown_to_html('# Title\\n\\nSome *text*.\\n', qt=True)\n"
        "loaded = [name for name in sys.modules if name.split('.')[0] == 'pygments']\n"
        "print(loaded)\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=True
    )
    assert result.stdout.strip() == "[]"
