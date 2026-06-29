"""Read legacy JSON/JSONL files during migration."""

from __future__ import annotations

import json
from pathlib import Path

from app.config import settings


def data_dir() -> Path:
    return Path(settings.hermes_data_dir)


def read_jsonl(filename: str) -> list[dict]:
    path = data_dir() / filename
    if not path.exists():
        return []
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def read_json(filename: str, default=None):
    path = data_dir() / filename
    if not path.exists():
        return default if default is not None else {}
    return json.loads(path.read_text(encoding="utf-8"))


def list_dispatches(limit: int = 100) -> list[dict]:
    rows = read_jsonl("dispatch_queue.jsonl")
    return rows[-limit:]


def list_active_dispatches() -> list[dict]:
    return [d for d in list_dispatches(500) if d.get("status") in ("queued", "running", "starting")]


def get_dispatch(dispatch_id: str) -> dict | None:
    for row in reversed(list_dispatches(1000)):
        if row.get("dispatch_id") == dispatch_id:
            return row
    return None


def list_workflows() -> dict:
    return read_json("workflows_multi.json", default={})


def list_tasks() -> list[dict]:
    data = read_json("tasks.json", default=[])
    return data if isinstance(data, list) else []


def list_services() -> list[dict]:
    return read_json("services.json", default=[])


def list_profiles_from_workflows() -> list[dict]:
    catalog = read_json("workflows.json", default={})
    agents = catalog.get("agents", [])
    return agents if isinstance(agents, list) else []
