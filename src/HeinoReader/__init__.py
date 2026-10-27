"""Heino Reader - a fast document viewer for markdown files.

Heino Reader displays markdown files read-only as HTML. By default the
lightweight Qt text renderer paints the document; the heavier QtWebEngine
backend is only imported and created when it is actually used. It can be
started with a file path, so it can be bound to the .md extension in file
managers such as Dolphin.

Usage:
    heino-reader [FILE]
    python -m HeinoReader [FILE]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from .editor import (
    LineNumberArea,
    LineNumberGutter,
    MarkdownHighlighter,
    MarkdownSourceEdit,
    ask_image,
    ask_link_url,
    ask_table_size,
    formatting,
)
from .files import rejection_reason
from .icons import APP_DIR, ICON_PATH, ICONS_DIR
from .icons import _glyph_icon as _glyph_icon
from .icons import _material_icon as _material_icon
from .layout import DOCUMENT_MARGIN, MAX_CONTENT_WIDTH, content_layout
from .qtview import QtMarkdownView
from .render import (
    PREVIEW_CSS,
    _resolve_relative_paths,
    _resolve_url,
    markdown_to_html,
    preview_body_point_size,
    preview_font_families,
    preview_line_height,
    render_html_document,
)
from .utils import open_external
from .window import (
    ABOUT_TEXT,
    DEFAULT_RENDERER,
    EDIT_MODE_WIDTH,
    PLACEHOLDER_MD,
    RENDERER_QT,
    RENDERER_WEB,
    RENDERERS,
    ViewerWindow,
    ask_open_file,
    create_markdown_view,
    show_about,
    web_engine_available,
)

__all__ = [
    "ABOUT_TEXT",
    "APP_DIR",
    "DEFAULT_RENDERER",
    "DOCUMENT_MARGIN",
    "EDIT_MODE_WIDTH",
    "ICONS_DIR",
    "MAX_CONTENT_WIDTH",
    "PLACEHOLDER_MD",
    "PREVIEW_CSS",
    "RENDERERS",
    "RENDERER_QT",
    "RENDERER_WEB",
    "LineNumberArea",
    "LineNumberGutter",
    "MarkdownHighlighter",
    "MarkdownSourceEdit",
    "QtMarkdownView",
    "ViewerWindow",
    "_resolve_relative_paths",
    "_resolve_url",
    "ask_image",
    "ask_link_url",
    "ask_open_file",
    "ask_table_size",
    "content_layout",
    "create_markdown_view",
    "formatting",
    "main",
    "markdown_to_html",
    "open_external",
    "preview_body_point_size",
    "preview_font_families",
    "preview_line_height",
    "render_html_document",
    "show_about",
    "web_engine_available",
]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="heino-reader",
        description="A fast document viewer for markdown files.",
    )
    parser.add_argument(
        "file",
        nargs="?",
        type=Path,
        help="markdown file to display",
    )
    parser.add_argument(
        "--renderer",
        choices=RENDERERS,
        default=None,
        help=(
            "preview backend: 'qt' (QTextEdit, the default) or 'web' "
            "(QtWebEngine, loaded only when selected); defaults to the last "
            "used renderer, initially 'qt'"
        ),
    )
    args = parser.parse_args(argv)

    if args.file is not None:
        reason = rejection_reason(args.file)
        if reason is not None:
            print(f"heino-reader: cannot open {args.file}: {reason}", file=sys.stderr)
            return 2

    app = QApplication([sys.argv[0]])
    app.setApplicationName("heino-reader")
    app.setApplicationDisplayName("Heino Reader")
    app.setDesktopFileName("heino-reader")
    if ICON_PATH.is_file():
        app.setWindowIcon(QIcon(str(ICON_PATH)))
    window = ViewerWindow(args.file, renderer=args.renderer)
    window.show()
    return app.exec()
