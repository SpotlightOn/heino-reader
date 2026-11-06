"""The main window: wiring for document, editor, viewer and chrome."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from PySide6.QtCore import QFileSystemWatcher, QRect, Qt, Slot
from PySide6.QtWidgets import (
    QFileDialog,
    QMainWindow,
    QMessageBox,
    QSplitter,
    QWidget,
)

from .actions import Actions
from .chrome import build_menu, build_toolbars
from .document import Document
from .editor import ask_image, ask_link_url, ask_table_size, formatting
from .editpane import EditorPane
from .files import is_supported_path, rejection_reason
from .icons import APP_DIR
from .settings import (
    LINE_NUMBERS_KEY,
    REMOTE_IMAGES_KEY,
    RENDERER_KEY,
    SCALE_KEY,
    WRAP_CODE_KEY,
    Settings,
)
from .texts import ABOUT_TEXT, PLACEHOLDER_MD, WEB_EXTRA_HINT
from .viewer import (
    DEFAULT_RENDERER,
    RENDERER_QT,
    RENDERER_WEB,
    RENDERERS,
    ViewerArea,
    chosen_renderer,
)

ZOOM_STEP = 0.1
MIN_SCALE = 0.5
MAX_SCALE = 4.0

# Entering edit mode widens the window up to this many pixels, so the two
# panes do not get cramped; on smaller screens it is clamped to the usable
# screen width. Leaving edit mode restores the previous size.
EDIT_MODE_WIDTH = 1200


def ask_open_file(parent: QWidget, start_dir: str) -> Path | None:
    name, _ = QFileDialog.getOpenFileName(
        parent,
        "Open Markdown File",
        start_dir,
        "Markdown and text (*.md *.markdown *.mdown *.mkd *.mdx *.mdtext "
        "*.mdtxt *.txt *.text);;All files (*)",
    )
    return Path(name) if name else None


def ask_save_file(parent: QWidget, start_path: str) -> Path | None:
    name, _ = QFileDialog.getSaveFileName(
        parent,
        "Save Markdown File",
        start_path,
        "Markdown (*.md);;All files (*)",
    )
    return Path(name) if name else None


def show_about(parent: QWidget) -> None:
    QMessageBox.about(parent, "About Heino Reader", ABOUT_TEXT)


def ask_discard_changes(parent: QWidget, name: str) -> str:
    """Ask what to do with unsaved changes: discard, save or cancel."""
    box = QMessageBox(parent)
    box.setWindowTitle("Unsaved changes")
    box.setText(f"{name} has unsaved changes.")
    box.setInformativeText("Do you want to save them before continuing?")
    box.setIcon(QMessageBox.Icon.Warning)
    discard = box.addButton("Discard", QMessageBox.ButtonRole.DestructiveRole)
    save = box.addButton("Save", QMessageBox.ButtonRole.AcceptRole)
    cancel = box.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
    box.setDefaultButton(save)
    box.exec()
    clicked = box.clickedButton()
    if clicked is discard:
        return "discard"
    if clicked is save:
        return "save"
    assert clicked is cancel
    return "cancel"


class ViewerWindow(QMainWindow):
    """Read-only markdown viewer with zoom and an optional source pane."""

    def __init__(
        self, path: Path | None = None, renderer: str | None = None
    ) -> None:
        super().__init__()
        self.settings = Settings()
        self.document = Document(PLACEHOLDER_MD)
        self.scale = 1.0
        # Geometry to restore when leaving edit mode (None = never widened).
        self._pre_edit_geometry: QRect | None = None

        remembered = self.settings.get_string(RENDERER_KEY, DEFAULT_RENDERER)
        self.splitter = QSplitter(Qt.Orientation.Horizontal, self)
        self.viewer_area = ViewerArea(
            self.splitter, self, chosen_renderer(renderer, remembered), APP_DIR
        )
        self.setCentralWidget(self.splitter)
        self.editor = EditorPane(
            self.splitter, self._text_edited, self._update_edit_actions
        )
        self.editor.timer.timeout.connect(self.render)

        self.watcher = QFileSystemWatcher(self)
        self.watcher.fileChanged.connect(self._on_file_changed)

        self.setAcceptDrops(True)
        self.resize(800, 900)

        self.actions = Actions(self)
        build_menu(self)
        build_toolbars(self)
        self.set_scale(self.settings.get_float(SCALE_KEY, 1.0))
        self._sync_view_options()

        if path is not None:
            self.open(path)
        else:
            self.setWindowTitle("Heino Reader[*]")
            self.render()

    @property
    def viewer(self) -> QWidget:
        """The viewer widget currently in the splitter."""
        return self.viewer_area.view

    # ------------------------------------------------------- formatting

    def apply_format(self, func, *args) -> None:
        """Run a formatting operation on the source cursor, keep selection."""
        source = self.editor.ensure()
        cursor = source.textCursor()
        func(cursor, *args)
        source.setTextCursor(cursor)
        source.setFocus()

    def _relative_path(self, target: str) -> str:
        """Prefer a path relative to the markdown file, for portability."""
        if self.document.path is None:
            return target
        try:
            return os.path.relpath(target, self.document.path.parent)
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
    def insert_link(self) -> None:
        selected = self.editor.ensure().textCursor().selectedText()
        initial = selected if self._looks_like_url(selected) else ""
        url = ask_link_url(self, initial)
        if url:
            self.apply_format(formatting.insert_link, url)

    @Slot()
    def insert_image(self) -> None:
        source = self.editor.ensure()
        start = (
            str(self.document.path.parent)
            if self.document.path is not None
            else str(Path.home())
        )
        alt = source.textCursor().selectedText()
        choice = ask_image(self, start, alt)
        if choice is None:
            return
        path, alt_text = choice
        self.apply_format(
            formatting.insert_image, self._relative_path(path), alt_text
        )

    @Slot()
    def insert_table(self) -> None:
        size = ask_table_size(self)
        if size is None:
            return
        rows, columns = size
        self.apply_format(formatting.insert_table, rows, columns)

    # -------------------------------------------------------------- files

    @Slot()
    def open_dialog(self) -> None:
        start = (
            str(self.document.path.parent)
            if self.document.path is not None
            else str(Path.home())
        )
        path = ask_open_file(self, start)
        if path is not None:
            self.open(path)

    @Slot()
    def save(self) -> bool:
        """Write the edit buffer to the file; False when nothing was written.

        Without a file yet (the placeholder document), saving asks where to
        put it - the same path the close prompt takes.
        """
        if self.editor.source is None:
            return False
        if self.document.path is None:
            return self.save_as()
        return self._write_to(self.document.path)

    @Slot()
    def save_as(self) -> bool:
        """Write the edit buffer to the chosen file and keep editing it."""
        if self.editor.source is None:
            return False
        start = str(self.document.path or Path.home() / "untitled.md")
        path = ask_save_file(self, start)
        if path is None:
            return False
        if not self._write_to(path):
            return False
        if path != self.document.path:
            self.document.adopt(path)
            self._attach_path()
            self.render_now()
        return True

    def _write_to(self, path: Path) -> bool:
        """Write the buffer to ``path`` and clear the modified marker."""
        self.document.markdown = self.editor.text
        if not self.document.write(path):
            return False
        self._show_modified()
        return True

    def _attach_path(self) -> None:
        """Point the window at the document file: base dir, watcher, title."""
        path = self.document.path
        if path is None:
            return
        self.viewer_area.set_base_dir(path.parent)
        watched = self.watcher.files()
        if watched:
            self.watcher.removePaths(watched)
        self.watcher.addPath(str(path))
        self.setWindowTitle(
            f"{path.name} \N{EM DASH} Heino Reader[*]"
        )
        self._show_modified()
        self._update_edit_actions()

    def _show_modified(self) -> None:
        """Show unsaved changes in the title, the way Qt windows do."""
        self.setWindowModified(self.document.is_modified)

    def _confirm_discard(self) -> bool:
        """True when the buffer may go, asking about unsaved changes first.

        Guards everything that throws the buffer away: closing the window,
        opening another file, dropping a file onto the window.
        """
        if not self.document.is_modified:
            return True
        choice = ask_discard_changes(self, self.document.name)
        if choice == "discard":
            return True
        return choice == "save" and self.save()

    def _update_edit_actions(self) -> None:
        """Match saving, undo/redo and formatting to the current mode."""
        editing = self.actions.edit_mode.isChecked()
        self.actions.save.setEnabled(
            editing and self.document.path is not None
        )
        self.actions.save_as.setEnabled(editing)
        self.actions.undo.setEnabled(editing and self.editor.can_undo)
        self.actions.redo.setEnabled(editing and self.editor.can_redo)
        # Formatting only makes sense while editing, so its toolbar appears
        # with edit mode and its actions become enabled.
        self.format_toolbar.setVisible(editing)
        for action in self.actions.editing_actions:
            action.setEnabled(editing)

    @Slot()
    def undo(self) -> None:
        """Undo the last change in the source editor."""
        self.editor.undo()

    @Slot()
    def redo(self) -> None:
        """Redo the last undone change in the source editor."""
        self.editor.redo()

    @Slot()
    def show_about_dialog(self) -> None:
        show_about(self)

    # ------------------------------------------------------- view options

    @Slot(bool)
    def set_line_numbers(self, enabled: bool) -> None:
        """Switch the optional line-number gutter on or off.

        The gutter only exists once the editor has been created; until then
        the setting is just remembered and applied on first use.
        """
        self.editor.apply_line_numbers(enabled)
        self.settings.set_bool(LINE_NUMBERS_KEY, enabled)

    @Slot(bool)
    def set_remote_images(self, enabled: bool) -> None:
        """Allow or forbid downloading remote images, then re-render."""
        self.settings.set_bool(REMOTE_IMAGES_KEY, enabled)
        self._sync_view_options()
        self.render_now()

    @Slot(bool)
    def set_code_wrap(self, enabled: bool) -> None:
        """Switch wide code lines between wrapping and a page scrollbar."""
        self.settings.set_bool(WRAP_CODE_KEY, enabled)
        self._sync_view_options()
        self.render_now()

    def _sync_view_options(self) -> None:
        """Apply the View-menu toggles to the current backend."""
        self.viewer_area.apply_options(
            remote_images=self.actions.remote_images.isChecked(),
            wrap_code=self.actions.wrap_code.isChecked(),
        )

    @Slot(bool)
    def set_web_renderer(self, enabled: bool) -> None:
        """Switch between the WebEngine and the Qt text renderer."""
        self._set_renderer(RENDERER_WEB if enabled else RENDERER_QT)

    def _set_renderer(self, kind: str) -> None:
        """Swap the viewer widget for the other backend."""
        if kind not in RENDERERS or kind == self.viewer_area.kind:
            return
        if not self.viewer_area.switch(kind):
            # QtWebEngine is missing: keep the current backend and
            # explain instead of dying on a lazy import.
            QMessageBox.information(
                self, "Web Engine Renderer unavailable", WEB_EXTRA_HINT
            )
            self._check_web_renderer(False)
            return
        self.viewer_area.set_base_dir(self._base_dir())
        self._sync_view_options()
        self.settings.set_string(RENDERER_KEY, kind)
        self._check_web_renderer(kind == RENDERER_WEB)
        self.render_now()

    def _check_web_renderer(self, checked: bool) -> None:
        """Set the menu state without firing the toggle handler."""
        self.actions.web_renderer.blockSignals(True)
        self.actions.web_renderer.setChecked(checked)
        self.actions.web_renderer.blockSignals(False)

    def _base_dir(self) -> Path:
        """Directory relative links and images resolve against."""
        if self.document.path is not None:
            return self.document.path.parent
        return APP_DIR

    # --------------------------------------------------------------- zoom

    @Slot()
    def zoom_in(self) -> None:
        self.set_scale(self.scale + ZOOM_STEP)

    @Slot()
    def zoom_out(self) -> None:
        self.set_scale(self.scale - ZOOM_STEP)

    @Slot()
    def zoom_reset(self) -> None:
        self.set_scale(1.0)

    def set_scale(self, scale: float) -> None:
        self.scale = max(MIN_SCALE, min(MAX_SCALE, round(scale, 2)))
        self.viewer_area.set_zoom(self.scale)
        self.editor.set_zoom(self.scale)
        self.zoom_label.setText(f"{round(self.scale * 100)}%")
        # set_string() syncs the whole file, so skip it when the stored value
        # already matches (every startup would otherwise rewrite it).
        if self.settings.get_string(SCALE_KEY) != str(self.scale):
            self.settings.set_string(SCALE_KEY, str(self.scale))

    # --------------------------------------------------------- edit mode

    @Slot(bool)
    def set_edit_mode(self, enabled: bool) -> None:
        """Split the window (source left, viewer right) or show the viewer only."""
        if enabled:
            source = self.editor.ensure()
            # The gutter only exists now; apply the remembered preference.
            self.editor.apply_line_numbers(
                self.actions.line_numbers.isChecked()
            )
            if source.toPlainText() != self.document.markdown:
                self.editor.set_text(self.document.markdown)
            self._widen_for_edit()
            source.show()
            half = max(self.splitter.width() // 2, 1)
            self.splitter.setSizes([half, half])
        else:
            # QSplitter skips hidden widgets, so the viewer takes over.
            self.editor.set_visible(False)
            self._restore_pre_edit_geometry()
            # Leaving edit mode exposes the viewer: skip the debounce wait.
            if self.editor.timer.isActive():
                self.render_now()
        self._update_edit_actions()

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
    def _text_edited(self) -> None:
        """Mirror the buffer; the viewer waits for the typing to pause.

        The text is taken over immediately - saving must not lag behind -
        while the render is started by the editor's timer.
        """
        self.document.markdown = self.editor.text
        self._show_modified()

    # ------------------------------------------------------------- render

    def render(self) -> None:
        """Show the document in the viewer."""
        self.viewer_area.set_markdown(self.document.markdown)

    def render_now(self) -> None:
        """Render at once, dropping a pending live-render update.

        Used wherever a stale view would be visible: opening a file,
        switching the backend, changing the remote-image setting.
        """
        self.editor.timer.stop()
        self.render()

    # -------------------------------------------------------------- files

    def closeEvent(self, event) -> None:
        """Ask about unsaved changes before the window goes away."""
        if self._confirm_discard():
            event.accept()
        else:
            event.ignore()

    def open(self, path: Path) -> bool:
        """Show ``path``, asking about unsaved changes first."""
        reason = rejection_reason(path)
        if reason is not None:
            print(
                f"heino-reader: cannot open {path}: {reason}", file=sys.stderr
            )
            return False
        if not self._confirm_discard():
            return False
        previous = self.document.path
        if not self.document.read(path):
            return False
        if self.editor.source is not None:
            replaced = self.editor.text != self.document.markdown
            if replaced:
                self.editor.set_text(self.document.markdown)
            if replaced or path != previous:
                # A document must never be undoable into the one before it.
                self.editor.clear_history()
        self._attach_path()
        self.render_now()
        return True

    @Slot(str)
    def _on_file_changed(self, path: str) -> None:
        # Many editors replace the file; ensure it stays watched.
        if not self.watcher.files():
            self.watcher.addPath(path)
        if self.document.path is not None:
            self.open(self.document.path)

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
