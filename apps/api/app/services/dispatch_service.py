"""Thin wrapper — reads from legacy JSONL; future: Postgres + dispatch_engine."""

from app.services import legacy_adapter


def list_all(limit: int = 100) -> list[dict]:
    return legacy_adapter.list_dispatches(limit)


def list_active() -> list[dict]:
    return legacy_adapter.list_active_dispatches()


def get(dispatch_id: str) -> dict | None:
    return legacy_adapter.get_dispatch(dispatch_id)
