# Changelog

## [Unreleased]

### Added

- Viewer: `View → Wrap Code` (default on) keeps long code lines inside the
  text column.
- Viewer: the zoom level is remembered across restarts.

### Changed

- PySide6 6.12 on Python 3.12 and newer; 3.10/3.11 stay on 6.11.3 until 6.12.1
  is released (PYSIDE-3474).

### Fixed

- Viewer: tables that fill the column no longer stick out by their cell borders
  and add a horizontal scrollbar.
- Viewer: the zoom applies to both renderers, so switching back no longer
  restores an older value.
- Editor: line numbers come back on startup when they were enabled.
- Editor: `**bold**` is bold instead of italic.

## [0.2.2] - 2026-10-27

### Added

- Source editor: Enter continues quote and list markers, empty items end them.
- Toolbar lists, quote and heading start on an empty line.
- Editor: Undo, Redo, toolbar buttons.

### Changed

- Viewer: debounced rendering, CSS line heights, lazy highlighting.
- Editor: text size follows the viewer and the zoom.

### Fixed

- Qt viewer on HiDPI: font size and line spacing now follow `document.css`.
- Editor: unsaved changes, close prompt, title marker.

## [0.2.1] - 2026-10-27

### Changed

- Renamed to heino-reader: package `HeinoReader`, command `heino-reader`,
  config `~/.config/heino-reader`.
- Install size 675 MB → 258 MB via `PySide6-Essentials`.
- QtWebEngine moved to the optional `web` extra.

### Added

- UI hint for the optional Web Engine renderer.
- MIT license.

### Fixed

- Startup without `pyside6-addons` falls back to the Qt renderer.
