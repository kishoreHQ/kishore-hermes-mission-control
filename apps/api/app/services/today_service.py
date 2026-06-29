"""Aggregates Today briefing from legacy + computed data."""

from datetime import datetime, timezone

from app.services import legacy_adapter


def build_today() -> dict:
    dispatches = legacy_adapter.list_active_dispatches()
    tasks = legacy_adapter.list_tasks()
    services = legacy_adapter.list_services()
    attention = _build_attention(dispatches, services)
    agenda = [
        {"id": t.get("id", str(i)), "title": t.get("title", "Task"), "done": t.get("lane") == "archived"}
        for i, t in enumerate(tasks)
        if t.get("lane") in ("in_progress", "scheduled", "needs_review")
    ][:10]

    return {
        "greeting": "Good morning, Kishore.",
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "attention_count": len(attention),
        "metrics": {
            "nightly": {"status": "pending", "succeeded": 0, "total": 0},
            "agents_active": len(dispatches),
            "content_queued": 0,
            "stocks": {"symbol": "NIFTY", "change": "—"},
        },
        "attention": attention,
        "agenda": agenda,
        "nightly_report": {
            "summary": "Nightly pipeline not yet run. Configure scheduler in Agents → Nightly.",
            "artifacts": [],
        },
        "recommendations": _recommendations(attention, dispatches),
        "quick_actions": ["dispatch", "run_cron", "capture", "summary"],
    }


def _build_attention(active_dispatches: list, services: list) -> list[dict]:
    items: list[dict] = []
    failed = [d for d in legacy_adapter.list_dispatches(50) if d.get("status") in ("failed", "retry_exhausted")]
    for d in failed[:3]:
        items.append(
            {
                "id": d.get("dispatch_id"),
                "severity": "error",
                "title": f"Dispatch failed: {d.get('profile', 'unknown')}",
                "actions": ["logs", "retry"],
            }
        )
    for svc in services:
        if svc.get("health") == "degraded":
            items.append(
                {
                    "id": svc.get("id"),
                    "severity": "warning",
                    "title": f"Service degraded: {svc.get('name')}",
                    "actions": ["logs", "restart"],
                }
            )
    if not items and not active_dispatches:
        items.append(
            {
                "id": "all-clear",
                "severity": "info",
                "title": "All systems operational",
                "actions": [],
            }
        )
    return items


def _recommendations(attention: list, active: list) -> list[dict]:
    recs: list[dict] = []
    if any(a.get("severity") == "error" for a in attention):
        recs.append({"id": "r1", "text": "Review failed dispatches and retry or reroute profile"})
    if len(active) == 0:
        recs.append({"id": "r2", "text": "No active agents — consider running morning intelligence cron"})
    return recs
