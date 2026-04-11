"""Lightweight import smoke test (no DB required)."""

from __future__ import annotations


def test_app_importable():
    import sys
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / "backend"))
    from app.main import app  # noqa: F401

    assert app.title
