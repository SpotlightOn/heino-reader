"""Allow running the viewer as ``python -m HeinoReader``."""

from HeinoReader.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
