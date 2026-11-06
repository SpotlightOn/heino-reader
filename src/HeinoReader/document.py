"""The open document: its file, its text and the unsaved-changes state.

Holds no Qt widget, so the save and discard rules can be exercised without a
window. The window keeps the widgets in sync with these plain values.
"""

from __future__ import annotations

import sys
from pathlib import Path


class Document:
    """Markdown text, the file it belongs to and whether they still match."""

    def __init__(self, markdown: str = "") -> None:
        self.path: Path | None = None
        self.markdown = markdown
        self.saved_text = markdown

    @property
    def name(self) -> str:
        """File name for prompts, or a stand-in before the first save."""
        return self.path.name if self.path is not None else "This document"

    @property
    def is_modified(self) -> bool:
        """True while the text differs from what the file holds.

        Comparing texts instead of latching a flag means undoing back to the
        saved state counts as clean again.
        """
        return self.markdown != self.saved_text

    def read(self, path: Path) -> bool:
        """Load ``path`` and make it the current file; False on a read error."""
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError as error:
            print(f"heino-reader: cannot read {path}: {error}", file=sys.stderr)
            return False
        self.markdown = text
        self.saved_text = text
        self.path = path
        return True

    def write(self, path: Path) -> bool:
        """Write the current text to ``path``; False on an OS error."""
        try:
            path.write_text(self.markdown, encoding="utf-8")
        except OSError as error:
            print(f"heino-reader: cannot save {path}: {error}", file=sys.stderr)
            return False
        self.saved_text = self.markdown
        return True

    def adopt(self, path: Path) -> None:
        """Make ``path`` the file this text belongs to."""
        self.path = path
