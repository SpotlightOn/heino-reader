"""User-visible text and the shared toolbar style.

Long strings live here so the window code stays wiring. VERSION is also the
one place the About dialog reads; it mirrors ``pyproject.toml``.
"""

VERSION = "0.3.0"

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

ABOUT_TEXT = (
    f"<b>Heino Reader {VERSION}</b>"
    "<p>A fast document viewer for markdown files, built with PySide6.</p>"
    "<p>An homage to Heino: dark sunglasses on, no fuss, just the text.</p>"
    "<p>Optional: the Web Engine renderer (View menu) renders with QtWebEngine "
    "for full CSS fidelity. It is the better but slower renderer and needs the "
    "optional <code>web</code> extra: "
    '<code>pip install "heino-reader[web]"</code>.</p>'
    "<p>Toolbar icons: Material Symbols Outlined (Apache License 2.0).</p>"
    "<p>License: MIT. Copyright (c) 2026 SpotlightOn.</p>"
)

WEB_EXTRA_HINT = (
    "The Web Engine renderer displays markdown with QtWebEngine (Chromium), so "
    "tables, borders and backgrounds follow the CSS exactly. It is more "
    "faithful than the default Qt text renderer, but slower to start and a "
    "much bigger download.\n\n"
    "It needs the optional QtWebEngine module, which the web extra installs:\n\n"
    '    pip install "heino-reader[web]"\n\n'
    "(or run scripts/install.sh --web)"
)

PLACEHOLDER_MD = """\
<img src="icon.svg" alt="Heino Reader">

# Heino Reader

An homage to Heino, the German singer with the black sunglasses: dark glasses
on, no fuss, just the text.

Drop a markdown file here, or start Heino Reader with a file path:

    heino-reader notes.md

- **Open** with `Ctrl+O` or drag a file onto the window
- **Edit** with the pencil button: source left, live view right;
  `Ctrl+S` saves, `Ctrl+Shift+S` saves as
- **Zoom** with `Ctrl++` / `Ctrl+-`, reset with `Ctrl+0`
- **Remote images**: View -> Load Remote Images (off sends no requests)
- **Full CSS fidelity**: View -> Web Engine Renderer. This is the better but
  slower renderer: it draws with QtWebEngine instead of Qt's text engine and
  needs the optional QtWebEngine module (`pip install "heino-reader[web]"`)
"""
