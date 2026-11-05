"""Every action of the window: icon, shortcut, tooltip and handler.

An action is defined once here and placed in as many menus and toolbars as
needed, so a new shortcut cannot end up connected in one place only.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import QStyle, QWidget

from . import viewer
from .editor import formatting
from .icons import _icon
from .settings import LINE_NUMBERS_KEY, REMOTE_IMAGES_KEY, WRAP_CODE_KEY
from .texts import WEB_EXTRA_HINT

# Text, icon, theme fallbacks, shortcut, formatting function, arguments, glyph.
# The function receives the editor cursor followed by these arguments.
_FORMAT_ACTIONS = (
    (
        "bold", "Bold", "format_bold", ("format-text-bold",), "Ctrl+B",
        formatting.toggle_wrap, ("**",), "B",
    ),
    (
        "italic", "Italic", "format_italic", ("format-text-italic",),
        "Ctrl+I", formatting.toggle_wrap, ("*",), "I",
    ),
    (
        "underline", "Underline", "format_underlined",
        ("format-text-underlined",), "Ctrl+U",
        formatting.toggle_wrap, ("<u>", "</u>"), "U",
    ),
    (
        "strike", "Strikethrough", "strikethrough_s",
        ("format-text-strikethrough",), "Ctrl+Shift+X",
        formatting.toggle_wrap, ("~~",), "S",
    ),
    (
        "code", "Inline Code", "code", ("insert-code",), "Ctrl+E",
        formatting.toggle_wrap, ("`",), "`",
    ),
)


def make_action(
    parent: QWidget,
    text: str,
    icon: str = "",
    themes: Sequence[str] = (),
    shortcut: str | QKeySequence | QKeySequence.StandardKey | None = None,
    slot: Callable[..., object] | None = None,
    *,
    glyph: str = "",
    standard: QStyle.StandardPixmap | None = None,
    checkable: bool = False,
    enabled: bool = True,
) -> QAction:
    """Build one action with its icon, shortcut, tooltip and handler."""
    action = QAction(text, parent)
    if icon or glyph:
        action.setIcon(_icon(icon, list(themes), standard, glyph=glyph))
    if shortcut is not None:
        sequence = QKeySequence(shortcut)
        action.setShortcut(sequence)
        if text:
            action.setToolTip(f"{text} ({sequence.toString()})")
    action.setCheckable(checkable)
    if slot is not None:
        # A checkable action reports its new state through ``toggled``; that
        # also fires when the state is set from code, which plain
        # ``triggered`` does not.
        signal = action.toggled if checkable else action.triggered
        signal.connect(slot)
    action.setEnabled(enabled)
    return action


class Actions:
    """All actions of one window, already connected to its handlers."""

    def __init__(self, window) -> None:
        self._window = window
        parent = window

        self.undo = make_action(
            parent, "Undo", "undo", ("edit-undo",),
            QKeySequence.StandardKey.Undo, window.undo,
            glyph="\N{ANTICLOCKWISE OPEN CIRCLE ARROW}", enabled=False,
        )
        self.redo = make_action(
            parent, "Redo", "redo", ("edit-redo",),
            QKeySequence.StandardKey.Redo, window.redo,
            glyph="\N{CLOCKWISE OPEN CIRCLE ARROW}", enabled=False,
        )
        # Ctrl+Y on top of the platform shortcut, which is Ctrl+Shift+Z.
        self.redo.setShortcuts(
            [
                QKeySequence(QKeySequence.StandardKey.Redo),
                QKeySequence("Ctrl+Y"),
            ]
        )
        self.redo.setToolTip("Redo (Ctrl+Shift+Z, Ctrl+Y)")

        self.formatting: list[QAction] = []
        for key, text, icon, themes, shortcut, func, args, glyph in (
            _FORMAT_ACTIONS
        ):
            action = self._format(text, icon, themes, shortcut, func, args, glyph)
            setattr(self, key, action)
            self.formatting.append(action)

        self.headings = [
            self._format(
                f"Heading {level}", "title", ("format-heading",),
                f"Ctrl+{level}", formatting.set_heading, (level,), str(level),
            )
            for level in range(1, 7)
        ]
        self.paragraph = self._format(
            "Plain Paragraph", "title", ("format-clear",), "Ctrl+Shift+0",
            formatting.set_heading, (0,), "P",
        )
        self.quote = self._format(
            "Block Quote", "format_quote", ("format-text-quote",),
            "Ctrl+Shift+Q", formatting.toggle_quote, (), ">",
        )
        self.bullet = self._format(
            "Bullet List", "format_list_bulleted", ("format-list-bullet",),
            "Ctrl+Shift+L", formatting.toggle_list, (), "-",
        )
        self.numbered = self._format(
            "Numbered List", "format_list_numbered", ("format-list-ordered",),
            "Ctrl+Shift+N", formatting.toggle_list, (True,), "1.",
        )

        # These open a dialog first, so they call the window directly.
        self.link = self._editor_action(
            "Link...", "link", ("insert-link",), "Ctrl+K",
            window.insert_link, "L",
        )
        self.image = self._editor_action(
            "Image...", "image", ("insert-image",), "Ctrl+Shift+I",
            window.insert_image, "P",
        )
        self.table = self._editor_action(
            "Table...", "table", ("insert-table",), "Ctrl+Shift+T",
            window.insert_table, "T",
        )

        self.open = make_action(
            parent, "&Open...", "folder_open",
            ("document-open", "folder-open"), QKeySequence.StandardKey.Open,
            window.open_dialog, glyph="O",
        )
        self.save = make_action(
            parent, "&Save", "save", ("document-save", "document-save-as"),
            QKeySequence.StandardKey.Save, window.save, glyph="S", enabled=False,
        )
        self.save_as = make_action(
            parent, "Save &As...", "save", ("document-save-as",),
            QKeySequence.StandardKey.SaveAs, window.save_as,
            glyph="S", enabled=False,
        )
        self.close = make_action(
            parent, "&Close", "close", ("window-close",),
            QKeySequence.StandardKey.Close, window.close, glyph="X",
        )
        self.quit = make_action(
            parent, "Quit", "exit_to_app",
            ("application-exit", "window-close"),
            QKeySequence.StandardKey.Quit, window.close,
            glyph="\N{BALLOT X}",
        )
        self.about = make_action(
            parent, "&About", "info", ("help-about",), None,
            window.show_about_dialog, glyph="i",
        )

        self.zoom_out = make_action(
            parent, "Zoom out", "text_decrease", ("zoom-out", "list-remove"),
            QKeySequence.StandardKey.ZoomOut, window.zoom_out,
            standard=QStyle.StandardPixmap.SP_TitleBarMinButton,
            glyph="\N{MINUS SIGN}",
        )
        self.zoom_in = make_action(
            parent, "Zoom in", "text_increase", ("zoom-in", "list-add"),
            QKeySequence.StandardKey.ZoomIn, window.zoom_in, glyph="+",
        )
        self.zoom_reset = make_action(
            parent, "", "", (), "Ctrl+0", window.zoom_reset,
        )
        self.edit_mode = make_action(
            parent, "Edit mode", "edit", ("document-edit", "edit"), None,
            window.set_edit_mode, checkable=True,
            glyph="\N{LOWER LEFT PENCIL}",
        )
        self.edit_mode.setToolTip(
            "Toggle edit mode: source left, live view right "
            "(click again for the default view)"
        )

        self.line_numbers = self._toggle(
            "&Line Numbers", window.set_line_numbers,
            "Show line numbers in the source editor (optional)",
            window.settings.get_bool(LINE_NUMBERS_KEY, False),
        )
        self.remote_images = self._toggle(
            "Load &Remote Images", window.set_remote_images,
            "Download images from http(s) URLs; sends network requests",
            window.settings.get_bool(REMOTE_IMAGES_KEY, True),
        )
        self.wrap_code = self._toggle(
            "Wrap &Code", window.set_code_wrap,
            "Wrap lines that are wider than the text column. Off leaves long "
            "code lines intact and shows a horizontal scrollbar for the page",
            window.settings.get_bool(WRAP_CODE_KEY, True),
        )
        self.web_renderer = make_action(
            parent, "&Web Engine Renderer", "", (), None,
            window.set_web_renderer, checkable=True,
            enabled=viewer.web_engine_available(),
        )
        self.web_renderer.blockSignals(True)
        self.web_renderer.setChecked(
            window.viewer_area.kind == viewer.RENDERER_WEB
        )
        self.web_renderer.blockSignals(False)
        self.web_renderer.setToolTip(
            "Render with QtWebEngine for full HTML/CSS fidelity. Better but "
            "slower than the Qt text renderer (default), which never loads "
            "Chromium"
            if viewer.web_engine_available()
            else f"Not installed. {WEB_EXTRA_HINT}"
        )

    @property
    def editing_actions(self) -> list[QAction]:
        """Everything that only makes sense with the editor open."""
        return [
            *self.formatting,
            *self.headings,
            self.paragraph,
            self.quote,
            self.bullet,
            self.numbered,
            self.link,
            self.image,
            self.table,
        ]

    def _format(self, text, icon, themes, shortcut, func, args, glyph) -> QAction:
        """An action that runs a formatting function on the cursor."""

        def run(*_ignored, func=func, args=args) -> None:
            # QAction hands over a checked flag; the formatting call does not
            # want it.
            self._window.apply_format(func, *args)

        return self._editor_action(text, icon, themes, shortcut, run, glyph)

    def _editor_action(self, text, icon, themes, shortcut, slot, glyph) -> QAction:
        """An action that is only enabled while the editor is open."""
        return make_action(
            self._window, text, icon, themes, shortcut, slot,
            glyph=glyph, enabled=False,
        )

    def _toggle(self, text, slot, tip, checked) -> QAction:
        action = make_action(
            self._window, text, "", (), None, slot, checkable=True,
        )
        action.setToolTip(tip)
        # The state comes from the settings file; applying it must not run the
        # handler, because the window is still being built at this point.
        action.blockSignals(True)
        action.setChecked(checked)
        action.blockSignals(False)
        return action
