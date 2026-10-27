# Changelog

## [Unreleased]

### Added

- Source editor: Enter continues quote and list markers, empty items end them.
- Toolbar lists, quote and heading start on an empty line.
- Editor: Undo, Redo, toolbar buttons.

### Changed

- Preview: debounced rendering, CSS line heights, lazy highlighting.

### Fixed

- Qt preview on HiDPI: font size and line spacing now follow `preview.css`.
- Editor: unsaved changes, close prompt, title marker.

## [0.2.1] - 2026-10-27

### Changed

- Renamed to heino-reader: package `HeinoReader`, command `heino-reader`,
  config `~/.config/heino-reader`.
- Install size 675 MB → 258 MB via `PySide6-Essentials`.
- QtWebEngine moved to the optional `web` extra.

### Added

- UI hint for the optional Web Engine preview.
- MIT license.

### Fixed

- Startup without `pyside6-addons` falls back to the Qt renderer.
