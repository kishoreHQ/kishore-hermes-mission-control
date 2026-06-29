"""Bridge to legacy dispatch_engine — configures paths from V2 settings."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from app.config import settings

_engine = None
_import_error: str | None = None


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _get_engine():
    global _engine, _import_error
    if _engine is not None:
        return _engine
    if _import_error:
        raise RuntimeError(_import_error)
    try:
        root = _repo_root()
        if str(root) not in sys.path:
            sys.path.insert(0, str(root))
        home = settings.hermes_home or os.environ.get("HERMES_HOME", str(Path.home() / ".hermes"))
        os.environ.setdefault("HERMES_HOME", home)
        import dispatch_engine as de

        data_dir = Path(settings.hermes_data_dir)
        if not data_dir.is_absolute():
            data_dir = root / data_dir
        de.DATA_DIR = data_dir
        de.DISPATCH_DATA = data_dir / "dispatch_queue.jsonl"
        de.WF_EVENTS_DATA = data_dir / "workflow_events.jsonl"
        de.HERMES_HOME = Path(home)
        de.PROFILES_DIR = de.HERMES_HOME / "profiles"
        _engine = de
        return de
    except Exception as exc:  # noqa: BLE001
        _import_error = str(exc)
        raise RuntimeError(_import_error) from exc


def available() -> bool:
    try:
        _get_engine()
        return True
    except RuntimeError:
        return False


def enqueue(payload: dict) -> dict:
    return _get_engine().enqueue_dispatch(payload)


def cancel(dispatch_id: str) -> dict:
    return _get_engine().dispatch_cancel(dispatch_id)


def start(dispatch_id: str) -> dict:
    return _get_engine().dispatch_start(dispatch_id)


def retry(dispatch_id: str) -> dict:
    return _get_engine().dispatch_retry(dispatch_id)


def live(dispatch_id: str) -> dict:
    return _get_engine().get_dispatch_live(dispatch_id)
