"""Aggregates Today briefing from legacy + Hermes + status."""

from __future__ import annotations

from datetime import datetime, timezone

from app.services import hermes_adapter, legacy_adapter, metrics_store, status_service


def build_today() -> dict:
    status = status_service.build_status(include_heavy=True)
    summary = status.get("summary", {})
    dispatches = legacy_adapter.list_active_dispatches()
    tasks = legacy_adapter.list_tasks()
    services = status.get("services") or legacy_adapter.list_services()
    cron_jobs = hermes_adapter.list_cron_summaries()
    stats = hermes_adapter.session_stats()
    metrics_store.ingest_session_cost(stats)

    attention = _build_attention(dispatches, services, cron_jobs, status)
    status_hero = _status_hero(summary, attention, dispatches, services, cron_jobs)
    bento = _bento(summary, dispatches, tasks, stats)
    running_now = _running_now(dispatches, cron_jobs, legacy_adapter.list_active_runs())
    agenda = [
        {"id": t.get("id", str(i)), "title": t.get("title", "Task"), "done": t.get("lane") == "archived"}
        for i, t in enumerate(tasks)
        if t.get("lane") in ("in_progress", "scheduled", "needs_review")
    ][:10]

    nightly = _nightly_report()

    return {
        "greeting": _greeting(),
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "attention_count": len([a for a in attention if a.get("severity") in ("error", "warning")]),
        "status_hero": status_hero,
        "bento": bento,
        "running_now": running_now,
        "metrics": {
            "nightly": nightly.get("metrics", {"status": "pending", "succeeded": 0, "total": 0}),
            "agents_active": len(dispatches),
            "content_queued": len(_content_queue_count()),
            "stocks": {"symbol": "NIFTY", "change": "—"},
        },
        "attention": attention,
        "agenda": agenda,
        "nightly_report": nightly.get("report", {"summary": "No nightly report yet.", "artifacts": []}),
        "recommendations": _recommendations(attention, dispatches, summary),
        "quick_actions": ["dispatch", "run_cron", "capture", "summary"],
    }


def _greeting() -> str:
    hour = datetime.now(timezone.utc).hour
    if hour < 12:
        return "Good morning, Kishore."
    if hour < 17:
        return "Good afternoon, Kishore."
    return "Good evening, Kishore."


def _status_hero(summary: dict, attention: list, dispatches: list, services: list, cron_jobs: list) -> dict:
    errors = sum(1 for a in attention if a.get("severity") == "error")
    warnings = sum(1 for a in attention if a.get("severity") == "warning")
    if errors:
        level = "action_required"
        headline = f"{errors} critical · {warnings} warnings"
    elif warnings:
        level = "attention"
        headline = f"{warnings} items need review"
    else:
        level = "operational"
        headline = "All systems operational"
    return {
        "level": level,
        "summary": headline,
        "active_runs": len(dispatches) + len(legacy_adapter.list_active_runs()),
        "services_monitored": len(services) or len(legacy_adapter.list_services()),
        "enabled_crons": summary.get("enabled_crons", len([j for j in cron_jobs if j.get("enabled")])),
    }


def _bento(summary: dict, dispatches: list, tasks: list, stats: dict) -> dict:
    failed = [
        d
        for d in legacy_adapter.list_dispatches(100)
        if d.get("status") in ("failed", "retry_exhausted")
    ]
    review = [t for t in tasks if t.get("lane") == "needs_review"]
    blocked = [t for t in tasks if t.get("lane") == "blocked"]
    workflows = legacy_adapter.list_workflows()
    wf_count = len(workflows) if isinstance(workflows, dict) else len(workflows or [])
    return {
        "running": len(dispatches) + len(legacy_adapter.list_active_runs()),
        "failed": len(failed),
        "review": len(review) + int(summary.get("review_items", 0)),
        "blocked": len(blocked),
        "workflows": wf_count,
        "cost_usd": round(float(summary.get("cost") or stats.get("cost", 0)), 2),
        "tokens": int(summary.get("tokens") or stats.get("tokens", 0)),
    }


def _running_now(dispatches: list, cron_jobs: list, runs: list) -> list[dict]:
    items: list[dict] = []
    for d in dispatches[:6]:
        items.append(
            {
                "id": d.get("dispatch_id"),
                "name": d.get("profile") or "Dispatch",
                "type": "dispatch",
                "progress": d.get("progress") or 0,
                "status": d.get("status", "running"),
            }
        )
    for r in runs[:4]:
        items.append(
            {
                "id": r.get("run_id"),
                "name": r.get("title") or r.get("profile") or "Run",
                "type": "run",
                "progress": r.get("progress") or 0,
                "status": r.get("status", "running"),
            }
        )
    for j in [c for c in cron_jobs if c.get("last_status") == "running"][:3]:
        items.append(
            {
                "id": j.get("id"),
                "name": j.get("name"),
                "type": "cron",
                "progress": 0,
                "status": "running",
            }
        )
    return items


def _build_attention(active_dispatches: list, services: list, cron_jobs: list, status: dict) -> list[dict]:
    items: list[dict] = []
    failed = [d for d in legacy_adapter.list_dispatches(50) if d.get("status") in ("failed", "retry_exhausted")]
    for d in failed[:3]:
        items.append(
            {
                "id": d.get("dispatch_id"),
                "severity": "error",
                "title": f"Dispatch failed: {d.get('profile', 'unknown')}",
                "actions": ["logs", "retry"],
                "action_targets": {"dispatch_id": d.get("dispatch_id")},
            }
        )
    for j in [c for c in cron_jobs if c.get("needs_review")][:3]:
        items.append(
            {
                "id": j.get("id"),
                "severity": "warning",
                "title": f"Cron needs review: {j.get('name')}",
                "actions": ["logs", "fix"],
                "action_targets": {"job_id": j.get("id")},
            }
        )
    for svc in services:
        st = svc.get("status") or svc.get("health")
        if st in ("degraded", "offline"):
            items.append(
                {
                    "id": svc.get("id"),
                    "severity": "warning" if st == "degraded" else "error",
                    "title": f"Service {st}: {svc.get('name')}",
                    "actions": ["logs", "restart"],
                    "action_targets": {"service": svc.get("systemd_service")},
                }
            )
    for item in status.get("review_queue", [])[:2]:
        items.append(
            {
                "id": item.get("id"),
                "severity": "warning",
                "title": f"Review: {item.get('name', item.get('id'))}",
                "actions": ["open"],
                "action_targets": {"job_id": item.get("id")},
            }
        )
    if not items:
        items.append({"id": "all-clear", "severity": "info", "title": "All systems operational", "actions": []})
    return items[:12]


def _recommendations(attention: list, active: list, summary: dict) -> list[dict]:
    recs: list[dict] = []
    if any(a.get("severity") == "error" for a in attention):
        recs.append({"id": "r1", "text": "Review failed dispatches and retry or reroute profile"})
    if summary.get("review_items", 0) > 0:
        recs.append({"id": "r2", "text": f"{summary['review_items']} cron jobs need review — check Agents → Cron"})
    if len(active) == 0:
        recs.append({"id": "r3", "text": "No active agents — consider running morning intelligence cron"})
    return recs


def _content_queue_count() -> list:
    try:
        from app.services import contentforge_adapter

        return contentforge_adapter.queue()
    except Exception:
        return []


def _nightly_report() -> dict:
    runs = legacy_adapter.read_jsonl("nightly_runs.jsonl") if hasattr(legacy_adapter, "read_jsonl") else []
    path_runs = legacy_adapter.data_dir() / "nightly_runs.jsonl"
    if path_runs.exists():
        runs = legacy_adapter.read_jsonl("nightly_runs.jsonl")
    if not runs:
        return {
            "metrics": {"status": "pending", "succeeded": 0, "total": 0},
            "report": {"summary": "Nightly pipeline not yet run.", "artifacts": []},
        }
    latest = runs[-1]
    return {
        "metrics": {
            "status": latest.get("status", "unknown"),
            "succeeded": latest.get("jobs_succeeded", 0),
            "total": latest.get("jobs_total", 0),
        },
        "report": {
            "summary": latest.get("report_markdown", "Nightly run completed.")[:500],
            "artifacts": latest.get("artifacts", []),
        },
    }
