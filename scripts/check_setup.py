#!/usr/bin/env python3
"""Verify fear_mecanumbot dependencies before running demos."""

from __future__ import annotations

import importlib
import sys


def main() -> int:
    missing: list[str] = []
    for name in ("numpy", "pytest"):
        try:
            importlib.import_module(name)
        except ImportError:
            missing.append(name)
    if missing:
        print("Missing packages:", ", ".join(missing))
        print("Run: pip install -r requirements.txt")
        return 1
    print("OK: numpy and pytest installed")
    print("Next: python -m pytest -q")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
