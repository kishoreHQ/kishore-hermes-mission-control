#!/usr/bin/env python3
"""Import legacy JSONL/JSON into Postgres."""

from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.session import SessionLocal, engine
from app.models.base import Base
from app.models.tables import Dispatch, Task
from app.services import legacy_adapter


def import_dispatches(session) -> int:
    count = 0
    for row in legacy_adapter.list_dispatches(10000):
        legacy_id = row.get("dispatch_id")
        if not legacy_id:
            continue
        existing = session.query(Dispatch).filter(Dispatch.legacy_id == legacy_id).first()
        if existing:
            continue
        session.add(
            Dispatch(
                legacy_id=legacy_id,
                workflow_id=row.get("workflow_id"),
                subtask_id=row.get("subtask_id"),
                profile=row.get("profile", "Default"),
                prompt=row.get("prompt", ""),
                status=row.get("status", "unknown"),
                process_status=row.get("process_status"),
                pid=row.get("pid"),
                exit_code=row.get("exit_code"),
                timeout_seconds=row.get("timeout_seconds") or 3600,
                retry_count=row.get("retry_count") or 0,
                failure_reason=row.get("failure_reason"),
                stdout_tail=row.get("stdout_tail"),
                stderr_tail=row.get("stderr_tail"),
            )
        )
        count += 1
    return count


def import_tasks(session) -> int:
    count = 0
    for row in legacy_adapter.list_tasks():
        legacy_id = str(row.get("id", uuid.uuid4()))
        existing = session.query(Task).filter(Task.legacy_id == legacy_id).first()
        if existing:
            continue
        session.add(
            Task(
                legacy_id=legacy_id,
                title=row.get("title", "Untitled"),
                lane=row.get("lane", "scheduled"),
                assignee_profile=row.get("assignee"),
                priority=row.get("priority"),
                metadata_=row.get("metadata") or {},
            )
        )
        count += 1
    return count


def main() -> None:
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        d = import_dispatches(session)
        t = import_tasks(session)
        session.commit()
        print(f"Imported {d} dispatches, {t} tasks")
    finally:
        session.close()


if __name__ == "__main__":
    main()
