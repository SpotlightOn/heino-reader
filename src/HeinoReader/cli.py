"""Command line entry point: parse arguments, start Qt, show the window."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from .files import rejection_reason
from .icons import ICON_PATH
from .viewer import RENDERERS
from .window import ViewerWindow


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
            "renderer: 'qt' (QTextEdit, the default) or 'web' "
            "(QtWebEngine, loaded only when selected); defaults to the last "
            "used renderer, initially 'qt'"
        ),
    )
    args = parser.parse_args(argv)

    if args.file is not None:
        reason = rejection_reason(args.file)
        if reason is not None:
            print(
                f"heino-reader: cannot open {args.file}: {reason}",
                file=sys.stderr,
            )
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
