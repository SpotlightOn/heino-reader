"""Menu bar and toolbars, built from the window's actions.

Placement only: which action goes where. The actions themselves carry icon,
shortcut and handler, so this module never connects signals.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import (
    QLabel,
    QMenu,
    QSizePolicy,
    QToolBar,
    QToolButton,
    QWidget,
)

from .icons import _icon
from .texts import TOOLBAR_STYLE

if TYPE_CHECKING:
    from .window import ViewerWindow


def build_menu(window: ViewerWindow) -> None:
    """Fill the menu bar."""
    actions = window.actions

    file_menu = window.menuBar().addMenu("&File")
    file_menu.addAction(actions.open)
    file_menu.addAction(actions.save)
    file_menu.addAction(actions.save_as)
    file_menu.addSeparator()
    file_menu.addAction(actions.close)

    view_menu = window.menuBar().addMenu("&View")
    view_menu.addAction(actions.line_numbers)
    view_menu.addAction(actions.remote_images)
    view_menu.addAction(actions.wrap_code)
    view_menu.addSeparator()
    view_menu.addAction(actions.web_preview)

    help_menu = window.menuBar().addMenu("&Help")
    help_menu.addAction(actions.about)


def build_toolbars(window: ViewerWindow) -> None:
    """Add the main toolbar and the hidden formatting toolbar."""
    actions = window.actions

    toolbar = _toolbar(window)
    window.addToolBar(Qt.ToolBarArea.TopToolBarArea, toolbar)
    toolbar.addAction(actions.zoom_out)
    toolbar.addAction(actions.zoom_in)
    toolbar.addSeparator()
    toolbar.addAction(actions.edit_mode)
    toolbar.addAction(actions.quit)

    # A stretch spacer pushes the zoom level into the right corner.
    spacer = QWidget()
    spacer.setSizePolicy(
        QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
    )
    toolbar.addWidget(spacer)
    window.zoom_label = QLabel("100%")
    window.zoom_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    window.zoom_label.setContentsMargins(8, 0, 6, 0)
    toolbar.addWidget(window.zoom_label)
    # The reset action has no button; registering it keeps its shortcut alive.
    window.addAction(actions.zoom_reset)

    window.format_toolbar = _format_toolbar(window)


def _toolbar(window: ViewerWindow, title: str = "") -> QToolBar:
    """A top toolbar with the shared button chrome."""
    toolbar = QToolBar(title, window)
    toolbar.setMovable(False)
    toolbar.setFloatable(False)
    toolbar.setIconSize(QSize(18, 18))
    toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
    toolbar.setStyleSheet(TOOLBAR_STYLE)
    return toolbar


def _format_toolbar(window: ViewerWindow) -> QToolBar:
    """Second toolbar row, hidden until edit mode is switched on."""
    actions = window.actions
    toolbar = _toolbar(window, "Format")
    # Force its own row below the main toolbar; without the break Qt packs
    # both toolbars side by side and the zoom label loses its corner.
    window.addToolBarBreak(Qt.ToolBarArea.TopToolBarArea)
    window.addToolBar(Qt.ToolBarArea.TopToolBarArea, toolbar)

    toolbar.addAction(actions.undo)
    toolbar.addAction(actions.redo)
    toolbar.addSeparator()
    for action in (
        actions.bold,
        actions.italic,
        actions.underline,
        actions.strike,
        actions.code,
    ):
        toolbar.addAction(action)
    toolbar.addSeparator()

    heading_button = QToolButton(toolbar)
    heading_button.setIcon(
        _icon("title", ["format-heading"], glyph="\N{LATIN CAPITAL LETTER H}")
    )
    heading_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
    heading_button.setToolTip("Heading level")
    heading_menu = QMenu(heading_button)
    heading_menu.addActions(actions.headings)
    heading_menu.addSeparator()
    heading_menu.addAction(actions.paragraph)
    heading_button.setMenu(heading_menu)
    toolbar.addWidget(heading_button)

    toolbar.addSeparator()
    for action in (actions.quote, actions.bullet, actions.numbered):
        toolbar.addAction(action)
    toolbar.addSeparator()
    for action in (actions.link, actions.image, actions.table):
        toolbar.addAction(action)

    toolbar.hide()
    return toolbar
