"""Persistent user settings, stored in the XDG config directory.

The file lives at ``$XDG_CONFIG_HOME/heinoreader/settings.ini`` (usually
``~/.config/heinoreader/settings.ini``). ``HEINOREADER_CONFIG_DIR``
overrides the directory, which the test suite uses to stay isolated.
"""

from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import QSettings, QStandardPaths

RENDERER_KEY = "view/renderer"
LINE_NUMBERS_KEY = "view/line_numbers"
REMOTE_IMAGES_KEY = "view/remote_images"


def config_dir() -> Path:
    """Directory that holds heinoreader's settings file."""
    override = os.environ.get("HEINOREADER_CONFIG_DIR")
    if override:
        return Path(override)
    base = QStandardPaths.writableLocation(
        QStandardPaths.StandardLocation.GenericConfigLocation
    )
    return Path(base or Path.home() / ".config") / "heinoreader"


class Settings:
    """Typed access to the INI settings file."""

    def __init__(self, path: Path | None = None) -> None:
        if path is None:
            path = config_dir() / "settings.ini"
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self._settings = QSettings(str(path), QSettings.Format.IniFormat)

    def get_string(self, key: str, default: str = "") -> str:
        return str(self._settings.value(key, default))

    def set_string(self, key: str, value: str) -> None:
        self._settings.setValue(key, value)
        self._settings.sync()

    def get_bool(self, key: str, default: bool = False) -> bool:
        value = self._settings.value(key, "true" if default else "false")
        return str(value).lower() in ("1", "true", "yes", "on")

    def set_bool(self, key: str, value: bool) -> None:
        self._settings.setValue(key, "true" if value else "false")
        self._settings.sync()
