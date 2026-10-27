"""Small shared helpers."""

from __future__ import annotations

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices


def open_external(url: QUrl) -> None:
    """Open a URL with the system default handler (xdg-open)."""
    QDesktopServices.openUrl(url)
