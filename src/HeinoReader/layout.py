"""Text column layout shared by the preview backends."""

from __future__ import annotations

# Side margin around the text column. The top and bottom margin is larger
# and follows the window height, see vertical_margins().
DOCUMENT_MARGIN = 16.0
MAX_CONTENT_WIDTH = 760

VERTICAL_MARGIN_RATIO = 0.06
VERTICAL_MARGIN_MIN = 32
VERTICAL_MARGIN_MAX = 96


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


def vertical_margins(viewport_height: int) -> tuple[int, int]:
    """Top and bottom margin for the text column, in pixels.

    The preview needs clearly more air above and below than at the sides:
    the text starts below the toolbar instead of underneath it, and the last
    line does not sit on the window edge. The value grows with the window
    height, so a maximised window does not look cramped while a small one
    keeps its text area.
    """
    if viewport_height <= 0:
        return VERTICAL_MARGIN_MIN, VERTICAL_MARGIN_MIN
    edge = int(viewport_height * VERTICAL_MARGIN_RATIO)
    edge = max(VERTICAL_MARGIN_MIN, min(edge, VERTICAL_MARGIN_MAX))
    return edge, edge
