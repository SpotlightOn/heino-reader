"""Validation of files that heinoreader is willing to open.

The viewer is a markdown reader, not a binary/hex viewer. Dropping an
image, an archive or any other binary onto the window must not dump bytes
into the text engine, so every entry point (drag & drop, the Open dialog,
the command line) goes through these checks.
"""

from __future__ import annotations

from pathlib import Path

# Formats that are treated as markdown.
MARKDOWN_SUFFIXES = frozenset(
    {".md", ".markdown", ".mdown", ".mkd", ".mdx", ".mdtxt", ".mdtext"}
)
# Plain text is harmless and useful to preview, so it is accepted too.
TEXT_SUFFIXES = MARKDOWN_SUFFIXES | {".txt", ".text"}

# Refuse absurdly large files instead of exhausting memory.
MAX_FILE_SIZE = 10 * 1024 * 1024
_SAMPLE_SIZE = 8192


def is_supported_path(path: Path) -> bool:
    """True when the file name suggests text/markdown we can display."""
    return path.suffix.lower() in TEXT_SUFFIXES


def looks_binary(path: Path, sample_size: int = _SAMPLE_SIZE) -> bool:
    """True when the first bytes contain a NUL, the usual binary marker."""
    try:
        with path.open("rb") as handle:
            sample = handle.read(sample_size)
    except OSError:
        return False
    return b"\x00" in sample


def rejection_reason(
    path: Path, max_size: int = MAX_FILE_SIZE
) -> str | None:
    """Why ``path`` must not be opened, or None when it is acceptable."""
    try:
        if not path.exists():
            return "the file does not exist"
        if not path.is_file():
            return "it is not a regular file"
        if path.stat().st_size > max_size:
            return f"it is larger than {max_size // (1024 * 1024)} MB"
    except OSError as error:
        return f"it cannot be read ({error})"
    if not is_supported_path(path):
        return f"'.{path.suffix.lstrip('.')}' is not a supported text format"
    if looks_binary(path):
        return "it looks like binary data"
    return None
