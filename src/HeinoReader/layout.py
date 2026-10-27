"""Text column layout shared by the preview backends."""

from __future__ import annotations

DOCUMENT_MARGIN = 16.0
MAX_CONTENT_WIDTH = 760


def content_layout(viewport_width: int) -> tuple[int, int]:
    """Return (content width, side margin) for the centred text column.

    Below MAX_CONTENT_WIDTH the content uses the full width; above it the
    column stays at MAX_CONTENT_WIDTH and the remainder becomes an equal
    left/right margin.
    """
    available = viewport_width - 2 * DOCUMENT_MARGIN
    if available <= 0:
        return 0, int(DOCUMENT_MARGIN)
    content = min(available, MAX_CONTENT_WIDTH)
    extra = max(0, (available - content) // 2)
    return content, int(DOCUMENT_MARGIN) + extra
