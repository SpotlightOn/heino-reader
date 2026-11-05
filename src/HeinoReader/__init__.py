"""Heino Reader - a fast document viewer for markdown files.

Heino Reader displays markdown files read-only as HTML. By default the
lightweight Qt text renderer paints the document; the heavier QtWebEngine
backend is only imported and created when it is actually used. It can be
started with a file path, so it can be bound to the .md extension in file
managers such as Dolphin.

Usage:
    heino-reader [FILE]
    python -m HeinoReader [FILE]

The package is a set of small modules rather than one API surface:

    window.py     wires document, editor, preview and chrome together
    document.py   the open file: its text, path and modified state
    editpane.py   the markdown editor with gutter and typing delay
    preview.py    the two preview backends and the one on screen
    chrome.py     menu bar and toolbars, built from the actions
    actions.py    every action with icon, shortcut and handler
    render.py     markdown and CSS to HTML, shared by both backends
"""

from __future__ import annotations
