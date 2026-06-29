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


def write_json(filename: str, payload) -> None:
    path = data_dir() / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")


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


def list_runs(limit: int = 200) -> list[dict]:
    return read_jsonl("runs.jsonl")[-limit:]


def list_active_runs() -> list[dict]:
    return [r for r in list_runs(500) if r.get("status") in ("queued", "running", "waiting_for_approval")]


def list_workflow_events(limit: int = 200) -> list[dict]:
    return read_jsonl("workflow_events.jsonl")[-limit:]


def list_routing_history(limit: int = 100) -> list[dict]:
    return read_jsonl("routing_history.jsonl")[-limit:]


def list_nightly_builds() -> list[dict]:
    data = read_json("nightly_builds.json", default=[])
    return data if isinstance(data, list) else []


def append_jsonl(filename: str, record: dict) -> None:
    path = data_dir() / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, default=str) + "\n")


def dispatch_file_path() -> Path:
    return data_dir() / "dispatch_queue.jsonl"
