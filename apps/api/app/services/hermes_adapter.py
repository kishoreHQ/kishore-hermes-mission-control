"""Read Hermes runtime from HERMES_HOME (~/.hermes)."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from app.config import settings


def hermes_home() -> Path:
    if settings.hermes_home:
        return Path(settings.hermes_home).expanduser()
    return Path.home() / ".hermes"


def _read_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def load_cron_jobs() -> list[dict]:
    payload = _read_json(hermes_home() / "cron" / "jobs.json", {"jobs": []})
    return payload.get("jobs", []) if isinstance(payload, dict) else []


def summarize_job(job: dict) -> dict:
    repeat = job.get("repeat") or {}
    last_error = str(job.get("last_error") or job.get("last_delivery_error") or "")[:180]
    needs_review = bool(
        job.get("last_error")
        or job.get("last_delivery_error")
        or job.get("last_status") == "error"
        or job.get("state") == "error"
    )
    return {
        "id": job.get("id"),
        "name": job.get("name") or job.get("id") or "Unnamed job",
        "enabled": bool(job.get("enabled", True)),
        "state": job.get("state") or "unknown",
        "schedule": job.get("schedule_display")
        or (job.get("schedule") or {}).get("display")
        or "manual",
        "next_run_at": job.get("next_run_at"),
        "last_run_at": job.get("last_run_at"),
        "last_status": job.get("last_status") or "unknown",
        "last_error": last_error,
        "needs_review": needs_review,
        "mode": "script" if job.get("no_agent") else "agent",
    }


def list_cron_summaries() -> list[dict]:
    return [summarize_job(j) for j in load_cron_jobs()]


def list_profiles() -> list[dict]:
    profiles_dir = hermes_home() / "profiles"
    if not profiles_dir.exists():
        return []
    out: list[dict] = []
    for path in sorted(profiles_dir.iterdir()):
        if not path.is_dir():
            continue
        out.append({"id": path.name, "name": path.name, "path": str(path)})
    return out


def list_skills() -> list[dict]:
    skills_dir = hermes_home() / "skills"
    if not skills_dir.exists():
        return []
    return [{"name": p.name, "path": str(p)} for p in skills_dir.iterdir() if p.is_dir() or p.suffix == ".md"]


def list_plugins() -> list[dict]:
    plugins_dir = hermes_home() / "plugins"
    if not plugins_dir.exists():
        return []
    return [{"name": p.name, "path": str(p)} for p in plugins_dir.iterdir()]


def session_stats() -> dict:
    stats = {"sessions": 0, "messages": 0, "tokens": 0, "cost": 0.0, "models": []}
    state_db = hermes_home() / "state.db"
    if not state_db.exists():
        return stats
    try:
        con = sqlite3.connect(f"file:{state_db}?mode=ro", uri=True, timeout=1)
        cur = con.cursor()
        for table, key in (("sessions", "sessions"), ("messages", "messages")):
            try:
                stats[key] = int(cur.execute(f"select count(*) from {table}").fetchone()[0])
            except Exception:
                pass
        try:
            row = cur.execute(
                "select coalesce(sum(input_tokens),0), coalesce(sum(output_tokens),0), "
                "coalesce(sum(cache_read_tokens),0), coalesce(sum(cache_write_tokens),0), "
                "coalesce(sum(reasoning_tokens),0) from sessions"
            ).fetchone()
            stats["tokens"] = int(sum(row or []))
        except Exception:
            pass
        try:
            stats["cost"] = float(
                cur.execute(
                    "select coalesce(sum(coalesce(actual_cost_usd, estimated_cost_usd, 0)),0) from sessions"
                ).fetchone()[0]
                or 0
            )
        except Exception:
            pass
        con.close()
    except Exception:
        pass
    return stats


def latest_cron_output_path(job_id: str) -> Path | None:
    root = hermes_home() / "cron" / "output" / job_id
    if not root.exists():
        return None
    files = [p for p in root.rglob("*") if p.is_file()]
    if not files:
        return None
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return files[0]
