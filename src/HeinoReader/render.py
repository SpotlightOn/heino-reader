"""Markdown to HTML rendering for the preview, plus relative path rewriting.

Everything in this module is GUI-free: it turns markdown text into HTML
and a stylesheet that the preview widget applies. Qt's built-in
``setMarkdown()`` renderer is avoided because its markdown coverage and
styling options are too limited for a faithful preview.
"""

from __future__ import annotations

import re
from html import escape
from pathlib import Path

from markdown_it import MarkdownIt
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import TextLexer, get_lexer_by_name
from pygments.util import ClassNotFound

# Pygments token colors for fenced code, kept in the same stylesheet.
_CODE_STYLE = "friendly"

_code_formatter = HtmlFormatter(nowrap=True, cssclass="codehilite", style=_CODE_STYLE)

# CommonMark (the GitHub flavor for the tested constructs) plus tables.
def _highlighted_fence(_renderer, tokens, index, options, env) -> str:
    """Render a fenced code block with Pygments; unknown languages stay plain."""
    token = tokens[index]
    words = token.info.strip().split()
    try:
        lexer = get_lexer_by_name(words[0]) if words else TextLexer()
    except ClassNotFound:
        lexer = TextLexer()
    body = highlight(token.content, lexer, _code_formatter).rstrip("\n")
    return f'<pre class="codehilite"><code>{body}</code></pre>\n'


def _code_block_qt(body: str) -> str:
    """Wrap highlighted code in a one-cell table for the Qt backend.

    Qt's rich text engine ignores padding and borders on block elements, so
    a ``<pre>`` with a background would sit flush against its surroundings.
    A table cell supports padding, border and background, which gives the
    code block its frame.
    """
    return (
        '<table class="codeblock" width="100%"><tr><td class="codebody">'
        f'<pre class="codehilite"><code>{body}</code></pre>'
        "</td></tr></table>\n"
    )


def _highlighted_fence_qt(_renderer, tokens, index, options, env) -> str:
    """Like _highlighted_fence, but join code lines with ``<br>``.

    Qt's rich text engine creates one text block per newline and paints a
    separate background for each, which shows up as one grey bar per line.
    A single block (``<br>``) keeps the background continuous.
    """
    token = tokens[index]
    words = token.info.strip().split()
    try:
        lexer = get_lexer_by_name(words[0]) if words else TextLexer()
    except ClassNotFound:
        lexer = TextLexer()
    body = highlight(token.content, lexer, _code_formatter).rstrip("\n")
    return _code_block_qt(body.replace("\n", "<br>"))


def _indented_code_qt(_renderer, tokens, index, options, env) -> str:
    """Indented code block for the Qt backend: one block, like fenced code.

    Without the ``<br>`` join Qt paints a separate grey bar per line, which
    looks like a stack of stripes instead of one code block.
    """
    body = escape(tokens[index].content.rstrip("\n")).replace("\n", "<br>")
    return _code_block_qt(body)


def _quote_open_qt(_renderer, tokens, index, options, env) -> str:
    """Start a block quote as a table cell, so it gets padding and a bar."""
    return '<table class="quote" width="100%"><tr><td class="quotebody">'


def _quote_close_qt(_renderer, tokens, index, options, env) -> str:
    """End the block quote table started by ``_quote_open_qt``."""
    return "</td></tr></table>\n"


def _make_parser(qt: bool) -> MarkdownIt:
    parser = MarkdownIt("commonmark", {"html": True}).enable("table")
    parser.add_render_rule(
        "fence", _highlighted_fence_qt if qt else _highlighted_fence
    )
    if qt:
        parser.add_render_rule("code_block", _indented_code_qt)
        parser.add_render_rule("blockquote_open", _quote_open_qt)
        parser.add_render_rule("blockquote_close", _quote_close_qt)
    return parser


_parser = _make_parser(qt=False)
_qt_parser = _make_parser(qt=True)

_CSS_PATH = Path(__file__).with_name("preview.css")
PREVIEW_CSS = _CSS_PATH.read_text(encoding="utf-8")


def markdown_to_html(text: str, qt: bool = False) -> str:
    """Render a markdown document to an HTML fragment.

    ``qt=True`` produces markup for the QTextEdit backend (code lines joined
    with ``<br>`` so backgrounds stay continuous).
    """
    return (_qt_parser if qt else _parser).render(text)


def render_html_document(text: str) -> str:
    """Render markdown to a complete HTML document for the web preview."""
    body = markdown_to_html(text)
    return (
        "<!DOCTYPE html><html><head><meta charset=\"utf-8\">"
        f"<style>{PREVIEW_CSS}</style></head><body>{body}</body></html>"
    )


# Code regions must not be touched when rewriting paths below.
_CODE_RE = re.compile(
    r"^(?:`{3,}|~{3,}).*?^(?:`{3,}|~{3,})[ \t]*$"  # fenced code block
    r"|`[^`\n]+`"  # inline code span
    r"|^(?:[ \t]{4,}[^\n]*\n?)+",  # indented code block
    re.MULTILINE | re.DOTALL,
)
_INLINE_LINK_RE = re.compile(r"(!?\[[^\]\n]*\]\()([^)]*)(\))")
_REF_DEF_RE = re.compile(r"(^[ \t]*\[[^\]\n]+\]:[ \t]*)([^\n]+)$", re.MULTILINE)
_HTML_IMG_RE = re.compile(
    r"(<img\b[^>]*?\bsrc\s*=\s*[\"'])([^\"']+)([\"'])", re.IGNORECASE
)


def _has_scheme(url: str) -> bool:
    """True for external targets such as http:, data: or mailto:."""
    if url.startswith(("#", "//")):
        return True
    return bool(re.match(r"^[A-Za-z][\w+.-]*:", url))


def _resolve_url(url: str, base_dir: Path) -> str:
    """Make a relative local path absolute, keeping external URLs as-is."""
    bracketed = url.startswith("<") and url.endswith(">") and len(url) > 2
    target = url[1:-1] if bracketed else url
    if not target or _has_scheme(target):
        return url
    resolved = str((base_dir / target).resolve())
    if bracketed or " " in resolved or "(" in resolved or ")" in resolved:
        return f"<{resolved}>"
    return resolved


def _rewrite_destination(dest: str, base_dir: Path) -> str:
    """Rewrite the url part of a markdown destination, keeping its title."""
    stripped = dest.lstrip()
    lead = dest[: len(dest) - len(stripped)]
    if stripped.startswith("<"):
        end = stripped.find(">")
        if end != -1:
            return lead + _resolve_url(stripped[: end + 1], base_dir) + stripped[end + 1 :]
    match = re.match(r"(\S+)([\s\S]*)", stripped)
    if not match:
        return dest
    return lead + _resolve_url(match.group(1), base_dir) + match.group(2)


def _resolve_relative_paths(markdown_text: str, base_dir: Path) -> str:
    """Point relative image/link targets at the markdown file's directory.

    Qt resolves relative paths against the process working directory,
    which is usually not the directory of the document.
    """
    def rewrite_segment(segment: str) -> str:
        segment = _INLINE_LINK_RE.sub(
            lambda m: m.group(1) + _rewrite_destination(m.group(2), base_dir) + m.group(3),
            segment,
        )
        segment = _REF_DEF_RE.sub(
            lambda m: m.group(1) + _rewrite_destination(m.group(2), base_dir),
            segment,
        )
        segment = _HTML_IMG_RE.sub(
            lambda m: m.group(1) + _resolve_url(m.group(2), base_dir) + m.group(3),
            segment,
        )
        return segment

    # Only rewrite outside of code blocks and inline code spans.
    parts: list[str] = []
    position = 0
    for match in _CODE_RE.finditer(markdown_text):
        parts.append(rewrite_segment(markdown_text[position : match.start()]))
        parts.append(match.group(0))
        position = match.end()
    parts.append(rewrite_segment(markdown_text[position:]))
    return "".join(parts)
