"""ContentForge integration (PRD §9.2)."""

from __future__ import annotations

import json
from pathlib import Path

CONTENTFORGE_ROOT = Path("/tmp/contentforge")


def _read(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def queue() -> list[dict]:
    data = _read(CONTENTFORGE_ROOT / "queue.json", [])
    return data if isinstance(data, list) else data.get("items", []) if isinstance(data, dict) else []


def published() -> list[dict]:
    data = _read(CONTENTFORGE_ROOT / "posted.json", [])
    return data if isinstance(data, list) else []


def metrics() -> dict:
    return _read(CONTENTFORGE_ROOT / "metrics.json", {})


def ideas() -> list[dict]:
    data = _read(CONTENTFORGE_ROOT / "ideas.json", [])
    return data if isinstance(data, list) else []
