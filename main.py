"""Entry point for PyInstaller builds and ``python main.py``."""

from __future__ import annotations

import sys
from pathlib import Path

# Running straight from a checkout: prefer src/ over any older installed copy.
_SRC = Path(__file__).resolve().parent / "src"
if _SRC.is_dir():
    sys.path.insert(0, str(_SRC))

from HeinoReader.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
