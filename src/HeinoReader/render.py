"""Markdown to HTML rendering for the preview, plus relative path rewriting.

Everything in this module is GUI-free: it turns markdown text into HTML
and a stylesheet that the preview widget applies. Qt's built-in
``setMarkdown()`` renderer is avoided because its markdown coverage and
styling options are too limited for a faithful preview.
"""

from __future__ import annotations

import re
from functools import lru_cache
from html import escape
from pathlib import Path

from markdown_it import MarkdownIt

from .highlighting import highlight_body


# CommonMark (the GitHub flavor for the tested constructs) plus tables.
def _highlighted_fence(_renderer, tokens, index, options, env) -> str:
    """Render a fenced code block; unknown languages stay plain."""
    body = highlight_body(tokens[index].content, tokens[index].info)
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
    body = highlight_body(tokens[index].content, tokens[index].info)
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


def _make_parser(*, qt: bool) -> MarkdownIt:
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

# One CSS pixel is 1/96 inch, one point is 1/72 inch.
_CSS_PX_PER_PT = 96.0 / 72.0

# Used when the stylesheet declares no usable body size (or declares it in a
# relative unit, which has no base to resolve against outside a browser).
_FALLBACK_POINT_SIZE = 12.0

_FONT_FAMILY_RE = re.compile(r"font-family\s*:\s*([^;]+);", re.IGNORECASE)
_FONT_SIZE_RE = re.compile(r"font-size\s*:\s*([\d.]+)\s*(px|pt)\b", re.IGNORECASE)
_LINE_HEIGHT_RE = re.compile(r"line-height\s*:\s*([\d.]+)\s*(%|px|pt)?", re.IGNORECASE)
_CSS_RULE_RE = re.compile(r"([^{}]+)\{([^}]*)\}")

_HEADING_SELECTORS = frozenset({"h1", "h2", "h3", "h4", "h5", "h6"})


@lru_cache(maxsize=8)
def _declarations(css: str, selectors: frozenset[str]) -> str:
    """All declarations of every rule whose selector list names one of them.

    Rules are merged in file order, so a later declaration wins — the same way
    a browser would apply them. ``preview.css`` opens with
    ``html, body { margin: 0; padding: 0 }`` before the real body rule, and
    both have to be taken into account.

    Cached: the stylesheet is a module constant, yet these helpers are called
    several times per render and per zoom step.
    """
    blocks = [
        declarations
        for selector_list, declarations in _CSS_RULE_RE.findall(css)
        if any(
            selector.strip().lower() in selectors
            for selector in selector_list.split(",")
        )
    ]
    return "\n".join(blocks)


def preview_font_families(css: str | None = None) -> list[str]:
    """Font families of the preview theme, in fallback order."""
    block = _declarations(PREVIEW_CSS if css is None else css, frozenset({"body"}))
    match = _FONT_FAMILY_RE.search(block)
    if match is None:
        return []
    families = (part.strip().strip("\"'") for part in match.group(1).split(","))
    return [family for family in families if family]


def preview_body_point_size(css: str | None = None) -> float:
    """Body font size of the preview theme, in points.

    Qt sizes fonts in points and scales them with the screen DPI, while CSS
    pixel sizes are not DPI aware inside ``QTextDocument``. The stylesheet
    therefore keeps its px declarations for the WebEngine backend, and only
    the Qt backend converts the body size once: Qt does the rest.
    """
    block = _declarations(PREVIEW_CSS if css is None else css, frozenset({"body"}))
    match = _FONT_SIZE_RE.search(block)
    if match is None:
        return _FALLBACK_POINT_SIZE
    value, unit = float(match.group(1)), match.group(2).lower()
    if unit == "pt":
        return value
    return value / _CSS_PX_PER_PT


def preview_line_height(*, heading: bool = False, css: str | None = None) -> float | None:
    """CSS ``line-height`` of headings or body text, as a factor.

    CSS multiplies the font size (``1.55`` = 1.55 × font size); Qt reads the
    same number as a percentage of the font's natural line height. The factor
    returned here is the CSS meaning, the Qt backend converts it. ``None``
    means the stylesheet does not declare one.
    """
    selectors = _HEADING_SELECTORS if heading else frozenset({"body"})
    block = _declarations(PREVIEW_CSS if css is None else css, selectors)
    match = _LINE_HEIGHT_RE.search(block)
    if match is None:
        return None
    value, unit = float(match.group(1)), (match.group(2) or "").lower()
    if unit == "%":
        return value / 100.0
    if unit:
        # A fixed length (px/pt) does not scale with the font; unsupported.
        return None
    return value


def markdown_to_html(text: str, *, qt: bool = False) -> str:
    """Render a markdown document to an HTML fragment.

    ``qt=True`` produces markup for the QTextEdit backend (code lines joined
    with ``<br>`` so backgrounds stay continuous).
    """
    return (_qt_parser if qt else _parser).render(text)


# A line-height declaration with its value and optional unit.
_LINE_HEIGHT_DECL_RE = re.compile(
    r"(?<![\w-])(line-height\s*:\s*)([\d.]+)\s*(%|px|pt)?", re.IGNORECASE
)

# Block elements whose line height has to come from an explicit rule: Qt's
# setHtml() parses a fragment without <body>, so the body rule never matches.
_BODY_BLOCK_SELECTORS = "p, li, dd, dt, td, th, blockquote"


def _qt_percent(value: float, unit: str, pixel_per_natural: float) -> float:
    """CSS line-height value as the percentage Qt expects for it.

    Qt reads the number as a percentage of the font's natural line height,
    CSS as a multiple of the font size, so the two differ by the font's
    natural height per pixel.
    """
    factor = value / 100.0 if unit == "%" else value
    return factor * pixel_per_natural * 100.0


def qt_stylesheet(css: str | None = None, pixel_per_natural: float = 1.0) -> str:
    """The preview stylesheet with line heights Qt can use as they are.

    ``preview.css`` states line heights the CSS way (``1.55``, ``125%``). Qt
    parses the same number as a share of the font's natural line height and
    would render the text far too tight, so every declaration is rewritten as
    the equivalent percentage. Fixed lengths (``px``, ``pt``) do not scale
    with the font size and are left alone.

    Because a ``body`` rule never matches in a fragment, the body line height
    is additionally spelled out on the block elements. ``pixel_per_natural``
    comes from the document font: ``QFontInfo.pixelSize() /
    QFontMetricsF.height()``.
    """
    sheet = PREVIEW_CSS if css is None else css

    def rewrite(match: re.Match[str]) -> str:
        unit = (match.group(3) or "").lower()
        if unit in {"px", "pt"}:
            return match.group(0)
        percent = _qt_percent(float(match.group(2)), unit, pixel_per_natural)
        return f"{match.group(1)}{percent:.2f}%"

    corrected = _LINE_HEIGHT_DECL_RE.sub(rewrite, sheet)
    body = preview_line_height(css=sheet)
    if body is None:
        return corrected
    percent = _qt_percent(body, "", pixel_per_natural)
    return f"{corrected}\n{_BODY_BLOCK_SELECTORS} {{ line-height: {percent:.2f}% }}"


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
