"""Renderers: the two backends and the one currently shown.

The Qt text renderer is the default and is imported eagerly; the WebEngine
backend is created lazily, so a Qt-rendered start never loads Chromium.
"""

from __future__ import annotations

import sys
from importlib.util import find_spec
from pathlib import Path

from PySide6.QtWidgets import QSplitter, QWidget

from .qt import QtMarkdownView

RENDERER_WEB = "web"
RENDERER_QT = "qt"
DEFAULT_RENDERER = RENDERER_QT
RENDERERS = (RENDERER_WEB, RENDERER_QT)


def web_engine_available() -> bool:
    """True when pyside6-addons (QtWebEngine) is installed.

    Uses a spec lookup instead of an import, so checking never loads the
    Chromium libraries.
    """
    return find_spec("PySide6.QtWebEngineWidgets") is not None


def create_markdown_view(
    kind: str, parent: QWidget | None = None
) -> QWidget:
    """Return a viewer widget for ``kind``.

    The WebEngine backend is imported here rather than at module level, so a
    Qt-rendered view never loads Chromium.
    """
    if kind == RENDERER_QT:
        return QtMarkdownView(parent)
    from .web import WebMarkdownView

    return WebMarkdownView(parent)


def chosen_renderer(requested: str | None, remembered: str | None) -> str:
    """The backend to start with, falling back to Qt when anything is off."""
    chosen = requested or remembered or DEFAULT_RENDERER
    if chosen not in RENDERERS:
        return DEFAULT_RENDERER
    if chosen == RENDERER_WEB and not web_engine_available():
        print(
            "heino-reader: QtWebEngine is not installed, "
            "falling back to the Qt renderer",
            file=sys.stderr,
        )
        return DEFAULT_RENDERER
    return chosen


class ViewerArea:
    """The viewer widgets and which backend the splitter shows.

    Both backends are kept once created, so switching back is instant. The
    zoom and the base directory are remembered here and reapplied to a view
    that was parked while another one was visible.
    """

    def __init__(
        self,
        splitter: QSplitter,
        parent: QWidget,
        kind: str = DEFAULT_RENDERER,
        base_dir: Path | None = None,
    ) -> None:
        self._splitter = splitter
        self._parent = parent
        self._kind = kind if kind in RENDERERS else DEFAULT_RENDERER
        self._base_dir = base_dir
        self._zoom = 1.0
        self._views: dict[str, QWidget] = {}
        self.view = self._create(self._kind)
        self._views[self._kind] = self.view
        splitter.addWidget(self.view)

    @property
    def kind(self) -> str:
        """Renderer of the view in the splitter."""
        return self._kind

    def _create(self, kind: str) -> QWidget:
        view = create_markdown_view(kind, self._parent)
        view.set_base_dir(self._base_dir)
        # Drops belong to the window, not to the viewer inside it.
        view.setAcceptDrops(False)
        return view

    def set_markdown(self, text: str) -> None:
        """Show ``text`` in the current backend."""
        self.view.set_markdown(text)

    def set_zoom(self, scale: float) -> None:
        """Apply the zoom to the current view and remember it for the other."""
        self._zoom = scale
        self.view.set_zoom(scale)

    def set_base_dir(self, base_dir: Path | None) -> None:
        """Resolve relative links and images against ``base_dir``."""
        self._base_dir = base_dir
        self.view.set_base_dir(base_dir)

    def apply_options(self, *, remote_images: bool, wrap_code: bool) -> None:
        """Hand the View-menu toggles to the current backend."""
        self.view.set_remote_images_enabled(remote_images)
        self.view.set_code_wrap(wrap_code)

    def switch(self, kind: str) -> bool:
        """Show the other backend; False when it cannot be created."""
        if kind not in RENDERERS or kind == self._kind:
            return True
        view = self._views.get(kind)
        if view is None:
            try:
                view = self._create(kind)
            except ImportError:
                return False
            self._views[kind] = view
        view.set_zoom(self._zoom)
        old = self.view
        visible = old.isVisible()
        sizes = self._splitter.sizes()
        self._splitter.replaceWidget(self._splitter.indexOf(old), view)
        if sizes:
            self._splitter.setSizes(sizes)
        self.view = view
        self._kind = kind
        view.setVisible(visible)
        return True
