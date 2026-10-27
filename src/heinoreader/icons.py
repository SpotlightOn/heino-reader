"""Toolbar icons: bundled Material Symbols SVGs with fallback rendering."""

from __future__ import annotations

import re
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPainter, QPalette, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QApplication, QStyle

APP_DIR = Path(__file__).resolve().parent
ICON_PATH = APP_DIR / "icon.svg"
ICONS_DIR = APP_DIR / "icons"


def _glyph_icon(glyph: str, size: int = 24) -> QIcon:
    """Draw a text glyph as icon, used when no theme icon is available."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    with QPainter(pixmap) as painter:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        font = QApplication.font()
        font.setBold(True)
        font.setPixelSize(int(size * 0.62))
        painter.setFont(font)
        painter.setPen(QApplication.palette().color(QPalette.ColorRole.WindowText))
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, glyph)
    return QIcon(pixmap)


def _material_icon(name: str) -> QIcon:
    """Render a bundled Material Symbols SVG in the current text color."""
    path = ICONS_DIR / f"{name}.svg"
    if not path.is_file():
        return QIcon()
    svg = path.read_text(encoding="utf-8")
    color = QApplication.palette().color(QPalette.ColorRole.WindowText).name()
    # Drop any existing fill and inherit the palette text color, so the
    # icons stay readable in light and dark themes.
    svg = re.sub(r'(<svg\b[^>]*?)\sfill="[^"]*"', r"\1", svg, count=1)
    svg = svg.replace("<svg", f'<svg fill="{color}"', 1)
    renderer = QSvgRenderer(svg.encode("utf-8"))
    if not renderer.isValid():
        return QIcon()
    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.GlobalColor.transparent)
    with QPainter(pixmap) as painter:
        renderer.render(painter)
    return QIcon(pixmap)


def _icon(
    material_name: str,
    theme_names: list[str],
    standard: QStyle.StandardPixmap | None = None,
    glyph: str = "",
) -> QIcon:
    """Prefer the bundled Material icon, else a theme, standard or drawn one."""
    icon = _material_icon(material_name)
    if not icon.isNull():
        return icon
    for name in theme_names:
        icon = QIcon.fromTheme(name)
        if not icon.isNull():
            return icon
    if standard is not None:
        icon = QApplication.style().standardIcon(standard)
        if not icon.isNull():
            return icon
    return _glyph_icon(glyph)
