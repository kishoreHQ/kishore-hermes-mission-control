"""System status aggregate — V1 parity + V2 extensions."""

from __future__ import annotations

from datetime import datetime, timezone

from app.services import hermes_adapter, legacy_adapter, probes, v1_bridge


def build_status(include_heavy: bool = True) -> dict:
    v1 = v1_bridge.fetch_v1_status() if include_heavy else None
    if v1:
        return v1

    services_static = legacy_adapter.list_services()
    services = [probes.probe_service(s) for s in services_static] if include_heavy else services_static
    cron_jobs = hermes_adapter.list_cron_summaries()
    stats = hermes_adapter.session_stats()
    workflows_cfg = legacy_adapter.read_json("workflows.json", default={"workflows": [], "agents": []})
    workflows = workflows_cfg.get("workflows", [])
    review_items = [j for j in cron_jobs if j.get("needs_review")]
    enabled_jobs = [j for j in cron_jobs if j.get("enabled")]

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "workflows": workflows,
        "agents": workflows_cfg.get("agents", []),
        "services": services,
        "profiles": hermes_adapter.list_profiles(),
        "skills": hermes_adapter.list_skills(),
        "plugins": hermes_adapter.list_plugins(),
        "active_runs": legacy_adapter.list_active_runs(),
        "recent_runs": legacy_adapter.list_runs(20),
        "scheduled_tasks": cron_jobs[:20],
        "review_queue": review_items[:8],
        "tasks": legacy_adapter.list_tasks()[:30],
        "workflows_multi": legacy_adapter.list_workflows(),
        "cost_tracker": {
            "estimated_cost_usd": stats.get("cost", 0.0),
            "tokens": stats.get("tokens", 0),
            "models": stats.get("models", []),
        },
        "summary": {
            "online_workflows": sum(1 for w in workflows if w.get("status") == "online"),
            "blocked_workflows": sum(1 for w in workflows if w.get("blocker")),
            "enabled_crons": len(enabled_jobs),
            "review_items": len(review_items),
            "sessions": stats.get("sessions", 0),
            "messages": stats.get("messages", 0),
            "tokens": stats.get("tokens", 0),
            "cost": stats.get("cost", 0.0),
            "services_online": sum(1 for s in services if s.get("status") == "online"),
        },
        "source": "v2_adapters",
    }
