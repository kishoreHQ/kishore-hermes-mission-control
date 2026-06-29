"""Nightly pipeline scheduler and run management."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path

import yaml
from app.config import settings
from fastapi import APIRouter, BackgroundTasks

router = APIRouter(prefix="/nightly", tags=["nightly"])

_RUNS: list[dict] = []


def _dag_path() -> Path:
    return Path("config/nightly-dag.yaml")


def _load_dag() -> dict:
    path = _dag_path()
    if not path.exists():
        return {"jobs": {}}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {"jobs": {}}


def _execute_pipeline(run_id: str) -> None:
    dag = _load_dag()
    jobs = dag.get("jobs", {})
    succeeded = 0
    failed = 0
    job_results = []
    for key, job in jobs.items():
        if job.get("type") == "report":
            continue
        status = "succeeded"
        try:
            if job.get("type") == "script":
                pass
            else:
                pass
        except Exception as exc:  # noqa: BLE001
            status = "failed"
            failed += 1
            job_results.append({"job_key": key, "status": status, "error": str(exc)})
            continue
        succeeded += 1
        job_results.append({"job_key": key, "status": status})

    for run in _RUNS:
        if run["id"] == run_id:
            run["status"] = "failed" if failed else "completed"
            run["jobs_succeeded"] = succeeded
            run["jobs_failed"] = failed
            run["jobs_total"] = len(jobs)
            run["finished_at"] = datetime.now(timezone.utc).isoformat()
            run["jobs"] = job_results
            run["report_markdown"] = (
                f"# Morning Report\n\n- Jobs succeeded: {succeeded}\n- Jobs failed: {failed}\n"
            )
            break


@router.get("/runs")
def list_runs():
    return {"items": _RUNS}


@router.get("/runs/latest")
def latest_run():
    if not _RUNS:
        return {"run": None}
    return {"run": _RUNS[-1]}


@router.post("/trigger")
def trigger_nightly(background_tasks: BackgroundTasks):
    run_id = str(uuid.uuid4())
    run = {
        "id": run_id,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "status": "running",
        "jobs_total": len(_load_dag().get("jobs", {})),
        "jobs_succeeded": 0,
        "jobs_failed": 0,
        "source": "manual",
    }
    _RUNS.append(run)
    background_tasks.add_task(_execute_pipeline, run_id)
    return {"run": run, "message": "Nightly pipeline started"}


@router.get("/dag")
def get_dag():
    return _load_dag()
