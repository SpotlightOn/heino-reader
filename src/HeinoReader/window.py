"""The viewer window: menus, toolbars, preview backends and edit mode."""

from __future__ import annotations

import os
import sys
from importlib.util import find_spec
from pathlib import Path

from PySide6.QtCore import QFileSystemWatcher, QRect, QSize, Qt, QTimer, Slot
from PySide6.QtGui import QAction, QFontDatabase, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QSizePolicy,
    QSplitter,
    QStyle,
    QToolBar,
    QToolButton,
    QWidget,
)

from .editor import (
    LineNumberGutter,
    MarkdownSourceEdit,
    ask_image,
    ask_link_url,
    ask_table_size,
    formatting,
)
from .files import is_supported_path, rejection_reason
from .icons import APP_DIR, _icon
from .layout import DOCUMENT_MARGIN
from .qtview import QtMarkdownView
from .settings import (
    LINE_NUMBERS_KEY,
    REMOTE_IMAGES_KEY,
    RENDERER_KEY,
    Settings,
)

ZOOM_STEP = 0.1
MIN_SCALE = 0.5
MAX_SCALE = 4.0

# Shared chrome for the main and the format toolbar buttons.
TOOLBAR_STYLE = """
    QToolBar QToolButton {
        border: 1px solid rgba(128, 128, 128, 0.45);
        border-radius: 4px;
        padding: 8px;
        margin: 2px;
        background-color: rgba(128, 128, 128, 0.10);
    }
    QToolBar QToolButton:hover {
        background-color: rgba(128, 128, 128, 0.22);
    }
    QToolBar QToolButton:pressed,
    QToolBar QToolButton:on {
        background-color: rgba(128, 128, 128, 0.35);
    }
    """

# Entering edit mode widens the window up to this many pixels, so the two
# panes do not get cramped; on smaller screens it is clamped to the usable
# screen width. Leaving edit mode restores the previous size.
EDIT_MODE_WIDTH = 1200

# Wait this long after the last keystroke before the preview re-renders.
# One render per short note is cheap, but a long document costs real time and
# typing does not need a fresh preview per character.
LIVE_PREVIEW_DELAY_MS = 200

# Keep in sync with pyproject.toml.
VERSION = "0.2.1"

ABOUT_TEXT = (
    f"<b>Heino Reader {VERSION}</b>"
    "<p>A fast document viewer for markdown files, built with PySide6.</p>"
    "<p>An homage to Heino: dark sunglasses on, no fuss, just the text.</p>"
    "<p>Optional: the Web Engine preview (View menu) renders with QtWebEngine "
    "for full CSS fidelity. It is the better but slower renderer and needs "
    'PySide6-Addons (<a href="https://pypi.org/project/PySide6-Addons/">'
    "pypi.org/project/PySide6-Addons</a>).</p>"
    "<p>Toolbar icons: Material Symbols Outlined (Apache License 2.0).</p>"
    "<p>License: MIT. Copyright (c) 2026 SpotlightOn.</p>"
)

PLACEHOLDER_MD = """\
<img src="icon.svg" alt="Heino Reader">

# Heino Reader

An homage to Heino, the German singer with the black sunglasses: dark glasses
on, no fuss, just the text.

Drop a markdown file here, or start Heino Reader with a file path:

    heino-reader notes.md

- **Open** with `Ctrl+O` or drag a file onto the window
- **Edit** with the pencil button: source left, live preview right;
  `Ctrl+S` saves, `Ctrl+Shift+S` saves as
- **Zoom** with `Ctrl++` / `Ctrl+-`, reset with `Ctrl+0`
- **Remote images**: View -> Load Remote Images (off sends no requests)
- **Full CSS fidelity**: View -> Web Engine Preview. This is the better but
  slower renderer: it draws with QtWebEngine instead of Qt's text engine and
  needs the optional PySide6-Addons package
  (https://pypi.org/project/PySide6-Addons/, `pip install "heino-reader[web]"`)
"""


def ask_open_file(parent: QWidget, start_dir: str) -> Path | None:
    """Ask the user for a markdown file; None when cancelled."""
    path, _ = QFileDialog.getOpenFileName(
        parent,
        "Open Markdown File",
        start_dir,
        "Markdown files (*.md *.markdown *.mdown *.mkd);;All files (*)",
    )
    return Path(path) if path else None


def ask_save_file(parent: QWidget, start_path: str) -> Path | None:
    """Ask the user where to save the markdown file; None when cancelled."""
    path, _ = QFileDialog.getSaveFileName(
        parent,
        "Save Markdown File",
        start_path,
        "Markdown files (*.md *.markdown *.mdown *.mkd);;All files (*)",
    )
    if not path:
        return None
    target = Path(path)
    return target if target.suffix else target.with_suffix(".md")


def show_about(parent: QWidget) -> None:
    """Show the about dialog."""
    QMessageBox.about(parent, "About Heino Reader", ABOUT_TEXT)


# Preview backends. The Qt text renderer is the default: it starts
# instantly and needs no Chromium process. The WebEngine backend is a
# deliberate opt-in (View menu or --renderer web) and is imported lazily.
RENDERER_WEB = "web"
RENDERER_QT = "qt"
DEFAULT_RENDERER = RENDERER_QT
RENDERERS = (RENDERER_WEB, RENDERER_QT)

WEB_EXTRA_HINT = (
    "The Web Engine preview renders markdown with QtWebEngine (Chromium), so "
    "tables, borders and backgrounds follow the CSS exactly. It is more "
    "faithful than the default Qt text renderer, but slower to start and a "
    "much bigger download.\n\n"
    "It needs the optional PySide6-Addons package:\n"
    "https://pypi.org/project/PySide6-Addons/\n\n"
    '    pip install "heino-reader[web]"\n\n'
    "(or run scripts/install.sh --web)"
)


def web_engine_available() -> bool:
    """True when pyside6-addons (QtWebEngine) is installed.

    Uses a spec lookup instead of an import, so checking never loads the
    Chromium libraries.
    """
    return find_spec("PySide6.QtWebEngineWidgets") is not None


def create_markdown_view(kind: str, parent: QWidget | None = None):
    """Return a preview widget for the given renderer kind.

    The WebEngine backend is imported here rather than at module level, so
    a Qt-rendered preview never loads Chromium.
    """
    if kind == RENDERER_QT:
        return QtMarkdownView(parent)
    from .webview import WebMarkdownView

    return WebMarkdownView(parent)


class ViewerWindow(QMainWindow):
    """Read-only markdown viewer with zoom controls in the top toolbar."""

    def __init__(
        self, path: Path | None = None, renderer: str | None = None
    ) -> None:
        super().__init__()
        self._settings = Settings()
        chosen = renderer or self._settings.get_string(
            RENDERER_KEY, DEFAULT_RENDERER
        )
        if chosen == RENDERER_WEB and not web_engine_available():
            print(
                "heino-reader: QtWebEngine is not installed, "
                "falling back to the Qt renderer",
                file=sys.stderr,
            )
            chosen = DEFAULT_RENDERER
        self._renderer = chosen if chosen in RENDERERS else DEFAULT_RENDERER
        self._markdown = PLACEHOLDER_MD
        self._path: Path | None = None
        # Geometry to restore when leaving edit mode (None = never widened).
        self._pre_edit_geometry: QRect | None = None
        base_size = QApplication.font().pointSizeF()
        self._base_point_size = base_size if base_size > 0 else 11.0

        self._views: dict[str, QWidget] = {}
        self.viewer = create_markdown_view(self._renderer, self)
        # The start screen shows the bundled icon, so relative image
        # paths resolve against the package directory until a file opens.
        self.viewer.set_base_dir(APP_DIR)
        self._views[self._renderer] = self.viewer
        self.viewer.setAcceptDrops(False)

        # Edit mode: raw markdown source on the left, preview on the right.
        # The source editor is created on first use (see _ensure_source),
        # so a plain preview start never builds the editor, its syntax
        # highlighter or its line-number gutter.
        self._source: MarkdownSourceEdit | None = None
        self._line_numbers: LineNumberGutter | None = None
        self._splitter = QSplitter(Qt.Orientation.Horizontal, self)
        self._splitter.addWidget(self.viewer)
        self.setCentralWidget(self._splitter)

        self._watcher = QFileSystemWatcher(self)
        self._watcher.fileChanged.connect(self._on_file_changed)

        # The live preview is debounced; see _source_edited.
        self._render_timer = QTimer(self)
        self._render_timer.setSingleShot(True)
        self._render_timer.setInterval(LIVE_PREVIEW_DELAY_MS)
        self._render_timer.timeout.connect(self._render)

        self.setAcceptDrops(True)
        self.resize(800, 900)

        self._build_format_actions()
        self._build_menu()
        self._build_toolbar()
        self._set_scale(1.0)

        if path is not None:
            self.open(path)
        else:
            self.setWindowTitle("Heino Reader")
            self._render()

    # ------------------------------------------------------------------ UI

    # ------------------------------------------------------- format actions

    def _apply_format(self, func, *args) -> None:
        """Run a formatting operation on the source cursor, keep selection."""
        source = self._ensure_source()
        cursor = source.textCursor()
        func(cursor, *args)
        source.setTextCursor(cursor)
        source.setFocus()

    # ------------------------------------------------- insert (via dialog)

    def _relative_path(self, target: str) -> str:
        """Prefer a path relative to the markdown file, for portability."""
        if self._path is None:
            return target
        try:
            return os.path.relpath(target, self._path.parent)
        except ValueError:
            # e.g. different drives on Windows.
            return target

    @staticmethod
    def _looks_like_url(text: str) -> bool:
        """A single token with a scheme or a leading www. reads as a URL."""
        if not text or " " in text:
            return False
        return "://" in text or text.startswith(("www.", "/", "./", "../"))

    @Slot()
    def _insert_link(self) -> None:
        selected = self._ensure_source().textCursor().selectedText()
        initial = selected if self._looks_like_url(selected) else ""
        url = ask_link_url(self, initial)
        if url:
            self._apply_format(formatting.insert_link, url)

    @Slot()
    def _insert_image(self) -> None:
        source = self._ensure_source()
        start = str(self._path.parent) if self._path is not None else str(Path.home())
        alt = source.textCursor().selectedText()
        choice = ask_image(self, start, alt)
        if choice is None:
            return
        path, alt_text = choice
        self._apply_format(formatting.insert_image, self._relative_path(path), alt_text)

    @Slot()
    def _insert_table(self) -> None:
        size = ask_table_size(self)
        if size is None:
            return
        rows, columns = size
        self._apply_format(formatting.insert_table, rows, columns)

    def _build_format_actions(self) -> None:
        """Create the markdown formatting actions (menu + format toolbar)."""
        self._format_actions: list[QAction] = []

        def add(text, icon_name, theme_names, shortcut, func, *args, glyph=""):
            action = QAction(_icon(icon_name, theme_names, glyph=glyph), text, self)
            action.setShortcut(QKeySequence(shortcut))
            action.setToolTip(f"{text} ({shortcut})")
            action.triggered.connect(
                lambda checked=False, f=func, a=args: self._apply_format(f, *a)
            )
            action.setEnabled(False)  # only meaningful in edit mode
            self._format_actions.append(action)
            return action

        self._bold_action = add(
            "Bold", "format_bold", ["format-text-bold"],
            "Ctrl+B", formatting.toggle_wrap, "**", glyph="B",
        )
        self._italic_action = add(
            "Italic", "format_italic", ["format-text-italic"],
            "Ctrl+I", formatting.toggle_wrap, "*", glyph="I",
        )
        self._underline_action = add(
            "Underline", "format_underlined", ["format-text-underlined"],
            "Ctrl+U", formatting.toggle_wrap, "<u>", "</u>", glyph="U",
        )
        self._strike_action = add(
            "Strikethrough", "strikethrough_s", ["format-text-strikethrough"],
            "Ctrl+Shift+X", formatting.toggle_wrap, "~~", glyph="S",
        )
        self._code_action = add(
            "Inline Code", "code", ["insert-code"],
            "Ctrl+E", formatting.toggle_wrap, "`", glyph="`",
        )

        # Headings 1-6 plus a "plain paragraph" reset.
        self._heading_actions = [
            add(
                f"Heading {level}", "title", ["format-heading"],
                f"Ctrl+{level}", formatting.set_heading, level, glyph=str(level),
            )
            for level in range(1, 7)
        ]
        self._paragraph_action = add(
            "Plain Paragraph", "title", ["format-clear"],
            "Ctrl+Shift+0", formatting.set_heading, 0, glyph="P",
        )

        self._quote_action = add(
            "Block Quote", "format_quote", ["format-text-quote"],
            "Ctrl+Shift+Q", formatting.toggle_quote, glyph=">",
        )
        self._bullet_action = add(
            "Bullet List", "format_list_bulleted", ["format-list-bullet"],
            "Ctrl+Shift+L", formatting.toggle_list, glyph="-",
        )
        self._numbered_action = add(
            "Numbered List", "format_list_numbered", ["format-list-ordered"],
            "Ctrl+Shift+N", formatting.toggle_list, True, glyph="1.",
        )

        # Insert actions open a dialog first, so they call their slot
        # directly instead of going through _apply_format.
        def add_slot(text, icon_name, theme_names, shortcut, slot, glyph=""):
            action = QAction(_icon(icon_name, theme_names, glyph=glyph), text, self)
            action.setShortcut(QKeySequence(shortcut))
            action.setToolTip(f"{text} ({shortcut})")
            action.triggered.connect(slot)
            action.setEnabled(False)  # only meaningful in edit mode
            self._format_actions.append(action)
            return action

        self._link_action = add_slot(
            "Link...", "link", ["insert-link"],
            "Ctrl+K", self._insert_link, glyph="L",
        )
        self._image_action = add_slot(
            "Image...", "image", ["insert-image"],
            "Ctrl+Shift+I", self._insert_image, glyph="P",
        )
        self._table_action = add_slot(
            "Table...", "table", ["insert-table"],
            "Ctrl+Shift+T", self._insert_table, glyph="T",
        )

    def _build_menu(self) -> None:
        file_menu = self.menuBar().addMenu("&File")

        open_action = QAction(
            _icon("folder_open", ["document-open", "folder-open"], glyph="O"),
            "&Open...",
            self,
        )
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self._open_dialog)
        file_menu.addAction(open_action)

        self._save_action = QAction(
            _icon("save", ["document-save", "document-save-as"], glyph="S"),
            "&Save",
            self,
        )
        self._save_action.setShortcut(QKeySequence.StandardKey.Save)
        self._save_action.setEnabled(False)  # only meaningful in edit mode
        self._save_action.triggered.connect(self._save)
        file_menu.addAction(self._save_action)

        self._save_as_action = QAction(
            _icon("save", ["document-save-as"], glyph="S"),
            "Save &As...",
            self,
        )
        self._save_as_action.setShortcut(QKeySequence.StandardKey.SaveAs)
        self._save_as_action.setEnabled(False)  # only meaningful in edit mode
        self._save_as_action.triggered.connect(self._save_as)
        file_menu.addAction(self._save_as_action)

        file_menu.addSeparator()

        close_action = QAction(
            _icon("close", ["window-close"], glyph="X"),
            "&Close",
            self,
        )
        close_action.setShortcut(QKeySequence.StandardKey.Close)
        close_action.triggered.connect(self.close)
        file_menu.addAction(close_action)

        view_menu = self.menuBar().addMenu("&View")
        self._line_numbers_action = QAction("&Line Numbers", self)
        self._line_numbers_action.setCheckable(True)
        self._line_numbers_action.setToolTip(
            "Show line numbers in the source editor (optional)"
        )
        self._line_numbers_action.toggled.connect(self._set_line_numbers)
        self._line_numbers_action.setChecked(
            self._settings.get_bool(LINE_NUMBERS_KEY, False)
        )
        view_menu.addAction(self._line_numbers_action)

        self._remote_images_action = QAction("Load &Remote Images", self)
        self._remote_images_action.setCheckable(True)
        self._remote_images_action.setToolTip(
            "Download images from http(s) URLs; sends network requests"
        )
        self._remote_images_action.toggled.connect(self._set_remote_images)
        self._remote_images_action.setChecked(
            self._settings.get_bool(REMOTE_IMAGES_KEY, True)
        )
        # setChecked() emits nothing when the value is already false, so
        # apply the saved state to the view explicitly.
        self.viewer.set_remote_images_enabled(
            self._remote_images_action.isChecked()
        )
        view_menu.addAction(self._remote_images_action)

        view_menu.addSeparator()
        self._web_preview_action = QAction("&Web Engine Preview", self)
        self._web_preview_action.setCheckable(True)
        self._web_preview_action.setChecked(self._renderer == RENDERER_WEB)
        if web_engine_available():
            self._web_preview_action.setToolTip(
                "Render with QtWebEngine for full HTML/CSS fidelity. Better "
                "but slower than the Qt text renderer (default), which never "
                "loads Chromium"
            )
        else:
            self._web_preview_action.setEnabled(False)
            self._web_preview_action.setToolTip(
                "Not installed. The Web Engine preview is the better but "
                "slower renderer and needs PySide6-Addons "
                '(https://pypi.org/project/PySide6-Addons/): pip install '
                '"heino-reader[web]"'
            )
        self._web_preview_action.toggled.connect(self._set_web_preview)
        view_menu.addAction(self._web_preview_action)

        help_menu = self.menuBar().addMenu("&Help")
        about_action = QAction(
            _icon("info", ["help-about"], glyph="i"),
            "&About",
            self,
        )
        about_action.triggered.connect(self._about)
        help_menu.addAction(about_action)

    @Slot()
    def _open_dialog(self) -> None:
        start = str(self._path.parent) if self._path is not None else str(Path.home())
        path = ask_open_file(self, start)
        if path is not None:
            self.open(path)

    @Slot()
    def _save(self) -> None:
        """Write the edit buffer back to the markdown file."""
        if self._path is None or self._source is None:
            return
        self._write(self._path)

    @Slot()
    def _save_as(self) -> None:
        """Write the edit buffer to the chosen file and keep editing it."""
        if self._source is None:
            return
        if self._path is not None:
            start = str(self._path)
        else:
            start = str(Path.home() / "untitled.md")
        path = ask_save_file(self, start)
        if path is None:
            return
        if path == self._path:
            self._write(path)
            return
        if self._write(path):
            self._adopt_path(path)
            self._render_now()

    def _write(self, path: Path) -> bool:
        """Write the edit buffer to ``path``; False when that fails."""
        try:
            path.write_text(self._source.toPlainText(), encoding="utf-8")
        except OSError as error:
            print(f"heino-reader: cannot save {path}: {error}", file=sys.stderr)
            return False
        return True

    def _adopt_path(self, path: Path) -> None:
        """Make ``path`` the file this window edits, watches and shows."""
        self._path = path
        self.viewer.set_base_dir(path.parent)
        watched = self._watcher.files()
        if watched:
            self._watcher.removePaths(watched)
        self._watcher.addPath(str(path))
        self.setWindowTitle(f"{path.name} \N{EM DASH} Heino Reader")
        self._update_save_action()

    def _update_save_action(self) -> None:
        """Saving is available only while editing."""
        editing = self._edit_action.isChecked()
        self._save_action.setEnabled(editing and self._path is not None)
        self._save_as_action.setEnabled(editing)
        # Formatting only makes sense while editing, so the format toolbar
        # appears with edit mode and its actions become enabled.
        self._format_toolbar.setVisible(editing)
        for action in self._format_actions:
            action.setEnabled(editing)

    @Slot()
    def _about(self) -> None:
        show_about(self)

    @Slot(bool)
    def _set_line_numbers(self, enabled: bool) -> None:
        """Switch the optional line-number gutter on or off.

        The gutter only exists once the editor has been created; until
        then the setting is just remembered and applied on first use.
        """
        self._apply_line_numbers()
        self._settings.set_bool(LINE_NUMBERS_KEY, enabled)

    def _apply_line_numbers(self) -> None:
        """Match the gutter (if the editor exists) to the menu state."""
        if self._line_numbers is None:
            return
        if self._line_numbers_action.isChecked():
            self._line_numbers.install()
        else:
            self._line_numbers.uninstall()

    @Slot(bool)
    def _set_remote_images(self, enabled: bool) -> None:
        """Allow or forbid downloading remote images, then re-render."""
        self.viewer.set_remote_images_enabled(enabled)
        self._settings.set_bool(REMOTE_IMAGES_KEY, enabled)
        self._render_now()

    @Slot(bool)
    def _set_web_preview(self, enabled: bool) -> None:
        """Switch between the WebEngine and the Qt text renderer."""
        self._set_renderer(RENDERER_WEB if enabled else RENDERER_QT)

    def _set_renderer(self, kind: str) -> None:
        """Swap the preview widget for the other backend."""
        if kind not in RENDERERS or kind == self._renderer:
            return
        new = self._views.get(kind)
        if new is None:
            try:
                new = create_markdown_view(kind, self)
            except ImportError:
                # pyside6-addons is missing: keep the current backend and
                # explain instead of dying on a lazy import.
                QMessageBox.information(
                    self, "Web Engine Preview unavailable", WEB_EXTRA_HINT
                )
                self._web_preview_action.blockSignals(True)
                self._web_preview_action.setChecked(False)
                self._web_preview_action.blockSignals(False)
                return
            new.set_zoom(self._scale)
            self._views[kind] = new
        new.set_base_dir(
            self._path.parent if self._path is not None else APP_DIR
        )
        new.set_remote_images_enabled(self._remote_images_action.isChecked())

        old = self.viewer
        visible = old.isVisible()
        sizes = self._splitter.sizes()
        index = self._splitter.indexOf(old)
        self._splitter.replaceWidget(index, new)
        if sizes:
            self._splitter.setSizes(sizes)

        self.viewer = new
        self._renderer = kind
        self._settings.set_string(RENDERER_KEY, kind)
        new.setVisible(visible)
        self._web_preview_action.blockSignals(True)
        self._web_preview_action.setChecked(kind == RENDERER_WEB)
        self._web_preview_action.blockSignals(False)
        self._render_now()

    def _build_toolbar(self) -> None:
        toolbar = QToolBar(self)
        toolbar.setMovable(False)
        toolbar.setFloatable(False)
        toolbar.setIconSize(QSize(18, 18))
        toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        # Give the buttons a visible button chrome (border, hover, pressed).
        toolbar.setStyleSheet(TOOLBAR_STYLE)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, toolbar)

        zoom_out = QAction(
            _icon(
                "text_decrease",
                ["zoom-out", "list-remove"],
                QStyle.StandardPixmap.SP_TitleBarMinButton,
                "\N{MINUS SIGN}",
            ),
            "Zoom out",
            self,
        )
        zoom_out.setToolTip("Zoom out (Ctrl+-)")
        zoom_out.setShortcut(QKeySequence.StandardKey.ZoomOut)
        zoom_out.triggered.connect(self.zoom_out)

        zoom_in = QAction(
            _icon("text_increase", ["zoom-in", "list-add"], glyph="+"),
            "Zoom in",
            self,
        )
        zoom_in.setToolTip("Zoom in (Ctrl++)")
        zoom_in.setShortcut(QKeySequence.StandardKey.ZoomIn)
        zoom_in.triggered.connect(self.zoom_in)

        reset = QAction(self)
        reset.setShortcut(QKeySequence("Ctrl+0"))
        reset.triggered.connect(self.zoom_reset)

        edit_action = QAction(
            _icon(
                "edit",
                ["document-edit", "edit"],
                glyph="\N{LOWER LEFT PENCIL}",
            ),
            "Edit mode",
            self,
        )
        edit_action.setCheckable(True)
        edit_action.setToolTip(
            "Toggle edit mode: source left, live preview right "
            "(click again for the default view)"
        )
        edit_action.triggered.connect(self._set_edit_mode)
        self._edit_action = edit_action

        quit_action = QAction(
            _icon(
                "exit_to_app",
                ["application-exit", "window-close"],
                QStyle.StandardPixmap.SP_DialogCloseButton,
                "\N{BALLOT X}",
            ),
            "Quit",
            self,
        )
        quit_action.setToolTip("Quit (Ctrl+Q)")
        quit_action.setShortcut(QKeySequence.StandardKey.Quit)
        quit_action.triggered.connect(self.close)

        toolbar.addAction(zoom_out)
        toolbar.addAction(zoom_in)
        toolbar.addSeparator()
        toolbar.addAction(edit_action)
        toolbar.addAction(quit_action)
        # A stretch spacer pushes the zoom level into the right corner.
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        toolbar.addWidget(spacer)
        # Zoom level stays visible even in long documents.
        self._zoom_label = QLabel("100%", self)
        self._zoom_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._zoom_label.setContentsMargins(8, 0, 6, 0)
        toolbar.addWidget(self._zoom_label)

        # The reset action has no button; register it for its shortcut.
        self.addAction(reset)

        self._build_format_toolbar()

    def _build_format_toolbar(self) -> None:
        """Second toolbar row with the formatting buttons.

        It stays hidden until edit mode is switched on.
        """
        toolbar = QToolBar("Format", self)
        toolbar.setMovable(False)
        toolbar.setFloatable(False)
        toolbar.setIconSize(QSize(18, 18))
        toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        toolbar.setStyleSheet(TOOLBAR_STYLE)
        # Force its own row below the main toolbar; without the break Qt
        # packs both toolbars side by side and the zoom label loses its
        # place in the right corner.
        self.addToolBarBreak(Qt.ToolBarArea.TopToolBarArea)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, toolbar)

        for action in (
            self._bold_action,
            self._italic_action,
            self._underline_action,
            self._strike_action,
            self._code_action,
        ):
            toolbar.addAction(action)

        toolbar.addSeparator()

        # Heading dropdown: H1-H6 plus a plain-paragraph reset.
        heading_button = QToolButton(toolbar)
        heading_button.setIcon(
            _icon("title", ["format-heading"], glyph="\N{LATIN CAPITAL LETTER H}")
        )
        heading_button.setPopupMode(
            QToolButton.ToolButtonPopupMode.InstantPopup
        )
        heading_button.setToolTip("Heading level")
        heading_menu = QMenu(heading_button)
        heading_menu.addActions(self._heading_actions)
        heading_menu.addSeparator()
        heading_menu.addAction(self._paragraph_action)
        heading_button.setMenu(heading_menu)
        toolbar.addWidget(heading_button)

        toolbar.addSeparator()

        for action in (
            self._quote_action,
            self._bullet_action,
            self._numbered_action,
        ):
            toolbar.addAction(action)

        toolbar.addSeparator()

        for action in (
            self._link_action,
            self._image_action,
            self._table_action,
        ):
            toolbar.addAction(action)

        toolbar.hide()
        self._format_toolbar = toolbar

    # --------------------------------------------------------------- zoom

    @Slot()
    def zoom_in(self) -> None:
        self._set_scale(self._scale + ZOOM_STEP)

    @Slot()
    def zoom_out(self) -> None:
        self._set_scale(self._scale - ZOOM_STEP)

    @Slot()
    def zoom_reset(self) -> None:
        self._set_scale(1.0)

    def _set_scale(self, scale: float) -> None:
        self._scale = max(MIN_SCALE, min(MAX_SCALE, round(scale, 2)))
        self.viewer.set_zoom(self._scale)
        self._zoom_label.setText(f"{round(self._scale * 100)}%")

    # --------------------------------------------------------- edit mode

    def _ensure_source(self) -> MarkdownSourceEdit:
        """Create the source editor (and its gutter) on first use."""
        if self._source is not None:
            return self._source
        source = MarkdownSourceEdit(self._splitter)
        source.setFont(
            QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        )
        source.document().setDocumentMargin(DOCUMENT_MARGIN)
        source.textChanged.connect(self._source_edited)
        # Line numbers are optional; the gutter is created with the editor
        # and attached only if the View menu asks for it.
        self._line_numbers = LineNumberGutter(source)
        self._splitter.insertWidget(0, source)
        self._source = source
        self._apply_line_numbers()
        return source

    @Slot(bool)
    def _set_edit_mode(self, enabled: bool) -> None:
        """Split the window (source left, preview right) or show preview only."""
        if enabled:
            source = self._ensure_source()
            if source.toPlainText() != self._markdown:
                source.blockSignals(True)
                source.setPlainText(self._markdown)
                source.blockSignals(False)
            self._widen_for_edit()
            source.show()
            half = max(self._splitter.width() // 2, 1)
            self._splitter.setSizes([half, half])
        else:
            # QSplitter skips hidden widgets, so the preview takes over.
            if self._source is not None:
                self._source.hide()
            self._restore_pre_edit_geometry()
            # Leaving edit mode exposes the preview: skip the debounce wait.
            self._flush_pending_render()
        self._update_save_action()

    def _widen_for_edit(self) -> None:
        """Widen the window for the split view, up to EDIT_MODE_WIDTH.

        On a smaller screen the width is clamped to the usable screen width,
        so the window never grows beyond the display.
        """
        if self.width() >= EDIT_MODE_WIDTH:
            return  # already wide enough, nothing to remember or change
        target = EDIT_MODE_WIDTH
        available = self.screen().availableGeometry() if self.screen() else None
        if available is not None:
            target = min(target, available.width())
        if target <= self.width():
            return
        self._pre_edit_geometry = self.geometry()
        # Shift left by half the growth so the window stays visually centered.
        x = self.x() - (target - self.width()) // 2
        if available is not None:
            x = max(available.left(), min(x, available.right() - target + 1))
        self.setGeometry(x, self.y(), target, self.height())

    def _restore_pre_edit_geometry(self) -> None:
        """Put the window back to its pre-edit-mode size and position."""
        if self._pre_edit_geometry is not None:
            self.setGeometry(self._pre_edit_geometry)
            self._pre_edit_geometry = None

    @Slot()
    def _source_edited(self) -> None:
        """Live-update the preview while the source is edited.

        The text is taken over immediately — saving must not lag behind — but
        the preview waits for the typing to pause, so a keystroke no longer
        costs a full render.
        """
        if self._source is None:
            return
        self._markdown = self._source.toPlainText()
        self._render_timer.start()

    # -------------------------------------------------------------- files

    def open(self, path: Path) -> bool:
        reason = rejection_reason(path)
        if reason is not None:
            print(f"heino-reader: cannot open {path}: {reason}", file=sys.stderr)
            return False
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError as error:
            print(f"heino-reader: cannot read {path}: {error}", file=sys.stderr)
            return False
        self._markdown = text
        # The editor may not exist yet; it picks up _markdown when created.
        if self._source is not None and self._source.toPlainText() != text:
            self._source.blockSignals(True)
            self._source.setPlainText(text)
            self._source.blockSignals(False)
        self._adopt_path(path)
        self._render_now()
        return True

    def _render(self) -> None:
        self.viewer.set_markdown(self._markdown)

    def _render_now(self) -> None:
        """Render at once, dropping a pending live-preview update.

        Used wherever a stale preview would be visible: opening a file,
        switching the backend, changing the remote-image setting.
        """
        self._render_timer.stop()
        self._render()

    def _flush_pending_render(self) -> None:
        """Render now only if a debounced update is still waiting."""
        if self._render_timer.isActive():
            self._render_now()

    @Slot(str)
    def _on_file_changed(self, path: str) -> None:
        # Many editors replace the file; ensure it stays watched.
        if not self._watcher.files():
            self._watcher.addPath(path)
        if self._path is not None:
            self.open(self._path)

    # ----------------------------------------------------------- drag drop

    def dragEnterEvent(self, event) -> None:
        path = _local_file(event.mimeData())
        # Reject non-text files up front, so the cursor shows "not allowed"
        # instead of dumping an image or archive into the text engine.
        if path is not None and is_supported_path(path):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event) -> None:
        path = _local_file(event.mimeData())
        if path is None:
            event.ignore()
            return
        reason = rejection_reason(path)
        if reason is not None:
            event.ignore()
            QMessageBox.warning(
                self, "Heino Reader", f"Cannot open {path.name}: {reason}."
            )
            return
        if self.open(path):
            event.acceptProposedAction()
        else:
            event.ignore()


def _local_file(mime) -> Path | None:
    """Return the first local file from mime data, if any."""
    if not mime.hasUrls():
        return None
    for url in mime.urls():
        if url.isLocalFile():
            return Path(url.toLocalFile())
    return None
