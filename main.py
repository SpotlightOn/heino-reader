"""Entry point for PyInstaller builds and ``python main.py``."""

from __future__ import annotations

import sys
from pathlib import Path

try:
    from HeinoReader import main
except ModuleNotFoundError as error:
    if error.name != "HeinoReader":
        raise
    # Running straight from a checkout: the package lives in src/.
    sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
    from HeinoReader import main

if __name__ == "__main__":
    raise SystemExit(main())
