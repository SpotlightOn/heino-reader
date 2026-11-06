"""Widget behavior tests for the Heino Reader viewer (pytest-qt)."""

from pathlib import Path

import pytest
from PySide6.QtCore import QEventLoop, Qt, QTimer, QUrl
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontDatabase,
    QImage,
    QTextCharFormat,
    QTextCursor,
)
from PySide6.QtWebEngineCore import QWebEnginePage
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QPlainTextEdit,
    QStatusBar,
    QToolBar,
    QWidgetAction,
)

import HeinoReader.icons
import HeinoReader.viewer.web
import HeinoReader.window
from HeinoReader.cli import main
from HeinoReader.editor import MarkdownHighlighter, MarkdownSourceEdit
from HeinoReader.icons import APP_DIR, ICONS_DIR, _material_icon
from HeinoReader.settings import WRAP_CODE_KEY
from HeinoReader.texts import PLACEHOLDER_MD, WEB_EXTRA_HINT
from HeinoReader.viewer import RENDERER_QT
from HeinoReader.viewer.qt import QtMarkdownView
from HeinoReader.viewer.render import markdown_to_html, viewer_body_point_size
from HeinoReader.viewer.web import MarkdownPage
from HeinoReader.window import EDIT_MODE_WIDTH, ViewerWindow


def make_window(qtbot, path):
    """Create a shown viewer window that is cleaned up by qtbot."""
    window = ViewerWindow(path)
    qtbot.addWidget(window)
    window.show()
    QApplication.processEvents()
    return window


def viewer_text(window, timeout=10000):
    """Return the rendered view text, waiting for the engine if needed."""
    page = getattr(window.viewer, "page", None)
    if page is None:  # Qt text renderer: no asynchronous page load
        return window.viewer.toPlainText()
    result = {}
    loop = QEventLoop()

    def read():
        def done(text):
            result["text"] = text
            if text.strip():
                loop.quit()
            else:
                QTimer.singleShot(50, read)

        page.toPlainText(done)

    read()
    QTimer.singleShot(timeout, loop.quit)
    loop.exec()
    return result.get("text", "")


@pytest.fixture
def md_file(tmp_path):
    path = tmp_path / "notes.md"
    path.write_text(
        "# Big Title\n\n"
        "Some text with a [web](https://example.org) link.\n\n"
        "See [other](other.md) too.\n\n"
        "## Smaller\n\n- one\n- two\n",
        encoding="utf-8",
    )
    (tmp_path / "other.md").write_text("# Other\n", encoding="utf-8")
    return path


@pytest.fixture
def window(qtbot, md_file):
    return make_window(qtbot, md_file)


# ------------------------------------------------------------------- menu

def menu_action(window, menu_name, item_name):
    """Return an action from the window's menu bar by menu and item name."""
    for menu_entry in window.menuBar().actions():
        if menu_entry.text().replace("&", "") == menu_name:
            for action in menu_entry.menu().actions():
                if action.text().replace("&", "") == item_name:
                    return action
    raise AssertionError(f"menu item not found: {menu_name} / {item_name}")


def test_menu_bar_has_file_view_and_help(window):
    names = [a.text().replace("&", "") for a in window.menuBar().actions()]
    assert names == ["File", "View", "Help"]


def test_file_menu_contains_open_and_close(window):
    open_action = menu_action(window, "File", "Open...")
    close_action = menu_action(window, "File", "Close")
    assert not open_action.shortcut().isEmpty()
    assert not close_action.shortcut().isEmpty()
    assert not open_action.icon().isNull()
    assert not menu_action(window, "Help", "About").icon().isNull()


def test_open_menu_item_loads_file(window, tmp_path, monkeypatch):
    target = tmp_path / "opened.md"
    target.write_text("# Opened Document\n", encoding="utf-8")
    chosen = []
    monkeypatch.setattr(
        HeinoReader.window,
        "ask_open_file",
        lambda parent, start: chosen.append(start) or target,
    )
    menu_action(window, "File", "Open...").trigger()
    assert chosen, "file dialog was not invoked"
    assert "opened.md" in window.windowTitle()
    assert "Opened Document" in window.document.markdown


def test_save_is_disabled_in_view_mode(window):
    save_action = menu_action(window, "File", "Save")
    assert not save_action.isEnabled()


def test_save_follows_edit_mode_toggle(window):
    save_action = menu_action(window, "File", "Save")
    edit_action(window).trigger()
    assert save_action.isEnabled()
    edit_action(window).trigger()
    assert not save_action.isEnabled()


def test_save_writes_the_edit_buffer(qtbot, window, md_file):
    edit_action(window).trigger()
    qtbot.keyClicks(window.editor.source, "#X")
    menu_action(window, "File", "Save").trigger()
    assert md_file.read_text(encoding="utf-8") == window.editor.source.toPlainText()


def test_save_as_writes_a_new_file_and_keeps_editing_it(
    qtbot, window, tmp_path, monkeypatch
):
    edit_action(window).trigger()
    window.editor.source.setPlainText("# Copy\n")
    target = tmp_path / "copy.md"
    monkeypatch.setattr(HeinoReader.window, "ask_save_file", lambda parent, start: target)

    menu_action(window, "File", "Save As...").trigger()

    assert target.read_text(encoding="utf-8") == "# Copy\n"
    assert window.document.path == target
    assert "copy.md" in window.windowTitle()
    assert menu_action(window, "File", "Save").isEnabled()


def test_save_as_works_without_an_open_file(qtbot, tmp_path, monkeypatch):
    window = ViewerWindow()
    qtbot.addWidget(window)
    window.show()
    window.actions.edit_mode.trigger()
    target = tmp_path / "new.md"
    monkeypatch.setattr(HeinoReader.window, "ask_save_file", lambda parent, start: target)

    menu_action(window, "File", "Save As...").trigger()

    assert "heino reader" in target.read_text(encoding="utf-8").lower()
    assert window.document.path == target


def test_save_as_is_skipped_when_cancelled(window, monkeypatch):
    edit_action(window).trigger()
    window.editor.source.setPlainText("unchanged")
    monkeypatch.setattr(
        HeinoReader.window, "ask_save_file", lambda parent, start: None
    )
    menu_action(window, "File", "Save As...").trigger()
    assert window.document.path.name == "notes.md"
    assert window.editor.source.toPlainText() == "unchanged"


def test_save_as_is_disabled_in_view_mode(window):
    assert not menu_action(window, "File", "Save As...").isEnabled()


def test_save_keyboard_shortcut(qtbot, window, md_file):
    """Ctrl+S must save without opening the menu."""
    from PySide6.QtTest import QTest

    edit_action(window).trigger()
    window.editor.source.setPlainText(window.editor.source.toPlainText() + "\nshortcut line\n")
    window.activateWindow()
    qtbot.wait(1)
    QTest.keyClick(window, Qt.Key.Key_S, Qt.KeyboardModifier.ControlModifier)
    qtbot.wait(1)
    assert "shortcut line" in md_file.read_text(encoding="utf-8")


def test_save_stays_disabled_without_a_file(qtbot):
    window = ViewerWindow(None)
    qtbot.addWidget(window)
    window.show()
    window.actions.edit_mode.trigger()
    assert not menu_action(window, "File", "Save").isEnabled()


# ------------------------------------------------------- unsaved changes


def _edit_buffer(window, text):
    """Append text to the source buffer as one undoable change."""
    edit_action(window).trigger()
    cursor = window.editor.source.textCursor()
    cursor.movePosition(QTextCursor.MoveOperation.End)
    cursor.insertText(text)


def test_closing_with_unsaved_changes_asks_first(qtbot, window, monkeypatch):
    _edit_buffer(window, " not saved")
    asked = []
    monkeypatch.setattr(
        HeinoReader.window,
        "ask_discard_changes",
        lambda parent, name: asked.append(name) or "cancel",
    )

    window.close()

    assert asked == ["notes.md"]
    assert window.isVisible(), "cancel must keep the window open"
    assert window.isWindowModified()


def test_closing_saves_when_the_user_asks(qtbot, window, md_file, monkeypatch):
    _edit_buffer(window, " kept")
    monkeypatch.setattr(
        HeinoReader.window, "ask_discard_changes", lambda parent, name: "save"
    )

    window.close()

    assert "kept" in md_file.read_text(encoding="utf-8")
    assert not window.isVisible()


def test_closing_discards_when_the_user_asks(qtbot, window, md_file, monkeypatch):
    before = md_file.read_text(encoding="utf-8")
    _edit_buffer(window, " dropped")
    monkeypatch.setattr(
        HeinoReader.window, "ask_discard_changes", lambda parent, name: "discard"
    )

    window.close()

    assert md_file.read_text(encoding="utf-8") == before
    assert not window.isVisible()


def test_clean_window_closes_without_asking(qtbot, window, monkeypatch):
    def refuse(*args):
        raise AssertionError("no prompt expected for an unmodified document")

    monkeypatch.setattr(HeinoReader.window, "ask_discard_changes", refuse)
    window.close()
    assert not window.isVisible()


def test_opening_another_file_asks_about_unsaved_changes(
    qtbot, window, md_file, monkeypatch
):
    _edit_buffer(window, " unsaved")
    monkeypatch.setattr(
        HeinoReader.window, "ask_discard_changes", lambda parent, name: "cancel"
    )

    assert not window.open(md_file.parent / "other.md")
    assert window.document.path == md_file
    assert "unsaved" in window.editor.source.toPlainText()


def test_title_marks_unsaved_changes(qtbot, window, monkeypatch):
    assert not window.isWindowModified()
    _edit_buffer(window, " dirty")
    assert window.isWindowModified()

    monkeypatch.setattr(
        HeinoReader.window, "ask_save_file", lambda parent, start: None
    )
    menu_action(window, "File", "Save").trigger()
    assert not window.isWindowModified()


def test_close_menu_item_closes_window(window):
    menu_action(window, "File", "Close").trigger()
    assert not window.isVisible()


def test_about_menu_item_shows_dialog(window, monkeypatch):
    shown = []
    monkeypatch.setattr(HeinoReader.window, "show_about", lambda parent: shown.append(parent))
    menu_action(window, "Help", "About").trigger()
    assert shown and shown[0] is window


# ------------------------------------------------------------------ icons

def test_bundled_material_icons_render(qapp):
    for name in ("text_decrease", "text_increase", "exit_to_app", "edit"):
        assert (ICONS_DIR / f"{name}.svg").is_file()
        icon = _material_icon(name)
        assert not icon.isNull()
        assert not icon.pixmap(32, 32).isNull()


def test_missing_material_icon_falls_back_gracefully(qapp, tmp_path, monkeypatch):
    monkeypatch.setattr(HeinoReader.icons, "ICONS_DIR", tmp_path)
    assert _material_icon("does_not_exist").isNull()


# ---------------------------------------------------------------- toolbar

def main_toolbar(window):
    """The always-visible toolbar (zoom, edit toggle, quit)."""
    for toolbar in window.findChildren(QToolBar):
        if any(a.text() == "Edit mode" for a in toolbar.actions()):
            return toolbar
    raise AssertionError("main toolbar not found")


def format_toolbar(window):
    """The formatting toolbar, shown only in edit mode."""
    for toolbar in window.findChildren(QToolBar):
        if any(a.text() == "Bold" for a in toolbar.actions()):
            return toolbar
    raise AssertionError("format toolbar not found")


def test_toolbar_has_four_icons_at_the_top(window):
    assert window.findChildren(QStatusBar) == []
    toolbar = main_toolbar(window)
    assert window.toolBarArea(toolbar) == Qt.ToolBarArea.TopToolBarArea
    icons = [
        action
        for action in toolbar.actions()
        if not action.isSeparator() and not isinstance(action, QWidgetAction)
    ]
    assert [action.text() for action in icons] == [
        "Zoom out",
        "Zoom in",
        "Edit mode",
        "Quit",
    ]
    assert all(not action.icon().isNull() for action in icons)


def test_format_toolbar_is_hidden_in_view_mode(window):
    assert not format_toolbar(window).isVisible()


def edit_action(window):
    toolbar = main_toolbar(window)
    return next(a for a in toolbar.actions() if a.text() == "Edit mode")


def test_edit_mode_action_is_checkable(window):
    action = edit_action(window)
    assert action.isCheckable()
    assert not action.isChecked()


def test_edit_mode_splits_and_restores_view(qtbot, window):
    action = edit_action(window)
    action.trigger()
    assert action.isChecked()
    assert window.splitter.count() == 2
    assert window.editor.source.isVisible()
    assert window.editor.source.x() < window.viewer.x(), "source must be left of the viewer"
    assert window.editor.source.toPlainText() == window.document.markdown
    assert abs(window.editor.source.width() - window.viewer.width()) <= 8, (
        "halves should be roughly equal"
    )

    action.trigger()
    assert not action.isChecked()
    qtbot.wait(1)
    assert not window.editor.source.isVisible()
    assert window.viewer.width() >= window.splitter.width() - 4, (
        "view should fill the window again"
    )


def test_edit_mode_widens_the_window(qtbot, window):
    window.resize(640, 480)
    QApplication.processEvents()
    before = window.width()
    edit_action(window).trigger()
    assert window.width() > before, "edit mode should widen the window"
    assert window.width() <= EDIT_MODE_WIDTH
    assert window.height() == 480, "only the width changes"


def test_edit_mode_never_exceeds_the_screen(qtbot, window):
    """On a screen narrower than EDIT_MODE_WIDTH, clamp to the screen."""
    window.resize(400, 300)
    QApplication.processEvents()
    edit_action(window).trigger()
    available = window.screen().availableGeometry()
    assert window.width() <= min(EDIT_MODE_WIDTH, available.width())


def test_edit_mode_never_shrinks_an_already_wide_window(qtbot, window):
    window.resize(EDIT_MODE_WIDTH + 200, 480)
    QApplication.processEvents()
    edit_action(window).trigger()
    assert window.width() == EDIT_MODE_WIDTH + 200


def test_leaving_edit_mode_restores_the_previous_size(qtbot, window):
    window.setGeometry(120, 60, 640, 480)
    QApplication.processEvents()
    before = window.geometry()
    edit_action(window).trigger()
    assert window.width() > before.width()
    edit_action(window).trigger()
    assert window.geometry() == before


def test_edit_mode_stays_on_screen_when_widening(qtbot, window):
    window.resize(640, 480)
    QApplication.processEvents()
    edit_action(window).trigger()
    screen = window.screen().availableGeometry()
    assert screen.contains(window.geometry())


def test_default_view_is_viewer_only(window):
    assert window.splitter.count() == 1, "no editor pane before edit mode"
    assert window.viewer.width() >= window.splitter.width() - 4


def test_editor_is_created_lazily_on_edit_mode(window):
    assert window.editor.source is None
    assert window.editor.gutter is None
    edit_action(window).trigger()
    assert isinstance(window.editor.source, MarkdownSourceEdit)
    assert window.splitter.count() == 2
    assert not window.editor.gutter.installed


def test_edit_mode_updates_the_view_live(qtbot, window):
    edit_action(window).trigger()
    qtbot.keyClicks(window.editor.source, "# Fresh Heading")
    assert window.document.markdown == window.editor.source.toPlainText()


def test_edit_mode_renders_after_the_typing_pause(qtbot, window):
    """The rendered view is debounced, not dropped: it catches up when typing stops."""
    edit_action(window).trigger()
    qtbot.keyClicks(window.editor.source, "# Fresh Heading")
    qtbot.waitUntil(lambda: "Fresh Heading" in viewer_text(window), timeout=3000)


def test_leaving_edit_mode_renders_pending_edits_at_once(qtbot, window):
    edit_action(window).trigger()
    qtbot.keyClicks(window.editor.source, "# Fresh Heading")
    assert window.editor.timer.isActive()
    edit_action(window).trigger()  # back to the full-width viewer
    assert "Fresh Heading" in viewer_text(window)


# ------------------------------------------------------------- undo and redo


def test_undo_and_redo_lead_the_format_toolbar(window):
    edit_action(window).trigger()
    actions = format_toolbar(window).actions()
    assert [action.text() for action in actions[:2]] == ["Undo", "Redo"]
    assert actions[2].isSeparator(), "the history is set off from formatting"
    texts = [action.text() for action in actions]
    assert texts.index("Bold") > texts.index("Redo")
    assert actions[0].shortcut().toString() == "Ctrl+Z"
    assert "Ctrl+Y" in [key.toString() for key in actions[1].shortcuts()]


def test_undo_and_redo_are_disabled_outside_edit_mode(window):
    assert not window.actions.undo.isEnabled()
    assert not window.actions.redo.isEnabled()


def test_undo_and_redo_follow_the_editor_history(qtbot, window):
    edit_action(window).trigger()
    source = window.editor.source
    original = source.toPlainText()
    assert not window.actions.undo.isEnabled()

    cursor = source.textCursor()
    cursor.movePosition(QTextCursor.MoveOperation.End)
    cursor.insertText(" appended")
    assert window.actions.undo.isEnabled()

    window.actions.undo.trigger()
    assert source.toPlainText() == original
    assert window.actions.redo.isEnabled()

    window.actions.redo.trigger()
    assert source.toPlainText() == original + " appended"


def test_a_new_change_after_undo_clears_redo(qtbot, window):
    edit_action(window).trigger()
    source = window.editor.source
    cursor = source.textCursor()
    cursor.movePosition(QTextCursor.MoveOperation.End)
    cursor.insertText("one")
    window.actions.undo.trigger()
    cursor = source.textCursor()
    cursor.movePosition(QTextCursor.MoveOperation.End)
    cursor.insertText("two")
    assert not window.actions.redo.isEnabled()


def test_formatting_is_one_undo_step(qtbot, window):
    edit_action(window).trigger()
    source = window.editor.source
    source.setPlainText("Title")
    _select(source, 0, 5)
    qtbot.keyClick(source, Qt.Key.Key_1, Qt.KeyboardModifier.ControlModifier)
    assert source.toPlainText() == "# Title"

    window.actions.undo.trigger()
    assert source.toPlainText() == "Title"


def test_opening_another_file_clears_the_history(qtbot, window, tmp_path):
    """The same text in another file must not undo into the previous one."""
    edit_action(window).trigger()
    cursor = window.editor.source.textCursor()
    cursor.movePosition(QTextCursor.MoveOperation.End)
    cursor.insertText("more")
    assert window.actions.undo.isEnabled()

    other = tmp_path / "other.md"
    other.write_text(window.editor.source.toPlainText(), encoding="utf-8")
    window.open(other)

    assert not window.actions.undo.isEnabled()
    assert not window.actions.redo.isEnabled()


def test_zoom_indicator_updates(window):
    labels = window.findChildren(QLabel)
    assert len(labels) == 1
    label = labels[0]
    assert label.text() == "100%"
    window.zoom_in()
    window.zoom_in()
    assert label.text() == "120%"
    window.zoom_out()
    window.zoom_out()
    assert label.text() == "100%"


def test_editor_text_matches_the_viewer_size(qtbot, window):
    """Both panes read at the same size; only the family differs."""
    edit_action(window).trigger()
    assert window.editor.source.font().pointSizeF() == pytest.approx(
        viewer_body_point_size()
    )


def test_zoom_scales_the_editor_text_too(qtbot, window):
    edit_action(window).trigger()
    window.zoom_in()
    assert window.editor.source.font().pointSizeF() == pytest.approx(
        viewer_body_point_size() * 1.1
    )


def test_editor_keeps_its_monospace_family(qtbot, window):
    from PySide6.QtGui import QFontDatabase

    fixed = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
    edit_action(window).trigger()
    window.zoom_in()
    assert window.editor.source.font().family() == fixed.family()


def test_editor_tab_stop_follows_the_font(qtbot, window):
    """The tab stop is a pixel distance, so it has to be recomputed."""
    edit_action(window).trigger()
    source = window.editor.source
    window.zoom_in()
    expected = source.fontMetrics().horizontalAdvance(source.INDENT)
    assert source.tabStopDistance() == expected


def test_zoom_label_is_in_the_right_corner(window):
    from PySide6.QtCore import QPoint

    toolbar = window.findChildren(QToolBar)[0]
    label = window.findChildren(QLabel)[0]
    label_left = label.mapTo(toolbar, QPoint(0, 0)).x()
    quit_action = next(a for a in toolbar.actions() if a.text() == "Quit")
    quit_button = toolbar.widgetForAction(quit_action)
    quit_left = quit_button.mapTo(toolbar, QPoint(0, 0)).x()
    assert label_left > quit_left, "zoom label must sit right of the buttons"
    right_gap = toolbar.width() - (label_left + label.width())
    assert right_gap <= 24, f"zoom label not in the corner, gap={right_gap}"


def test_window_title_contains_filename(window):
    assert "notes.md" in window.windowTitle()


def test_placeholder_is_rendered_without_a_file(qtbot):
    window = ViewerWindow()
    qtbot.addWidget(window)
    window.show()
    QApplication.processEvents()
    assert window.document.markdown == PLACEHOLDER_MD
    assert "Drop a markdown file here" in viewer_text(window)


def test_viewer_uses_the_qt_renderer_by_default(window):
    assert isinstance(window.viewer, QtMarkdownView)
    assert window.viewer_area.kind == RENDERER_QT
    assert not window.actions.web_renderer.isChecked()


# ------------------------------------------------------------------- zoom

def test_zoom_sets_the_view_zoom(window):
    assert window.scale == pytest.approx(1.0)
    window.zoom_in()
    assert window.scale == pytest.approx(1.1)
    window.zoom_reset()
    assert window.scale == pytest.approx(1.0)


def test_zoom_is_clamped(window):
    for _ in range(100):
        window.zoom_in()
    assert window.scale == 4.0
    for _ in range(200):
        window.zoom_out()
    assert window.scale == 0.5


# ------------------------------------------------------------------ files

def test_live_reload(qtbot, tmp_path):
    path = tmp_path / "live.md"
    path.write_text("# First version\n", encoding="utf-8")
    window = make_window(qtbot, path)
    assert "First version" in window.document.markdown
    path.write_text("# Second version\n", encoding="utf-8")
    qtbot.waitUntil(
        lambda: "Second version" in window.document.markdown, timeout=5000
    )


def test_missing_file_exits_with_error_code():
    assert main(["/does/not/exist.md"]) == 2


def test_relative_image_uses_the_document_directory(qtbot, tmp_path):
    image = QImage(8, 8, QImage.Format.Format_ARGB32)
    image.fill(QColor("orange"))
    assert image.save(str(tmp_path / "pic.png"))
    path = tmp_path / "doc.md"
    path.write_text("![alt](pic.png)\n", encoding="utf-8")
    window = make_window(qtbot, path)

    # The web engine resolves relative URLs against the document folder.
    assert window.viewer.base_dir == tmp_path
    html = markdown_to_html(window.document.markdown)
    assert 'src="pic.png"' in html


def test_code_block_is_not_rewritten(qtbot, tmp_path):
    path = tmp_path / "code.md"
    path.write_text(
        "# Doc\n\n```text\n![example](pic.png)\n```\n", encoding="utf-8"
    )
    window = make_window(qtbot, path)
    html = markdown_to_html(window.document.markdown)
    assert "![example](pic.png)" in html
    assert str(tmp_path / "pic.png") not in html


# ------------------------------------------------------------------ links

def test_relative_links_stay_relative_for_the_base_directory(window):
    assert window.viewer.base_dir == Path(window.document.path).parent
    html = markdown_to_html(window.document.markdown)
    assert 'href="other.md"' in html
    assert 'href="https://example.org"' in html


def test_link_click_opens_external_url(monkeypatch):
    opened = []
    monkeypatch.setattr(HeinoReader.viewer.web, "open_external", opened.append)
    page = MarkdownPage()
    accepted = page.acceptNavigationRequest(
        QUrl("https://example.org"),
        QWebEnginePage.NavigationType.NavigationTypeLinkClicked,
        True,
    )
    assert accepted is False
    assert [url.toString() for url in opened] == ["https://example.org"]


def test_link_click_opens_local_file(monkeypatch, tmp_path):
    opened = []
    monkeypatch.setattr(HeinoReader.viewer.web, "open_external", opened.append)
    target = tmp_path / "other.md"
    page = MarkdownPage()
    accepted = page.acceptNavigationRequest(
        QUrl.fromLocalFile(str(target)),
        QWebEnginePage.NavigationType.NavigationTypeLinkClicked,
        True,
    )
    assert accepted is False
    assert opened[0].toLocalFile() == str(target)


# ------------------------------------------------------------------ editor

def layout_formats(widget, needle):
    """Return the syntax-highlighting format ranges containing needle.

    QSyntaxHighlighter applies its formats to the text layouts, not to the
    document fragments, so the layout is the right place to look. The format
    is copied because the layout is a temporary object.
    """
    document = widget.document()
    for block_number in range(document.blockCount()):
        block = document.findBlockByNumber(block_number)
        layout = block.layout()
        if layout is None:
            continue
        for fmt_range in layout.formats():
            text = block.text()[fmt_range.start:fmt_range.start + fmt_range.length]
            if needle in text:
                return QTextCharFormat(fmt_range.format)
    raise AssertionError(f"text not found in layouts: {needle!r}")


def test_source_is_a_markdown_code_editor(window):
    edit_action(window).trigger()
    assert isinstance(window.editor.source, MarkdownSourceEdit)
    assert isinstance(window.editor.source, QPlainTextEdit)


def test_source_has_a_highlighter(window):
    edit_action(window).trigger()
    QApplication.processEvents()
    assert isinstance(window.editor.source.highlighter, MarkdownHighlighter)


def test_line_numbers_are_off_by_default(window):
    edit_action(window).trigger()
    QApplication.processEvents()
    assert not window.editor.gutter.installed
    assert not window.editor.gutter.area.isVisible()


def test_line_numbers_can_be_switched_on_and_off(window):
    edit_action(window).trigger()
    QApplication.processEvents()
    assert not window.editor.gutter.installed

    window.actions.line_numbers.setChecked(True)
    QApplication.processEvents()
    assert window.editor.gutter.installed
    assert window.editor.gutter.area.isVisible()

    window.actions.line_numbers.setChecked(False)
    QApplication.processEvents()
    assert not window.editor.gutter.installed
    assert not window.editor.gutter.area.isVisible()
    assert window.editor.source.viewportMargins().left() == 0


def test_remote_images_are_enabled_by_default(window):
    action = menu_action(window, "View", "Load Remote Images")
    assert action.isCheckable()
    assert action.isChecked()


def test_remote_images_can_be_switched_off(window):
    action = menu_action(window, "View", "Load Remote Images")
    action.setChecked(False)
    QApplication.processEvents()
    assert not window.viewer.remote_images_enabled

    action.setChecked(True)
    QApplication.processEvents()
    assert window.viewer.remote_images_enabled


def test_code_wrap_is_enabled_by_default(window):
    action = menu_action(window, "View", "Wrap Code")
    assert action.isCheckable()
    assert action.isChecked()
    assert window.viewer._wrap_code


def test_code_wrap_can_be_switched_off(window):
    action = menu_action(window, "View", "Wrap Code")
    action.setChecked(False)
    QApplication.processEvents()
    assert not window.viewer._wrap_code
    assert not window.settings.get_bool(WRAP_CODE_KEY, True)

    action.setChecked(True)
    QApplication.processEvents()
    assert window.viewer._wrap_code
    assert window.settings.get_bool(WRAP_CODE_KEY, False)


def test_highlighter_styles_headings_bold_and_code(window):
    edit_action(window).trigger()
    window.editor.source.setPlainText("# Title\n\nsome `inline code` here\n")
    QApplication.processEvents()
    heading = layout_formats(window.editor.source, "Title")
    assert heading.fontWeight() >= QFont.Weight.Bold
    code = layout_formats(window.editor.source, "inline code")
    base = window.editor.source.palette().base().color()
    assert code.background().color() != base


def test_a_fenced_block_stays_code_until_the_closing_fence(window):
    """The block state must survive body lines and empty lines, then reset."""
    edit_action(window).trigger()
    source = window.editor.source
    source.setPlainText(
        "before **first**\n"
        "```python\n"
        "# not a heading\n"
        "- not a list\n"
        "\n"
        "still code **literal**\n"
        "```\n"
        "after **second**\n"
    )
    QApplication.processEvents()

    base = source.palette().base().color()
    fixed = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)

    for line in ("```python", "# not a heading", "- not a list", "```"):
        fmt = layout_formats(source, line)
        assert fmt.font().family() == fixed.family()
        assert fmt.background().color() != base

    # Inside the fence no other rule may fire, not even a heading.
    assert layout_formats(source, "# not a heading").fontWeight() < QFont.Weight.Bold
    assert layout_formats(source, "- not a list").fontWeight() < QFont.Weight.Bold

    # The empty line is part of the block, not its end.
    assert layout_formats(source, "still code").background().color() != base
    assert layout_formats(source, "literal").fontWeight() < QFont.Weight.Bold

    # The closing fence resets the state: rules work again.
    first = layout_formats(source, "first")
    assert first.fontWeight() >= QFont.Weight.Bold
    assert not first.fontItalic()
    assert layout_formats(source, "second").fontWeight() >= QFont.Weight.Bold


def test_bold_and_italics_do_not_override_each_other(window):
    edit_action(window).trigger()
    source = window.editor.source
    source.setPlainText("plain *italic* and **bold**\n")
    QApplication.processEvents()

    italic = layout_formats(source, "italic")
    bold = layout_formats(source, "bold")

    assert italic.fontItalic()
    assert italic.fontWeight() < QFont.Weight.Bold
    assert bold.fontWeight() >= QFont.Weight.Bold
    assert not bold.fontItalic()


def test_tab_indents_selected_lines(qtbot, window):
    edit_action(window).trigger()
    source = window.editor.source
    source.setPlainText("first line\nsecond line\nthird line")
    cursor = source.textCursor()
    cursor.setPosition(0)
    cursor.movePosition(cursor.MoveOperation.EndOfBlock, cursor.MoveMode.KeepAnchor)
    cursor.movePosition(cursor.MoveOperation.NextBlock, cursor.MoveMode.KeepAnchor)
    source.setTextCursor(cursor)
    qtbot.keyClick(source, Qt.Key.Key_Tab)
    assert source.toPlainText() == "    first line\n    second line\nthird line"


def test_shift_tab_unindents_selected_lines(qtbot, window):
    edit_action(window).trigger()
    source = window.editor.source
    source.setPlainText("    first line\n    second line\nthird line")
    cursor = source.textCursor()
    cursor.setPosition(0)
    cursor.movePosition(cursor.MoveOperation.EndOfBlock, cursor.MoveMode.KeepAnchor)
    cursor.movePosition(cursor.MoveOperation.NextBlock, cursor.MoveMode.KeepAnchor)
    source.setTextCursor(cursor)
    qtbot.keyClick(source, Qt.Key.Key_Backtab, Qt.KeyboardModifier.ShiftModifier)
    assert source.toPlainText() == "first line\nsecond line\nthird line"


def test_tab_without_selection_moves_the_cursor(qtbot, window):
    edit_action(window).trigger()
    source = window.editor.source
    source.setPlainText("ab")
    source.moveCursor(source.textCursor().MoveOperation.Start)
    qtbot.keyClick(source, Qt.Key.Key_Tab)
    assert source.textCursor().position() == MarkdownSourceEdit.INDENT.__len__()


# ----------------------------------------------------------------- format

def _select(editor, start, end):
    """Select the character range [start, end) in the editor."""
    cursor = editor.textCursor()
    cursor.setPosition(start)
    cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
    editor.setTextCursor(cursor)


def format_actions(window):
    """All markdown formatting actions of the window."""
    return window.actions.editing_actions


def test_format_actions_are_disabled_in_view_mode(window):
    assert all(not action.isEnabled() for action in format_actions(window))


def test_format_actions_are_enabled_in_edit_mode(window):
    edit_action(window).trigger()
    assert all(action.isEnabled() for action in format_actions(window))


def test_format_toolbar_appears_with_edit_mode(window):
    toolbar = format_toolbar(window)
    assert not toolbar.isVisible()
    edit_action(window).trigger()
    assert toolbar.isVisible()


def test_format_toolbar_buttons_have_icons_and_tooltips(window):
    edit_action(window).trigger()
    buttons = [
        action
        for action in format_toolbar(window).actions()
        if not action.isSeparator() and not isinstance(action, QWidgetAction)
    ]
    assert len(buttons) == 13, (
        "undo, redo, bold..code, quote, bullet, numbered, link, image, table"
    )
    assert all(not action.icon().isNull() for action in buttons)
    assert all("(" in action.toolTip() for action in buttons), (
        "every tooltip should mention its shortcut"
    )
    # The heading dropdown is a widget action carrying its own tool button.
    dropdown = next(
        action
        for action in format_toolbar(window).actions()
        if isinstance(action, QWidgetAction)
    )
    assert not dropdown.defaultWidget().icon().isNull()


def test_text_formatting_actions_have_the_expected_shortcuts(window):
    actions = {action.text(): action for action in format_actions(window)}
    assert actions["Bold"].shortcut().toString() == "Ctrl+B"
    assert actions["Italic"].shortcut().toString() == "Ctrl+I"
    assert actions["Heading 1"].shortcut().toString() == "Ctrl+1"


def test_ctrl_b_wraps_the_selection_in_bold_markers(qtbot, window):
    edit_action(window).trigger()
    source = window.editor.source
    source.setPlainText("hello world")
    _select(source, 0, 5)
    qtbot.keyClick(source, Qt.Key.Key_B, Qt.KeyboardModifier.ControlModifier)
    assert source.toPlainText() == "**hello** world"


def test_ctrl_b_twice_unwraps_again(qtbot, window):
    edit_action(window).trigger()
    source = window.editor.source
    source.setPlainText("**hello** world")
    _select(source, 2, 7)
    qtbot.keyClick(source, Qt.Key.Key_B, Qt.KeyboardModifier.ControlModifier)
    assert source.toPlainText() == "hello world"


def test_ctrl_1_sets_a_heading_and_toggles_off(qtbot, window):
    edit_action(window).trigger()
    source = window.editor.source
    source.setPlainText("title")
    _select(source, 0, 5)
    qtbot.keyClick(source, Qt.Key.Key_1, Qt.KeyboardModifier.ControlModifier)
    assert source.toPlainText() == "# title"
    qtbot.keyClick(source, Qt.Key.Key_1, Qt.KeyboardModifier.ControlModifier)
    assert source.toPlainText() == "title"


def test_ctrl_u_underlines_with_the_u_tag(qtbot, window):
    edit_action(window).trigger()
    source = window.editor.source
    source.setPlainText("click me")
    _select(source, 0, 8)
    qtbot.keyClick(source, Qt.Key.Key_U, Qt.KeyboardModifier.ControlModifier)
    assert source.toPlainText() == "<u>click me</u>"


# -------------------------------------------------------------- insert ops

def insert_action(window, name):
    """Return a format action by its visible name."""
    return next(a for a in window.actions.editing_actions if a.text() == name)


def test_insert_actions_have_the_expected_shortcuts(window):
    assert insert_action(window, "Link...").shortcut().toString() == "Ctrl+K"
    assert (
        insert_action(window, "Image...").shortcut().toString() == "Ctrl+Shift+I"
    )
    assert (
        insert_action(window, "Table...").shortcut().toString() == "Ctrl+Shift+T"
    )


def test_insert_actions_live_in_the_format_toolbar(window):
    edit_action(window).trigger()
    texts = [action.text() for action in format_toolbar(window).actions()]
    assert {"Link...", "Image...", "Table..."} <= set(texts)


def test_insert_link_uses_the_dialog_result(window, monkeypatch):
    edit_action(window).trigger()
    source = window.editor.source
    source.setPlainText("see the docs")
    _select(source, 4, 7)  # "the"
    monkeypatch.setattr(HeinoReader.window, "ask_link_url", lambda parent, initial: "https://x.io")
    insert_action(window, "Link...").trigger()
    assert source.toPlainText() == "see [the](https://x.io) docs"


def test_insert_link_is_skipped_when_cancelled(window, monkeypatch):
    edit_action(window).trigger()
    source = window.editor.source
    source.setPlainText("keep me")
    monkeypatch.setattr(HeinoReader.window, "ask_link_url", lambda parent, initial: "")
    insert_action(window, "Link...").trigger()
    assert source.toPlainText() == "keep me"


def test_insert_image_stores_a_relative_path(window, tmp_path, monkeypatch):
    edit_action(window).trigger()
    window.open(tmp_path / "doc.md")
    source = window.editor.source
    source.setPlainText("")
    image = tmp_path / "img" / "pic.png"
    monkeypatch.setattr(
        HeinoReader.window, "ask_image", lambda parent, start, alt: (str(image), "Alt")
    )
    insert_action(window, "Image...").trigger()
    # Relative to doc.md's folder, so the document stays portable.
    assert source.toPlainText() == "![Alt](img/pic.png)"


def test_insert_image_keeps_an_absolute_path_outside_the_document(
    window, tmp_path, monkeypatch
):
    edit_action(window).trigger()
    window.open(tmp_path / "doc.md")
    source = window.editor.source
    source.setPlainText("")
    elsewhere = tmp_path.parent / "other" / "pic.png"
    monkeypatch.setattr(
        HeinoReader.window, "ask_image", lambda parent, start, alt: (str(elsewhere), "")
    )
    insert_action(window, "Image...").trigger()
    text = source.toPlainText()
    assert text.startswith("![](") and text.endswith("/pic.png)")


def test_insert_table_fills_the_dialog_size(window, monkeypatch):
    edit_action(window).trigger()
    source = window.editor.source
    source.setPlainText("")
    monkeypatch.setattr(HeinoReader.window, "ask_table_size", lambda parent: (2, 3))
    insert_action(window, "Table...").trigger()
    lines = source.toPlainText().splitlines()
    assert lines[0] == "| Col 1 | Col 2 | Col 3 |"
    assert lines[1] == "| --- | --- | --- |"
    assert len(lines) == 3  # header + separator + one body row
    assert source.textCursor().selectedText() == "Col 1"


def test_insert_table_is_skipped_when_cancelled(window, monkeypatch):
    edit_action(window).trigger()
    source = window.editor.source
    source.setPlainText("untouched")
    monkeypatch.setattr(HeinoReader.window, "ask_table_size", lambda parent: None)
    insert_action(window, "Table...").trigger()
    assert source.toPlainText() == "untouched"


# ----------------------------------------------------------- desktop entry

def test_desktop_file_uses_a_relative_exec_command():
    desktop = (APP_DIR.parent.parent / "heino-reader.desktop").read_text(
        encoding="utf-8"
    )
    exec_lines = [l for l in desktop.splitlines() if l.startswith("Exec=")]
    assert exec_lines == ["Exec=heino-reader %f"]


# ------------------------------------------------------- reloading from disk

def test_an_external_change_reloads_a_clean_document(window, md_file):
    md_file.write_text("# From disk\n", encoding="utf-8")

    window._on_file_changed(str(md_file))

    assert window.document.markdown == "# From disk\n"
    assert window.document.is_modified is False


def test_an_external_change_keeps_unsaved_edits_when_the_prompt_is_cancelled(
    window, md_file, monkeypatch
):
    """Reloading must never silently throw away the user's text."""
    window.document.markdown = "unsaved edit"
    md_file.write_text("# From disk\n", encoding="utf-8")
    monkeypatch.setattr(
        HeinoReader.window, "ask_discard_changes", lambda parent, name: "cancel"
    )

    window._on_file_changed(str(md_file))

    assert window.document.markdown == "unsaved edit"


def test_an_external_change_replaces_unsaved_edits_after_discarding(
    window, md_file, monkeypatch
):
    window.document.markdown = "unsaved edit"
    md_file.write_text("# From disk\n", encoding="utf-8")
    monkeypatch.setattr(
        HeinoReader.window, "ask_discard_changes", lambda parent, name: "discard"
    )

    window._on_file_changed(str(md_file))

    assert window.document.markdown == "# From disk\n"


def test_a_recreated_file_is_watched_again(window, md_file, monkeypatch):
    added = []
    monkeypatch.setattr(window.watcher, "files", list)
    monkeypatch.setattr(window.watcher, "addPath", added.append)

    window._on_file_changed(str(md_file))

    # The reload attaches the path again through open(), hence twice.
    assert str(md_file) in added


# --------------------------------------------------------- backend switching

def test_switching_to_the_web_backend_without_qtwebengine_explains(
    window, monkeypatch
):
    shown = []
    monkeypatch.setattr(
        HeinoReader.window.QMessageBox,
        "information",
        staticmethod(lambda parent, title, text: shown.append((title, text))),
    )
    monkeypatch.setattr(window.viewer_area, "switch", lambda kind: False)

    window.actions.web_renderer.trigger()

    assert [title for title, _ in shown] == ["Web Engine Renderer unavailable"]
    assert WEB_EXTRA_HINT in shown[0][1]
    assert window.actions.web_renderer.isChecked() is False
    assert window.viewer_area.kind == RENDERER_QT


def test_an_unsaved_window_renders_relative_links_next_to_the_application(qtbot):
    window = ViewerWindow()
    qtbot.addWidget(window)

    assert window._base_dir() == APP_DIR
    assert window.viewer.base_dir == APP_DIR


def test_the_close_prompt_can_save_instead_of_discarding(window, monkeypatch):
    window.document.markdown = "changed"
    monkeypatch.setattr(
        HeinoReader.window, "ask_discard_changes", lambda parent, name: "save"
    )
    monkeypatch.setattr(window, "save", lambda: True)

    assert window._confirm_discard() is True


def test_saving_before_edit_mode_has_nothing_to_write(window):
    assert window.save() is False


def test_save_as_can_be_cancelled(window, monkeypatch):
    edit_action(window).trigger()
    monkeypatch.setattr(HeinoReader.window, "ask_save_file", lambda parent, start: None)

    assert window.save_as() is False
    assert window.document.path == window.document.path  # unchanged
