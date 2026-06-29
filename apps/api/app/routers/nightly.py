"""Nightly pipeline scheduler and run management."""

from __future__ import annotations

import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path

import yaml
from app.services import event_bus, legacy_adapter
from fastapi import APIRouter, BackgroundTasks

router = APIRouter(prefix="/nightly", tags=["nightly"])

_RUNS: list[dict] = []


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _dag_path() -> Path:
    for base in (_repo_root(), Path.cwd()):
        p = base / "config" / "nightly-dag.yaml"
        if p.exists():
            return p
    return _repo_root() / "config" / "nightly-dag.yaml"


def _load_dag() -> dict:
    path = _dag_path()
    if not path.exists():
        return {"jobs": {}}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {"jobs": {}}


def _persist_run(run: dict) -> None:
    legacy_adapter.append_jsonl("nightly_runs.jsonl", run)


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
        err = None
        try:
            if job.get("type") == "script":
                cmd = job.get("command", "")
                if cmd:
                    subprocess.run(cmd, shell=True, cwd=str(_repo_root()), timeout=job.get("timeout", 300), check=False)
            elif job.get("profile") and job.get("prompt"):
                subprocess.run(
                    ["hermes", "-p", job["profile"].lower(), "chat", "-q", job["prompt"], "--quiet", "--max-turns=1"],
                    timeout=min(int(job.get("timeout", 600)), 600),
                    capture_output=True,
                    text=True,
                )
        except Exception as exc:  # noqa: BLE001
            status = "failed"
            err = str(exc)
            failed += 1
            job_results.append({"job_key": key, "status": status, "error": err})
            continue
        succeeded += 1
        job_results.append({"job_key": key, "status": status})

    report_md = f"# Morning Report\n\n- Jobs succeeded: {succeeded}\n- Jobs failed: {failed}\n"
    for run in _RUNS:
        if run["id"] == run_id:
            run["status"] = "failed" if failed else "completed"
            run["jobs_succeeded"] = succeeded
            run["jobs_failed"] = failed
            run["jobs_total"] = len([k for k, j in jobs.items() if j.get("type") != "report"])
            run["finished_at"] = datetime.now(timezone.utc).isoformat()
            run["jobs"] = job_results
            run["report_markdown"] = report_md
            run["artifacts"] = [j.get("artifact") for j in jobs.values() if j.get("artifact")]
            _persist_run(run)
            break
    event_bus.publish("nightly.completed", {"run_id": run_id})


@router.get("/runs")
def list_runs():
    file_runs = legacy_adapter.read_jsonl("nightly_runs.jsonl")
    return {"items": file_runs or _RUNS}


@router.get("/runs/latest")
def latest_run():
    file_runs = legacy_adapter.read_jsonl("nightly_runs.jsonl")
    runs = file_runs or _RUNS
    if not runs:
        return {"run": None}
    return {"run": runs[-1]}


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
