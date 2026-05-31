#!/usr/bin/env python3
"""Mission Control: unified local control plane for Hermes systems. No secrets."""
from __future__ import annotations

import json
import os
import re
import secrets
import sqlite3
import subprocess
import threading
import time
import uuid
from datetime import datetime, timezone
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from urllib.request import Request, urlopen

import dispatch_engine  # parallel dispatch, live status, retry, timeline, gateways

ROOT = Path(__file__).resolve().parent
STATIC = ROOT / "static"
DATA_DIR = ROOT / "data"
WORKFLOWS_DATA = DATA_DIR / "workflows.json"
SERVICES_DATA = DATA_DIR / "services.json"
NIGHTLY_DATA = DATA_DIR / "nightly_builds.json"
TASKS_DATA = DATA_DIR / "tasks.json"
DOCS_DATA = DATA_DIR / "docs.json"
ACTION_LOG = DATA_DIR / "action_log.jsonl"
RUNS_DATA = DATA_DIR / "runs.jsonl"
PROFILE_SETTINGS = DATA_DIR / "profile_settings.json"
ROUTING_HISTORY = DATA_DIR / "routing_history.jsonl"
ROUTING_INDEX = DATA_DIR / "profile_routing_index.json"
ROUTING_THRESHOLD = DATA_DIR / "routing_threshold.json"
WORKFLOWS_MULTI_DATA = DATA_DIR / "workflows_multi.json"
# Use the dispatch engine lock too; workflow writes happen from both server.py
# handlers and dispatch_engine monitor threads in the same process.
WORKFLOW_FILE_LOCK = dispatch_engine.dispatch_file_lock
DISPATCH_DATA = DATA_DIR / "dispatch_queue.jsonl"
HERMES_HOME = Path(os.environ.get("HERMES_HOME", "/root/.hermes")).expanduser()
PROFILES_DIR = HERMES_HOME / "profiles"
SKILLS_DIR = HERMES_HOME / "skills"
PLUGINS_DIR = HERMES_HOME / "plugins"
CRON_JOBS = HERMES_HOME / "cron" / "jobs.json"
STATE_DB = HERMES_HOME / "state.db"
CRON_OUTPUT = HERMES_HOME / "cron" / "output"
APPROVAL_TTL_SECONDS = 600
PENDING_APPROVALS: dict[str, dict] = {}

SECRET_HINTS = (".env", "token", "secret", "auth", "credential", "key", "password", "cookie")
SECRET_RE = re.compile(r"(?i)(api[_-]?key|token|secret|password|credential|cookie)(\s*[:=]\s*)([^\s\"']+)")
SAFE_SYSTEMD_RESTARTS = {"mission-control.service", "hermes-webui.service", "claw3d-studio.service", "claw3d-adapter.service"}
SERVICE_ALLOWLIST = {
    "mission-control.service", "hermes-dashboard.service", "hermes-gateway.service", "hermes-webui.service",
    "claw3d-studio.service", "claw3d-adapter.service", "tailscaled.service", "cron.service", "memory-wiki.service",
}

ACTION_DEFS = {
    "refresh_all_status": {"risk": "safe", "label": "Refresh all statuses"},
    "view_service_logs": {"risk": "safe", "label": "View service logs"},
    "test_adapter": {"risk": "safe", "label": "Test Claw3D adapter"},
    "test_ws_adapter": {"risk": "safe", "label": "Test Claw3D WebSocket adapter"},
    "export_status_report": {"risk": "safe", "label": "Export status report"},
    "create_task": {"risk": "safe", "label": "Create draft task"},
    "update_task": {"risk": "safe", "label": "Update task"},
    "move_task": {"risk": "safe", "label": "Move Kanban task"},
    "archive_task": {"risk": "safe", "label": "Archive Kanban task"},
    "assign_task": {"risk": "safe", "label": "Assign task to profile"},
    "create_nightly_build": {"risk": "safe", "label": "Create nightly build"},
    "update_nightly_build": {"risk": "safe", "label": "Update nightly build"},
    "upload_nightly_attachment": {"risk": "safe", "label": "Upload nightly build attachment"},
    "reload_profile": {"risk": "medium", "label": "Reload profile configuration"},
    "edit_profile": {"risk": "safe", "label": "Edit profile description"},
    "test_profile_routing": {"risk": "safe", "label": "Test profile routing"},
    "open_output": {"risk": "safe", "label": "Open latest output"},
    "fix_prompt": {"risk": "safe", "label": "Generate fix prompt"},
    "run_cron": {"risk": "medium", "label": "Run selected cron now"},
    "pause_cron": {"risk": "medium", "label": "Pause cron"},
    "resume_cron": {"risk": "medium", "label": "Resume cron"},
    "send_telegram_summary": {"risk": "medium", "label": "Send status summary to Telegram"},
    "restart_service": {"risk": "medium", "label": "Restart safe service"},
    "run_claw3d_standup": {"risk": "medium", "label": "Run Claw3D standup"},
    # Multi-profile workflow actions
    "create_workflow": {"risk": "safe", "label": "Create multi-profile workflow"},
    "start_workflow": {"risk": "medium", "label": "Start workflow"},
    "pause_workflow": {"risk": "medium", "label": "Pause workflow"},
    "retry_subtask": {"risk": "safe", "label": "Retry failed subtask"},
    "reroute_subtask": {"risk": "safe", "label": "Reroute subtask to profile"},
    "synthesize_workflow": {"risk": "safe", "label": "Synthesize final output"},
    # Dispatch actions
    "dispatch_workflow": {"risk": "medium", "label": "Dispatch workflow to agents"},
    "dispatch_subtask": {"risk": "medium", "label": "Dispatch subtask to agent"},
    "retry_dispatch": {"risk": "safe", "label": "Retry failed dispatch"},
    "cancel_dispatch": {"risk": "safe", "label": "Cancel pending dispatch"},
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sanitize_output(text: object, max_len: int = 12000) -> str:
    text = "" if text is None else str(text)
    text = SECRET_RE.sub(r"\1\2[REDACTED]", text)
    if len(text) > max_len:
        return text[-max_len:]
    return text


def safe_text(value: object, max_len: int = 160) -> str:
    text = "" if value is None else str(value)
    text = " ".join(text.split())
    if len(text) > max_len:
        text = text[: max_len - 1] + "…"
    return sanitize_output(text, max_len)


def json_response(handler, payload: object, status: int = 200):
    body = json.dumps(payload, indent=2, default=str).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Cache-Control", "no-store")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def read_json_body(handler) -> dict:
    length = int(handler.headers.get("Content-Length") or 0)
    if length <= 0 or length > 262144:
        return {}
    try:
        payload = json.loads(handler.rfile.read(length).decode("utf-8"))
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def read_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # Use a unique temp path per write. Workflow dispatch uses background
    # threads, and a shared `file.json.tmp` path can be replaced by one thread
    # while another is still trying to rename it.
    tmp = path.with_suffix(path.suffix + f".{uuid.uuid4().hex}.tmp")
    tmp.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")
    tmp.replace(path)


def run(cmd: list[str], timeout: int = 5) -> tuple[int, str]:
    try:
        p = subprocess.run(cmd, text=True, capture_output=True, timeout=timeout)
        return p.returncode, sanitize_output((p.stdout + p.stderr).strip())
    except Exception as exc:
        return 1, sanitize_output(str(exc))


def http_probe(url: str, timeout: int = 3) -> dict:
    started = time.time()
    try:
        req = Request(url, headers={"User-Agent": "MissionControl/1.0"})
        with urlopen(req, timeout=timeout) as resp:
            body = resp.read(5000).decode("utf-8", errors="replace")
            content_type = resp.headers.get("content-type", "")
            ok = 200 <= int(resp.status) < 400
            summary = body.strip().replace("\n", " ")[:500]
            parsed = None
            if "json" in content_type.lower():
                try:
                    parsed = json.loads(body)
                except Exception:
                    parsed = None
            return {"ok": ok, "status_code": resp.status, "content_type": content_type, "latency_ms": int((time.time() - started) * 1000), "summary": sanitize_output(summary, 800), "json": parsed}
    except Exception as exc:
        return {"ok": False, "status_code": None, "content_type": "", "latency_ms": int((time.time() - started) * 1000), "summary": sanitize_output(str(exc), 500), "json": None}


def service_status(service: str) -> dict:
    if service not in SERVICE_ALLOWLIST:
        return {"service": service, "active": "blocked", "enabled": "unknown", "ok": False}
    code, active = run(["systemctl", "is-active", service], timeout=3)
    _, enabled = run(["systemctl", "is-enabled", service], timeout=3)
    return {"service": service, "active": active.splitlines()[0] if active else "unknown", "enabled": enabled.splitlines()[0] if enabled else "unknown", "ok": code == 0 and active.startswith("active")}


def port_status(port: int) -> dict:
    code, _ = run(["bash", "-lc", f"ss -ltn | awk '{{print $4}}' | grep -E '(:|\\]){int(port)}$' >/dev/null"], timeout=3)
    return {"port": int(port), "listening": code == 0}


def load_services() -> list[dict]:
    return read_json(SERVICES_DATA, [])


def service_inventory() -> list[dict]:
    services = []
    for svc in load_services():
        item = dict(svc)
        item["systemd"] = service_status(str(svc.get("systemd_service", ""))) if svc.get("systemd_service") else None
        item["port_status"] = port_status(int(svc.get("port", 0))) if svc.get("port") else None
        health_url = str(svc.get("url", "")).rstrip("/") + str(svc.get("health_endpoint") or "/")
        item["health"] = http_probe(health_url)
        item["last_checked"] = now_iso()
        if item["systemd"] and item["systemd"].get("ok") and item["health"].get("ok"):
            item["status"] = "online"
        elif item["systemd"] and item["systemd"].get("ok"):
            item["status"] = "degraded"
        elif item["port_status"] and item["port_status"].get("listening"):
            item["status"] = "degraded"
        else:
            item["status"] = "offline"
        services.append(item)
    return services


def load_cron_jobs() -> list[dict]:
    payload = read_json(CRON_JOBS, {"jobs": []})
    return payload.get("jobs", []) if isinstance(payload, dict) else []


def find_job(job_id: str) -> dict | None:
    for job in load_cron_jobs():
        if str(job.get("id")) == str(job_id):
            return job
    return None


def latest_output_file(job_id: str) -> Path | None:
    if not job_id:
        return None
    root = (CRON_OUTPUT / job_id).resolve()
    base = CRON_OUTPUT.resolve()
    try:
        root.relative_to(base)
    except Exception:
        return None
    if not root.exists():
        return None
    files = [p for p in root.rglob("*") if p.is_file() and not any(h in str(p).lower() for h in SECRET_HINTS)]
    if not files:
        return None
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return files[0]


def delivery_label(job: dict) -> str:
    deliver = safe_text(job.get("deliver") or "local", 60)
    if deliver == "origin":
        return "origin channel"
    if deliver.startswith("telegram"):
        return "telegram"
    return deliver


def job_needs_review(job: dict) -> bool:
    return bool(job.get("last_error") or job.get("last_delivery_error") or job.get("last_status") == "error" or job.get("state") == "error")


def summarize_job(job: dict) -> dict:
    repeat = job.get("repeat") or {}
    return {
        "id": job.get("id"),
        "name": safe_text(job.get("name") or job.get("id") or "Unnamed job", 90),
        "enabled": bool(job.get("enabled", True)),
        "state": safe_text(job.get("state") or "unknown", 30),
        "schedule": safe_text(job.get("schedule_display") or (job.get("schedule") or {}).get("display") or "manual", 60),
        "next_run_at": job.get("next_run_at"),
        "last_run_at": job.get("last_run_at"),
        "last_status": job.get("last_status") or "unknown",
        "last_error": safe_text(job.get("last_error") or job.get("last_delivery_error") or "", 180),
        "deliver": delivery_label(job),
        "skills": [safe_text(s, 40) for s in (job.get("skills") or [])[:4]],
        "toolsets": [safe_text(s, 30) for s in (job.get("enabled_toolsets") or [])[:5]],
        "model": safe_text(job.get("model") or "default", 60),
        "provider": safe_text(job.get("provider") or "default", 60),
        "completed": repeat.get("completed") if isinstance(repeat, dict) else None,
        "repeat_times": repeat.get("times") if isinstance(repeat, dict) else None,
        "needs_review": job_needs_review(job),
        "mode": "script" if job.get("no_agent") else "agent",
        "has_output": latest_output_file(str(job.get("id") or "")) is not None,
    }


def session_stats() -> dict:
    stats = {"sessions": 0, "messages": 0, "tokens": 0, "cost": 0.0, "models": []}
    if not STATE_DB.exists():
        return stats
    try:
        con = sqlite3.connect(f"file:{STATE_DB}?mode=ro", uri=True, timeout=1)
        cur = con.cursor()
        for table, key in (("sessions", "sessions"), ("messages", "messages")):
            try:
                stats[key] = int(cur.execute(f"select count(*) from {table}").fetchone()[0])
            except Exception:
                pass
        try:
            row = cur.execute("select coalesce(sum(input_tokens),0), coalesce(sum(output_tokens),0), coalesce(sum(cache_read_tokens),0), coalesce(sum(cache_write_tokens),0), coalesce(sum(reasoning_tokens),0) from sessions").fetchone()
            stats["tokens"] = int(sum(row or []))
        except Exception:
            pass
        try:
            stats["cost"] = float(cur.execute("select coalesce(sum(coalesce(actual_cost_usd, estimated_cost_usd, 0)),0) from sessions").fetchone()[0] or 0)
        except Exception:
            pass
        try:
            rows = cur.execute("select coalesce(model,'unknown'), count(*), coalesce(sum(input_tokens+output_tokens+cache_read_tokens+cache_write_tokens+reasoning_tokens),0) from sessions group by model order by count(*) desc limit 6").fetchall()
            stats["models"] = [{"model": r[0], "sessions": int(r[1]), "tokens": int(r[2] or 0)} for r in rows]
        except Exception:
            pass
        con.close()
    except Exception:
        pass
    return stats


def recent_files() -> list[dict]:
    roots = [Path("/root/career-ops/interview-prep"), Path("/root/wiki"), ROOT, CRON_OUTPUT]
    files: list[Path] = []
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            low = str(path).lower()
            if any(hint in low for hint in SECRET_HINTS) or "/.git/" in low:
                continue
            if path.suffix.lower() not in {".md", ".pdf", ".json", ".txt", ".html", ".log"}:
                continue
            files.append(path)
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    out = []
    for path in files[:10]:
        try:
            st = path.stat()
            out.append({"path": str(path), "name": path.name, "size": st.st_size, "updated_at": datetime.fromtimestamp(st.st_mtime, timezone.utc).isoformat(timespec="seconds")})
        except Exception:
            continue
    return out


def build_task_board(workflows: list[dict], jobs: list[dict]) -> dict:
    columns = {"in_progress": [], "in_review": [], "scheduled": []}
    for workflow in workflows:
        cls = workflow.get("runtime_state") or workflow.get("status") or "unknown"
        card = {"id": workflow.get("id"), "title": workflow.get("name"), "kind": "workflow", "status": cls, "subtitle": workflow.get("purpose"), "meta": workflow.get("cadence")}
        if cls == "online":
            columns["in_progress"].append(card)
        elif workflow.get("blocker") or cls in {"blocked", "partial", "error"}:
            card["subtitle"] = workflow.get("blocker") or workflow.get("purpose")
            columns["in_review"].append(card)
    for job in [summarize_job(j) for j in jobs]:
        card = {"id": job["id"], "title": job["name"], "kind": "cron", "status": "review" if job["needs_review"] else job["state"], "subtitle": job["last_error"] or f"Next: {job['next_run_at'] or 'not scheduled'}", "meta": f"{job['schedule']} · {job['mode']} · {job['deliver']}"}
        if job["needs_review"]:
            columns["in_review"].append(card)
        elif job["enabled"]:
            columns["scheduled"].append(card)
    for key in columns:
        columns[key] = columns[key][:10]
    return columns


def cron_summary_text() -> str:
    status = api_status(include_heavy=False)
    s = status.get("summary", {})
    lines = ["Mission Control status", f"Online workflows: {s.get('online_workflows')}", f"Needs review: {s.get('review_items')}", f"Enabled crons: {s.get('enabled_crons')}", f"Sessions: {s.get('sessions')}", f"Messages: {s.get('messages')}", f"Tokens: {s.get('tokens')}", f"Estimated cost: ${float(s.get('cost') or 0):.2f}", "", "Dashboard: https://gcp-hermes.tail57c68b.ts.net:8090/"]
    return sanitize_output("\n".join(lines), 4000)


def build_fix_prompt(job: dict, output_excerpt: str) -> str:
    sj = summarize_job(job)
    return sanitize_output(f"""Fix this Hermes cron job failure. Inspect evidence first, avoid exposing secrets, and verify with a real run before claiming success.

Job ID: {sj.get('id')}
Name: {sj.get('name')}
Schedule: {sj.get('schedule')}
Mode: {sj.get('mode')}
Delivery: {sj.get('deliver')}
Last status: {sj.get('last_status')}
Last run: {sj.get('last_run_at')}
Last error: {sj.get('last_error') or 'not recorded'}

Latest output excerpt:
```text
{output_excerpt or 'No output file found.'}
```

Required result:
1. Identify root cause.
2. Make the smallest safe fix.
3. Run/verify the job or related script.
4. Report exactly what changed and any remaining blocker.
""", 12000)


def append_action_log(record: dict) -> dict:
    record = dict(record)
    record.setdefault("id", uuid.uuid4().hex[:12])
    record.setdefault("created_at", now_iso())
    record.setdefault("requested_by", "Kishore")
    ACTION_LOG.parent.mkdir(parents=True, exist_ok=True)
    with ACTION_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, default=str) + "\n")
    return record


def action_history(limit: int = 50) -> list[dict]:
    if not ACTION_LOG.exists():
        return []
    lines = ACTION_LOG.read_text(encoding="utf-8", errors="replace").splitlines()[-limit:]
    out = []
    for line in reversed(lines):
        try:
            out.append(json.loads(line))
        except Exception:
            continue
    return out


# ── Run tracking ──────────────────────────────────────────────────────

RUN_STATUSES = {"queued", "running", "waiting_for_approval", "succeeded", "failed", "cancelled", "timed_out", "needs_review"}
RUN_TRIGGERS = {"dashboard", "chat", "cron", "kanban", "api", "claw3d", "nightly"}

DASHBOARD_URL = "https://gcp-hermes.tail57c68b.ts.net:8090/"


def _append_run(record: dict) -> dict:
    record.setdefault("run_id", uuid.uuid4().hex[:12])
    record.setdefault("created_at", now_iso())
    record.setdefault("updated_at", now_iso())
    RUNS_DATA.parent.mkdir(parents=True, exist_ok=True)
    with RUNS_DATA.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, default=str) + "\n")
    return record


def _read_runs(limit: int = 200) -> list[dict]:
    if not RUNS_DATA.exists():
        return []
    lines = RUNS_DATA.read_text(encoding="utf-8", errors="replace").splitlines()
    runs = []
    for line in lines[-limit:]:
        try:
            runs.append(json.loads(line))
        except Exception:
            continue
    return runs


def _find_run(run_id: str) -> dict | None:
    if not RUNS_DATA.exists():
        return None
    for line in RUNS_DATA.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            obj = json.loads(line)
            if obj.get("run_id") == run_id:
                return obj
        except Exception:
            continue
    return None


def _update_run(run_id: str, patch: dict) -> dict:
    if not RUNS_DATA.exists():
        return {}
    lines = RUNS_DATA.read_text(encoding="utf-8", errors="replace").splitlines()
    updated_run = {}
    new_lines = []
    for line in lines:
        try:
            obj = json.loads(line)
        except Exception:
            new_lines.append(line + "\n")
            continue
        if obj.get("run_id") == run_id:
            obj.update(patch)
            obj["updated_at"] = now_iso()
            updated_run = obj
        new_lines.append(json.dumps(obj, default=str) + "\n")
    RUNS_DATA.parent.mkdir(parents=True, exist_ok=True)
    RUNS_DATA.write_text("".join(new_lines), encoding="utf-8")
    return updated_run


def start_run(payload: dict) -> dict:
    settings = get_profile_settings()
    # Auto-route profile if not explicitly provided
    explicit_profile = str(payload.get("profile") or "").strip()
    if explicit_profile and explicit_profile in PROFILE_KEYWORDS:
        # Explicit profile provided — use it
        selected = explicit_profile
        routing = {"profile_mode": "manual", "selected_profile": selected, "confidence": 1.0, "reason": "Explicitly selected profile.", "mode": "manual"}
    else:
        # Auto-route
        routing = route_profile_v2(payload)
        selected = routing["selected_profile"]
        # Append routing history
        append_routing_history({"task_title": payload.get("title", ""), "recommended": selected, "selected": selected, "confidence": routing["confidence"], "reason": routing.get("reason", ""), "mode": routing.get("mode", "auto"), "matched_signals": routing.get("matched_signals", []), "manual": False})

    record = {
        "run_id": str(payload.get("run_id") or uuid.uuid4().hex[:12]),
        "title": safe_text(payload.get("title") or "Untitled run", 200),
        "trigger_source": str(payload.get("trigger_source") or "api") if str(payload.get("trigger_source") or "") in RUN_TRIGGERS else "api",
        "service": safe_text(payload.get("service") or "mission-control", 60),
        "profile": selected,
        # Profile routing metadata
        "profile_mode": routing.get("mode", "auto"),
        "selected_profile": selected,
        "recommended_profile": routing.get("selected_profile", selected),
        "routing_confidence": routing.get("confidence", 0),
        "routing_reason": routing.get("reason", ""),
        "alternate_profiles": routing.get("alternates", []),
        "profile_switch_history": [],
        "status": "running",
        "current_step": safe_text(payload.get("current_step") or "started", 200),
        "started_at": now_iso(),
        "finished_at": None,
        "duration": None,
        "input": payload.get("input") or {},
        "output": {},
        "error": {},
        "logs": [],
        "telegram_sent": False,
        "telegram_updates": [],
        "related_task_id": safe_text(payload.get("related_task_id") or "", 40),
        "related_nightly_build_id": safe_text(payload.get("related_nightly_build_id") or "", 40),
    }
    result = _append_run(record)
    _notify_telegram_run(result, "started")
    return result


def append_run_log(run_id: str, payload: dict) -> dict:
    run = _find_run(run_id)
    if not run:
        return {"ok": False, "error": "Run not found"}
    entry = {
        "timestamp": now_iso(),
        "level": safe_text(payload.get("level") or "info", 20),
        "message": safe_text(payload.get("message") or "", 2000),
        "step": safe_text(payload.get("step") or run.get("current_step", ""), 200),
    }
    logs = list(run.get("logs") or [])
    logs.append(entry)
    return _update_run(run_id, {"logs": logs[-200:], "current_step": entry["step"]})


def update_run_status(run_id: str, payload: dict) -> dict:
    run = _find_run(run_id)
    if not run:
        return {"ok": False, "error": "Run not found"}
    status = str(payload.get("status") or "")
    patch = {}
    if status in RUN_STATUSES:
        patch["status"] = status
    step = payload.get("current_step")
    if step:
        patch["current_step"] = safe_text(step, 200)
    output = payload.get("output")
    if output is not None:
        patch["output"] = output
    error = payload.get("error")
    if error is not None:
        patch["error"] = error
    if not patch:
        return {"ok": False, "error": "No valid fields to update"}
    updated = _update_run(run_id, patch)
    # Send progress Telegram for important transitions
    if status in {"failed", "needs_review"}:
        _notify_telegram_run(updated, "failed" if status == "failed" else "progress")
    return updated


def finish_run(run_id: str, payload: dict) -> dict:
    run = _find_run(run_id)
    if not run:
        return {"ok": False, "error": "Run not found"}
    status = str(payload.get("status") or "succeeded")
    if status not in RUN_STATUSES:
        status = "succeeded"
    start = run.get("started_at")
    finished = now_iso()
    duration = None
    if start:
        try:
            st = datetime.fromisoformat(str(start).replace("Z", "+00:00"))
            ft = datetime.fromisoformat(finished.replace("Z", "+00:00"))
            duration = round((ft - st).total_seconds(), 1)
        except Exception:
            pass
    patch = {
        "status": status,
        "finished_at": finished,
        "duration": duration,
        "current_step": safe_text(payload.get("current_step") or run.get("current_step", ""), 200),
        "output": payload.get("output") or run.get("output") or {},
        "error": payload.get("error") or run.get("error") or {},
    }
    updated = _update_run(run_id, patch)
    if status == "succeeded":
        _notify_telegram_run(updated, "succeeded")
    elif status == "failed":
        _notify_telegram_run(updated, "failed")
    return updated


def get_runs(limit: int = 50, status_filter: str = "") -> list[dict]:
    runs = _read_runs(limit=400)
    filtered = [r for r in runs if not status_filter or r.get("status") == status_filter]
    filtered.sort(key=lambda r: r.get("started_at") or "", reverse=True)
    return filtered[:limit]


def get_active_runs() -> list[dict]:
    return [r for r in _read_runs(limit=200) if r.get("status") in {"queued", "running", "waiting_for_approval"}]


def get_run(run_id: str) -> dict | None:
    return _find_run(run_id)


# ── Telegram notifications for runs ───────────────────────────────────

def _send_telegram(text: str) -> bool:
    """Send a message via hermes CLI to the home channel. Returns True on success."""
    try:
        p = subprocess.run(
            ["hermes", "send", "--to", "telegram", "--subject", "[Mission Control]"],
            input=text, text=True, capture_output=True, timeout=30,
        )
        return p.returncode == 0
    except Exception:
        return False


def _notify_telegram_run(run: dict, event: str) -> None:
    """Send concise, safe Telegram notification for run events."""
    run_id = run.get("run_id", "?")
    title = run.get("title", "Untitled")
    trigger = run.get("trigger_source", "?")
    profile = run.get("profile", run.get("selected_profile", "Default"))
    profile_mode = run.get("profile_mode", "auto")
    routing_reason = run.get("routing_reason", "")
    status = run.get("status", "?")
    step = run.get("current_step", "")
    duration = run.get("duration")
    error_info = run.get("error") or {}
    # Profile line for all messages
    mode_icon = "🔄" if profile_mode == "auto" else "👆"
    profile_line = f"Profile: {profile} ({mode_icon} {profile_mode})\n"

    if event == "started":
        reason_line = f"Reason: {routing_reason}\n" if routing_reason and profile_mode == "auto" else ""
        msg = f"""🚀 *Run Started*
*{title}*
{profile_line}{reason_line}Source: {trigger}
Run ID: `{run_id}`
Started: {run.get('started_at', '?')[:19]}

[Dashboard →]({DASHBOARD_URL}#runs)"""
    elif event == "succeeded":
        dur_str = f" · {duration}s" if duration else ""
        out_preview = sanitize_output(str(run.get("output", ""))[:300], 300)
        msg = f"""✅ *Run Succeeded*
*{title}*
{profile_line}Status: succeeded{dur_str}
Run ID: `{run_id}`

{out_preview if out_preview else ''}
[Dashboard →]({DASHBOARD_URL}#runs)"""
    elif event == "failed":
        err_summary = safe_text(error_info.get("message") or error_info.get("summary") or str(error_info)[:200], 200)
        msg = f"""❌ *Run Failed*
*{title}*
{profile_line}Failed at: {step or 'unknown step'}
Error: {err_summary}
Run ID: `{run_id}`

[Dashboard →]({DASHBOARD_URL}#runs)"""
    elif event == "progress":
        msg = f"""⏳ *Run Progress*
*{title}* → {step}
{profile_line}Status: {status}
Run ID: `{run_id}`

[Dashboard →]({DASHBOARD_URL}#runs)"""
    elif event == "profile_switch":
        history = run.get("profile_switch_history") or []
        last = history[-1] if history else {}
        msg = f"""🔄 *Profile Switched*
*{title}*
From: {last.get('from', '?')} → To: {last.get('to', '?')}
Reason: {last.get('reason', 'Manual switch')}
Run ID: `{run_id}`

[Dashboard →]({DASHBOARD_URL}#runs)"""
    else:
        return

    def _send_and_record():
        sent = _send_telegram(msg)
        runs_file = RUNS_DATA
        if runs_file.exists():
            lines = runs_file.read_text(encoding="utf-8", errors="replace").splitlines()
            new_lines = []
            for line in lines:
                try:
                    obj = json.loads(line)
                except Exception:
                    new_lines.append(line + "\n")
                    continue
                if obj.get("run_id") == run_id:
                    obj["telegram_sent"] = True
                    updates = list(obj.get("telegram_updates") or [])
                    updates.append({"event": event, "sent_at": now_iso(), "ok": sent})
                    obj["telegram_updates"] = updates[-20:]
                new_lines.append(json.dumps(obj, default=str) + "\n")
            runs_file.write_text("".join(new_lines), encoding="utf-8")
    threading.Thread(target=_send_and_record, daemon=True).start()


# ── Profile data ──────────────────────────────────────────────────────

def get_profiles() -> list[dict]:
    profiles = []
    profile_names = ["Default", "Coder", "ContentCreator", "DeepResearch", "MarketAnalyst", "Tutor"]
    active_runs = get_active_runs()
    for name in profile_names:
        pdir = PROFILES_DIR / name.lower() if name != "Default" else None
        soul_path = (pdir / "SOUL.md") if pdir else None
        has_soul = soul_path.exists() if soul_path else False
        soul_size = soul_path.stat().st_size if has_soul else 0
        # Get description from first lines of SOUL.md
        desc = ""
        if has_soul:
            try:
                first_lines = soul_path.read_text(encoding="utf-8")[:500]
                desc = safe_text(first_lines.split("\n")[:3], 300)
            except Exception:
                desc = ""
        profile_runs = [r for r in active_runs if r.get("profile", "").lower() == name.lower()]
        profiles.append({
            "name": name,
            "directory": str(pdir) if pdir else "built-in",
            "has_soul": has_soul,
            "soul_size": soul_size,
            "description": desc or f"Built-in {name} profile",
            "active_runs": len(profile_runs),
            "active_run_ids": [r["run_id"] for r in profile_runs[:5]],
            "tools_linked": [],  # future: parse from SOUL.md
            "last_checked": now_iso(),
        })
    return profiles


# ── Profile Routing Engine ────────────────────────────────────────────

PROFILE_KEYWORDS = {
    "Coder": {
        "primary": ["code", "coding", "debug", "bug", "fix", "implement", "devops", "linux", "server", "gcp",
                     "docker", "api", "endpoint", "script", "github", "git", "system", "design", "log",
                     "deploy", "deployment", "automation", "automate", "mission control", "server.py",
                     "app.js", "backend", "frontend", "build", "compile", "test", "patch", "infrastructure",
                     "vps", "ssh", "cloud", "config", "configuration", "service", "daemon", "cron job",
                     "python", "javascript", "go", "rust", "sql", "database", "monitoring", "alert",
                     "cli", "terminal", "command", "restart", "install", "package", "dependency"],
        "weight": 1.2,
    },
    "ContentCreator": {
        "primary": ["post", "tweet", "x post", "article", "instagram", "youtube", "shorts", "reel",
                     "caption", "hook", "headline", "script", "thumbnail", "image prompt", "video",
                     "social media", "content", "calendar", "schedule", "publish", "draft", "idea",
                     "viral", "engagement", "audience", "follower", "creator", "influencer",
                     "hashtag", "trending", "ai avatar", "ai content", "character", "persona"],
        "weight": 1.2,
    },
    "DeepResearch": {
        "primary": ["research", "investigate", "compare", "comparison", "analysis", "analyze",
                     "fact", "check", "evidence", "source", "report", "deep dive", "survey",
                     "competitor", "market", "opportunity", "tool comparison", "benchmark",
                     "findings", "white paper", "literature", "review", "recommendation",
                     "decision brief", "pros and cons", "evaluate", "assessment", "audit"],
        "weight": 1.2,
    },
    "MarketAnalyst": {
        "primary": ["stock", "nifty", "sensex", "bse", "nse", "indian stock", "us stock",
                     "mutual fund", "etf", "reit", "invit", "aif", "private equity", "crypto",
                     "bitcoin", "ethereum", "portfolio", "watchlist", "scalp", "day trade",
                     "position", "dividend", "market cap", "valuation", "pe ratio", "technicals",
                     "chart", "candlestick", "support", "resistance", "rsi", "macd", "moving average",
                     "hdfc", "reliance", "tcs", "icici", "financial", "trading", "invest", "sector",
                     "small cap", "mid cap", "large cap", "fii", "dii", "option", "future",
                     "stockforge", "alpha", "factor", "screener", "pick", "nifty 200"],
        "weight": 1.2,
    },
    "Tutor": {
        "primary": ["teach", "learn", "explain", "tutorial", "lesson", "course", "quiz",
                     "question", "answer", "concept", "article explanation", "transcript",
                     "yt video", "summarize", "section", "chapter", "exercises", "practice",
                     "kubernetes", "k8s", "devops learning", "go lang", "interview", "prep",
                     "revision", "recap", "study", "guide", "study guide", "walkthrough",
                     "beginner", "advanced", "skill", "certification", "exam"],
        "weight": 1.2,
    },
    "Default": {
        "primary": ["orchestrate", "coordinate", "plan", "workflow", "pipeline", "multi",
                     "dispatch", "route", "decompose", "subtask", "overview", "project",
                     "manage", "monitor", "status", "report", "dashboard"],
        "weight": 0.8,
    },
}

# Secondary keywords that span profiles (lower weight)
PROFILE_SECONDARY = {
    "Coder": ["test", "ci/cd", "pipeline", "code review", "merge", "branch", "release"],
    "ContentCreator": ["render", "export", "upload", "schedule post", "media", "asset"],
    "DeepResearch": ["data", "metric", "chart", "graph", "statistics", "history", "trend"],
    "MarketAnalyst": ["economy", "gdp", "inflation", "interest rate", "fed", "rbi", "market"],
    "Tutor": ["example", "analogy", "diagram", "step by step", "code snippet", "cheat sheet"],
    "Default": ["setup", "init", "bootstrap", "scaffold"],
}


def _tokenize(text: str) -> list[str]:
    """Lowercase, strip punctuation, split into tokens."""
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    return [t for t in text.split() if len(t) > 1]


def _score_profile(tokens: list[str], profile: str) -> float:
    """Score how well the tokens match a profile's keywords."""
    keywords = PROFILE_KEYWORDS.get(profile, {})
    primary = keywords.get("primary", [])
    secondary = PROFILE_SECONDARY.get(profile, [])
    weight = keywords.get("weight", 1.0)
    score = 0.0
    text = " ".join(tokens)
    # Multi-word phrases (check first for better matching)
    for kw in primary:
        if " " in kw and kw in text:
            score += 2.0 * weight
        elif " " not in kw and kw in tokens:
            score += 1.0 * weight
    for kw in secondary:
        if " " in kw and kw in text:
            score += 0.5 * weight
        elif " " not in kw and kw in tokens:
            score += 0.3 * weight
    return score


def _detect_multi_profile(tokens: list[str], scores: dict[str, float]) -> list[dict] | None:
    """Check if task needs multiple profiles. Returns list of profile steps or None."""
    text = " ".join(tokens)
    # Detect common multi-profile patterns
    patterns = [
        (r"(stock|market|finance|nifty|portfolio|trading|invest|hdfc|reliance|sensex).*(carousel|instagram|post|content|create|social|write)", ["MarketAnalyst", "ContentCreator"]),
        (r"research.*and.*(create|make|build|produce|write|post)", ["DeepResearch", "ContentCreator"]),
        (r"(research|analyze|investigate).*(code|implement|build|fix|deploy)", ["DeepResearch", "Coder"]),
        (r"(teach|explain).*(code|implement|deploy)", ["Tutor", "Coder"]),
        (r"(research|analyze).*(stock|market|nifty|portfolio)", ["DeepResearch", "MarketAnalyst"]),
        (r"(build|code|implement).*(deploy|ship|release)", ["Coder", "Default"]),
        (r"(debug|fix|repair).*(document|note|guide|write.*up)", ["Coder", "Default"]),
        (r"(read|article).*(teach|tutor|explain|quiz)", ["Tutor", "Coder"]),
        (r"(build|create|automate).*(content|workflow|pipeline).*(document|note|guide)", ["Default", "Coder", "ContentCreator"]),
    ]
    for pattern, profiles in patterns:
        if re.search(pattern, text):
            # Use pattern-specified order, not score-sorted (dependency order matters)
            return [{"profile": p, "task": _subtask_title(p, "")} for p in profiles]

    # If no pattern matches but two profiles have close scores, suggest dual
    top = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    if len(top) >= 2 and top[0][1] > 1.5 and top[1][1] > top[0][1] * 0.55:
        return [{"profile": top[0][0], "task": "Primary execution"}, {"profile": top[1][0], "task": "Secondary support"}]
    return None


# ── SOUL.md Indexer ───────────────────────────────────────────────────

def _extract_section(text: str, heading: str) -> str:
    """Extract content under a markdown heading."""
    pat = re.compile(rf"^#*\s*{re.escape(heading)}.*?\n(.*?)(?=^#+\s|\Z)", re.MULTILINE | re.DOTALL | re.IGNORECASE)
    m = pat.search(text)
    return m.group(1).strip() if m else ""


def _extract_bullets(text: str) -> list[str]:
    """Extract bullet points from markdown text."""
    bullets = []
    for line in text.split("\n"):
        line = line.strip()
        if line.startswith("* ") or line.startswith("- ") or re.match(r"^\d+\. ", line):
            item = re.sub(r"^[\*\-\d]+\.?\s*", "", line).strip()
            if len(item) > 3:
                bullets.append(item)
    return bullets


def _extract_heading_sections(text: str) -> dict[str, str]:
    """Extract all top-level sections from SOUL.md."""
    sections = {}
    current_heading = "preamble"
    current_content = []
    for line in text.split("\n"):
        if line.startswith("## ") or line.startswith("# "):
            if current_content:
                sections[current_heading] = "\n".join(current_content).strip()
            current_heading = line.lstrip("# ").strip().lower()
            current_content = []
        else:
            current_content.append(line)
    if current_content:
        sections[current_heading] = "\n".join(current_content).strip()
    return sections


def index_profile(profile_name: str) -> dict:
    """Parse a profile's SOUL.md and return routing index."""
    pdir = PROFILES_DIR / profile_name.lower() if profile_name != "Default" else None
    if not pdir or not pdir.exists():
        return _default_routing_index(profile_name)

    soul_path = pdir / "SOUL.md"
    if not soul_path.exists():
        return _default_routing_index(profile_name)

    content = soul_path.read_text(encoding="utf-8")
    sections = _extract_heading_sections(content)

    # Extract identity
    identity = sections.get("identity", "") or sections.get("preamble", "")[:500]

    # Extract mission
    mission_section = sections.get("mission", "") or sections.get("core principles", "")
    mission_bullets = _extract_bullets(mission_section)

    # Extract expertise areas
    expertise = []
    for sec_name, sec_content in sections.items():
        if any(w in sec_name for w in ["identity", "mission", "behavior", "expertise", "coverage", "rules"]):
            expertise.extend(_extract_bullets(sec_content))

    # Build strong keywords from identity + mission + expertise
    strong_keywords = []
    all_text = identity + " " + " ".join(mission_bullets) + " " + " ".join(expertise)
    # Extract key noun phrases and action verbs
    for phrase in re.findall(r"\b[a-z]{4,}(?:\s[a-z]{4,})?\b", all_text.lower()):
        if phrase not in strong_keywords and len(phrase) > 3:
            strong_keywords.append(phrase)

    # Weak keywords from secondary sections
    weak_keywords = []
    for sec_name, sec_content in sections.items():
        if sec_name not in ["identity", "mission", "core principles", "communication style", "safety"]:
            for phrase in re.findall(r"\b[a-z]{3,}\b", sec_content.lower()):
                if phrase not in weak_keywords and phrase not in strong_keywords and len(phrase) > 3:
                    weak_keywords.append(phrase)

    # Task patterns
    task_patterns = _build_task_patterns(profile_name, strong_keywords)

    # Best for / avoid for
    best_for = _summarize_best_for(profile_name, identity, mission_bullets)
    avoid_for = _summarize_avoid_for(profile_name)

    # Example tasks
    example_tasks = _profile_template_tasks(profile_name)

    return {
        "profile": profile_name,
        "source": str(soul_path),
        "summary": identity[:200] if identity else f"{profile_name} profile",
        "mission": mission_bullets[:8],
        "strong_keywords": list(dict.fromkeys(strong_keywords))[:50],
        "weak_keywords": list(dict.fromkeys(weak_keywords))[:30],
        "task_patterns": task_patterns,
        "best_for": best_for,
        "avoid_for": avoid_for,
        "example_tasks": example_tasks,
        "last_indexed_at": now_iso(),
        "soul_size": len(content),
    }


def _default_routing_index(profile_name: str) -> dict:
    return {
        "profile": profile_name,
        "source": "built-in",
        "summary": f"Built-in {profile_name} profile",
        "mission": [],
        "strong_keywords": [],
        "weak_keywords": [],
        "task_patterns": [],
        "best_for": ["General tasks", "Coordination"],
        "avoid_for": [],
        "example_tasks": [],
        "last_indexed_at": now_iso(),
        "soul_size": 0,
    }


def _build_task_patterns(profile_name: str, keywords: list[str]) -> list[str]:
    """Build regex task patterns from profile keywords."""
    patterns = {
        "Coder": [r"\b(fix|debug|build|implement|deploy|compile|patch|restart|install|automate)\b.*\b(code|api|server|docker|bug|error|system|infra|cloud|script|config)\b"],
        "ContentCreator": [r"\b(create|write|post|make|produce|design)\b.*\b(post|tweet|article|video|shorts|reel|instagram|youtube|content|caption|hook|thumbnail|script)\b"],
        "DeepResearch": [r"\b(research|analyze|compare|investigate|evaluate|review|audit)\b.*\b(tool|market|competitor|finding|evidence|source|benchmark|trend|recommendation)\b"],
        "MarketAnalyst": [r"\b(analyze|research|compare|track|screen)\b.*\b(stock|nifty|sensex|fund|etf|reit|portfolio|market|trading|crypto|dividend|valuation|technicals|rsi|macd)\b"],
        "Tutor": [r"\b(teach|learn|explain|tutor|study)\b.*\b(article|concept|kubernetes|k8s|devops|go|certification|quiz|exercise|tutorial|lesson)\b"],
        "Default": [r"\b(orchestrate|coordinate|plan|manage|dispatch|workflow|pipeline|overview|monitor|multi)\b"],
    }
    return patterns.get(profile_name, [])


def _summarize_best_for(profile_name: str, identity: str, mission: list[str]) -> list[str]:
    best_map = {
        "Coder": ["Software engineering", "DevOps/Infrastructure", "Debugging", "Cloud/Server work", "Automation scripts", "API design", "System design"],
        "ContentCreator": ["Social media content", "X/Twitter posts", "YouTube scripts", "Instagram posts/reels", "Content calendars", "Captions/Hooks", "AI image prompts", "Content repurposing"],
        "DeepResearch": ["Research briefs", "Tool comparisons", "Market research", "Competitor analysis", "Decision support", "Fact-checking", "Trend analysis"],
        "MarketAnalyst": ["Stock analysis (NSE/BSE)", "Portfolio review", "Technical analysis", "Mutual fund comparison", "Market screening", "Trading setups", "Investment research"],
        "Tutor": ["Article explanations", "Concept teaching", "Quiz creation", "Study guides", "Tutorial creation", "Interview prep", "Step-by-step walkthroughs"],
        "Default": ["Multi-profile coordination", "Workflow orchestration", "Pipeline management", "Task decomposition", "System monitoring"],
    }
    return best_map.get(profile_name, ["General tasks"])


def _summarize_avoid_for(profile_name: str) -> list[str]:
    avoid_map = {
        "Coder": ["Content creation", "Social media strategy", "Financial analysis"],
        "ContentCreator": ["Server administration", "Deep research", "Financial modeling"],
        "DeepResearch": ["Code implementation", "Live trading", "Social media publishing"],
        "MarketAnalyst": ["Content creation", "Teaching/K-12", "System administration"],
        "Tutor": ["Production deployment", "Financial trading", "Content marketing"],
        "Default": ["Specialized domain work where a profile exists"],
    }
    return avoid_map.get(profile_name, [])


def _profile_template_tasks(profile_name: str) -> list[str]:
    templates = {
        "Coder": ["Fix a bug in server.py", "Deploy new service to GCP", "Debug Docker networking issue", "Automate cron job pipeline", "Refactor API endpoint"],
        "ContentCreator": ["Create 10 X posts from this idea", "Write YouTube script about AI tools", "Design Instagram carousel for DevOps tips", "Generate AI image prompts for avatar content"],
        "DeepResearch": ["Research best AI video generation tools", "Compare Kubernetes vs Nomad", "Analyze competitor content strategy", "Market research for content niches"],
        "MarketAnalyst": ["Analyze HDFC Bank stock fundamentals", "Screen Nifty 200 for momentum picks", "Compare mutual funds for SIP", "Technical analysis of Reliance chart"],
        "Tutor": ["Teach me Kubernetes services", "Explain this Go article with quiz", "Create study guide for AWS certification", "Tutor: Docker networking concepts"],
        "Default": ["Orchestrate multi-profile content pipeline", "Monitor system health and alerts", "Coordinate research-to-content workflow"],
    }
    return templates.get(profile_name, [])


def index_all_profiles() -> dict:
    """Index all profiles and save to routing_index.json."""
    profiles = ["Default", "Coder", "ContentCreator", "DeepResearch", "MarketAnalyst", "Tutor"]
    index = {}
    for name in profiles:
        index[name] = index_profile(name)
    write_json(ROUTING_INDEX, index)
    # Remove top-level "profile" field from each entry (key is the profile name)
    for k, v in index.items():
        v.pop("profile", None)
    return index


def reindex_profile(profile_name: str) -> dict:
    """Re-index a single profile."""
    entry = index_profile(profile_name)
    current = read_json(ROUTING_INDEX, {})
    current[profile_name] = entry
    write_json(ROUTING_INDEX, current)
    return entry


def get_routing_index() -> dict:
    """Load the routing index, auto-indexing if missing."""
    if not ROUTING_INDEX.exists():
        return index_all_profiles()
    idx = read_json(ROUTING_INDEX, {})
    # Ensure all profile names are keys
    for name in ["Default", "Coder", "ContentCreator", "DeepResearch", "MarketAnalyst", "Tutor"]:
        if name not in idx:
            idx[name] = index_profile(name)
    if not idx:
        return index_all_profiles()
    return idx


# ── Profile Run Templates ─────────────────────────────────────────────

def _run_template_prefill(profile_name: str) -> dict:
    """Return profile-specific run template."""
    templates = {
        "Coder": {"repo_path": "~", "files_affected": "", "commands_to_run": "", "test_plan": "", "rollback_plan": ""},
        "ContentCreator": {"platform": "x", "audience": "devops", "content_pillar": "", "format": "post", "tone": "practical", "output_type": "text", "image_prompt_needed": False},
        "DeepResearch": {"research_question": "", "decision_to_support": "", "source_requirements": "primary preferred", "comparison_needed": False, "output_format": "brief"},
        "MarketAnalyst": {"asset_type": "stock", "market": "nse", "time_horizon": "medium", "analysis_type": "fundamental", "risk_level": "medium", "output_format": "analysis"},
        "Tutor": {"source_topic": "", "difficulty_level": "intermediate", "quiz_required": False, "diagram_required": False, "section_wise_teaching": True},
        "Default": {"goal": "", "profiles_needed": [], "decomposition_needed": False, "approval_required": True, "final_output": ""},
    }
    return templates.get(profile_name, templates["Default"])


# ── New Weighted Router (SOUL.md-aware) ───────────────────────────────

def _signal_score(tokens: list[str], keywords: list[str], weight: float = 1.0) -> tuple[float, list[str]]:
    """Score tokens against keywords, returning (score, matched_keywords)."""
    text = " ".join(tokens)
    matched = []
    score = 0.0
    for kw in keywords:
        kw_lower = kw.lower()
        if " " in kw_lower and kw_lower in text:
            score += 2.0 * weight
            matched.append(kw)
        elif " " not in kw_lower and kw_lower in tokens:
            score += 1.0 * weight
            matched.append(kw)
    return score, matched


def route_profile_v2(task_input: dict) -> dict:
    """SOUL.md-aware routing with weighted signal scoring."""
    title = str(task_input.get("title") or "")
    desc = str(task_input.get("description") or task_input.get("notes") or "")
    trigger = str(task_input.get("trigger_source") or "dashboard")
    action = str(task_input.get("action") or "")
    explicit_override = str(task_input.get("manual_profile") or "").strip()
    settings = get_profile_settings()
    threshold = get_routing_threshold()

    # 1. Explicit Kishore override
    if explicit_override and explicit_override in PROFILE_KEYWORDS:
        return {
            "selected_profile": explicit_override,
            "confidence": 1.0,
            "reason": f"Kishore explicitly selected {explicit_override}.",
            "matched_signals": ["manual_override"],
            "alternates": [],
            "mode": "manual",
            "overridden_by": "Kishore",
        }

    # 2. Task-level assigned profile
    task_profile = str(task_input.get("profile") or str(task_input.get("assignee") or "")).strip()
    if task_profile and task_profile in PROFILE_KEYWORDS and task_profile != "Default":
        return {
            "selected_profile": task_profile,
            "confidence": 0.95,
            "reason": f"Task-level profile set to {task_profile}.",
            "matched_signals": ["task_assigned"],
            "alternates": [],
            "mode": "task_assigned",
        }

    # 3. Auto-router with SOUL.md signals
    text = f"{title} {desc} {trigger} {action}"
    tokens = _tokenize(text)

    # Load SOUL.md routing index
    index = get_routing_index()
    all_signals = {}
    all_matched = {}

    for profile_name in ["Coder", "ContentCreator", "DeepResearch", "MarketAnalyst", "Tutor", "Default"]:
        idx = index.get(profile_name, {})
        total = 0.0
        signals = []

        # Strong keywords (from SOUL.md identity/mission/expertise)
        s, m = _signal_score(tokens, idx.get("strong_keywords", []), weight=2.0)
        total += s
        if m: signals.extend([f"strong:{x}" for x in m[:6]])

        # Weak keywords
        s2, m2 = _signal_score(tokens, idx.get("weak_keywords", []), weight=0.5)
        total += s2
        if m2: signals.extend([f"weak:{x}" for x in m2[:3]])

        # Task patterns (regex)
        for pat in idx.get("task_patterns", []):
            if re.search(pat, text, re.IGNORECASE):
                total += 1.5
                signals.append(f"pattern_match")

        # Legacy keyword matching (from PROFILE_KEYWORDS)
        s3, m3 = _signal_score(tokens, PROFILE_KEYWORDS.get(profile_name, {}).get("primary", []), weight=0.8)
        total += s3
        if m3: signals.extend([f"keyword:{x}" for x in m3[:4]])

        # Best-for match
        if idx.get("best_for"):
            for area in idx["best_for"]:
                if any(word.lower() in text for word in area.lower().split()[:3]):
                    total += 0.3
                    signals.append(f"expertise:{area}")

        all_signals[profile_name] = total
        all_matched[profile_name] = list(dict.fromkeys(signals))

    # Find best profile
    best_profile = "Default"
    best_score = 0.0
    for profile_name, score in all_signals.items():
        if score > best_score:
            best_score = score
            best_profile = profile_name

    # Check for multi-profile pattern
    multi = _detect_multi_profile(tokens, all_signals)
    if multi:
        top_scores = sorted(all_signals.values(), reverse=True)
        if len(top_scores) >= 2 and top_scores[0] > top_scores[1] * 3.0:
            pass  # Lead dominates, use single
        else:
            return {
                "selected_profile": multi[0]["profile"] if multi else best_profile,
                "confidence": min(round(best_score / (best_score + 3), 2), 0.92),
                "reason": f"Multi-profile task detected. Lead: {multi[0]['profile'] if multi else best_profile}.",
                "matched_signals": all_matched.get(best_profile, [])[:8],
                "alternates": [{"profile": m["profile"], "confidence": round(all_signals.get(m["profile"], 0) / max(all_signals.values(), default=1), 2), "reason": m["task"]} for m in (multi or [])[1:3]],
                "mode": "multi_profile",
                "steps": multi,
            }

    # Low confidence fallback
    if best_score < 0.3:
        return {
            "selected_profile": "Default",
            "confidence": 0.3,
            "reason": "No strong profile match detected. Using Default dispatcher.",
            "matched_signals": [],
            "alternates": [],
            "mode": "auto",
        }

    # Build alternates
    alts = sorted(
        [(p, s) for p, s in all_signals.items() if p != best_profile and s > 0.2],
        key=lambda x: x[1], reverse=True,
    )
    alternates = [{"profile": a[0], "confidence": round(a[1] / max(all_signals.values(), default=1), 2), "reason": _build_routing_reason_v2(a[0], tokens, index)} for a in alts[:2]]
    confidence = min(round(best_score / (best_score + 3), 2), 0.95)

    idx = index.get(best_profile, {})
    reason = f"Task matches {best_profile} profile. " + (_build_routing_reason_v2(best_profile, tokens, index) or f"Best match: {best_profile}.")

    return {
        "selected_profile": best_profile,
        "confidence": confidence,
        "reason": reason,
        "matched_signals": all_matched.get(best_profile, [])[:8],
        "alternates": alternates,
        "mode": "auto",
        "threshold_passed": confidence >= threshold.get("auto_accept_above", 0.7),
    }


def _build_routing_reason_v2(profile: str, tokens: list[str], index: dict) -> str:
    """Build human-readable routing reason using SOUL.md index."""
    idx = index.get(profile, {})
    best_for = idx.get("best_for", [])
    mission = idx.get("mission", [])
    text = " ".join(tokens)

    # Check best_for match
    for area in best_for:
        if any(word.lower() in text for word in area.lower().split()[:3]):
            return f"Matches {profile} expertise: {area}."

    # Check mission bullet match
    for item in mission[:3]:
        words = [w for w in item.lower().split() if len(w) > 3]
        if any(w in tokens for w in words[:2]):
            return f"Aligns with {profile} mission: {item[:80]}."

    return f"Best match: {profile} profile."


# ── Routing Threshold Settings ────────────────────────────────────────

def _default_threshold() -> dict:
    return {"auto_accept_above": 0.7, "ask_between_min": 0.45, "ask_between_max": 0.7, "fallback_below": 0.45, "last_updated": now_iso()}


def get_routing_threshold() -> dict:
    if not ROUTING_THRESHOLD.exists():
        t = _default_threshold()
        write_json(ROUTING_THRESHOLD, t)
        return t
    return read_json(ROUTING_THRESHOLD, _default_threshold())


def save_routing_threshold(payload: dict) -> dict:
    current = get_routing_threshold()
    for k in ["auto_accept_above", "ask_between_min", "ask_between_max", "fallback_below"]:
        v = payload.get(k)
        if v is not None and isinstance(v, (int, float)):
            current[k] = round(float(v), 2)
    current["last_updated"] = now_iso()
    write_json(ROUTING_THRESHOLD, current)
    return current


# ── Multi-Profile Sub-Task Orchestration ──────────────────────────────

def decompose_task(payload: dict) -> dict:
    """Decompose a task into subtasks across profiles."""
    title = str(payload.get("title") or "Multi-profile task")
    routing = route_profile_v2(payload)

    if routing.get("mode") != "multi_profile":
        return {"ok": False, "error": "Task is not multi-profile", "routing": routing}

    steps = routing.get("steps") or []
    parent_task = save_task({"title": title, "status": "in_progress", "assignee": routing.get("selected_profile", "Default"), "priority": "high", "notes": f"Multi-profile orchestration: {', '.join(s.get('profile','') for s in steps)}", "subtask_ids": []})

    parent_id = parent_task.get("id", "")
    subtasks = []
    for i, step in enumerate(steps):
        st = save_task({
            "title": step.get("task", f"Subtask {i+1}: {title}"),
            "status": "queued",
            "assignee": step.get("profile", "Default"),
            "priority": "high",
            "notes": f"Subtask of {parent_id}",
            "parent_id": parent_id,
            "depends_on": steps[i-1].get("profile") if i > 0 else "",
            "order": i + 1,
        })
        subtasks.append(st)

    # Update parent with subtask IDs
    parent_task["subtask_ids"] = [s.get("id") for s in subtasks]
    save_task(parent_task)

    # Create run records for each subtask
    for st in subtasks:
        start_run({
            "title": st.get("title", ""),
            "trigger_source": "api",
            "service": "mission-control",
            "profile": st.get("assignee", "Default"),
            "current_step": "queued",
            "related_task_id": st.get("id", ""),
            "input": {"parent_task_id": parent_id, "subtask_order": st.get("order", 1)},
        })

    return {
        "ok": True,
        "parent_task": parent_task,
        "subtasks": subtasks,
        "routing": routing,
    }


# ── Multi-Profile Workflow Orchestrator ────────────────────────────────

WORKFLOW_STATUSES = {"draft", "queued", "running", "paused", "completed", "failed", "cancelled"}
SUBTASK_STATUSES = {"queued", "running", "blocked", "waiting_for_approval", "completed", "failed", "cancelled"}
COORDINATOR_PROFILE = "Default"


def _load_workflows() -> dict[str, dict]:
    """Load all multi-profile workflows keyed by workflow_id."""
    with WORKFLOW_FILE_LOCK:
        return read_json(WORKFLOWS_MULTI_DATA, {})


def _save_workflows(wfs: dict) -> None:
    """Save all multi-profile workflows."""
    with WORKFLOW_FILE_LOCK:
        write_json(WORKFLOWS_MULTI_DATA, wfs)


def _wf_telegram(wf: dict, event: str, extra: str = "") -> None:
    """Send workflow Telegram notification."""
    wf_id = wf.get("workflow_id", "?")
    title = wf.get("title", "Untitled")
    status = wf.get("status", "?")
    coordinator = wf.get("coordinator_profile", "Default")
    subtasks = wf.get("subtasks", [])
    completed = sum(1 for s in subtasks if s.get("status") == "completed")
    total = len(subtasks)

    if event == "workflow_created":
        profiles = ", ".join(s.get("profile", "?") for s in subtasks)
        st_list = "\n".join(f"  {i+1}. [{s.get('profile','?')}] {s.get('title','?')}" for i, s in enumerate(subtasks))
        msg = f"""🔄 *Workflow Created*
*{title}*
Coordinator: {coordinator}
Profiles: {profiles}
Subtasks ({total}):
{st_list}

[Dashboard →]({DASHBOARD_URL}#workflows)"""
    elif event == "workflow_started":
        msg = f"""🚀 *Workflow Started*
*{title}*
Status: {status} · {completed}/{total} subtasks complete
Coordinator: {coordinator}

[Dashboard →]({DASHBOARD_URL}#workflows)"""
    elif event == "subtask_completed":
        msg = f"""✅ *Subtask Completed*
Workflow: *{title}*
{extra}
Progress: {completed}/{total}

[Dashboard →]({DASHBOARD_URL}#workflows)"""
    elif event == "subtask_failed":
        msg = f"""❌ *Subtask Failed*
Workflow: *{title}*
{extra}
Progress: {completed}/{total}

[Dashboard →]({DASHBOARD_URL}#workflows)"""
    elif event == "subtask_rerouted":
        msg = f"""🔄 *Subtask Rerouted*
Workflow: *{title}*
{extra}

[Dashboard →]({DASHBOARD_URL}#workflows)"""
    elif event == "synthesis_ready":
        msg = f"""📋 *Final Synthesis Ready*
Workflow: *{title}*
{completed}/{total} subtasks completed
{extra}

[Dashboard →]({DASHBOARD_URL}#workflows)"""
    else:
        return

    # Fire-and-forget to avoid blocking HTTP handler
    threading.Thread(target=lambda: _send_telegram(msg), daemon=True).start()
    wf.setdefault("telegram_updates", []).append({"event": event, "sent_at": now_iso(), "ok": True})
    _save_workflow(wf)


def _subtask_title(profile: str, parent_title: str) -> str:
    """Generate a meaningful subtask title based on profile and parent task."""
    profile_tasks = {
        "DeepResearch": f"Research: {parent_title}",
        "ContentCreator": f"Create content: {parent_title}",
        "MarketAnalyst": f"Analyze market: {parent_title}",
        "Coder": f"Implement: {parent_title}",
        "Tutor": f"Teach: {parent_title}",
        "Default": f"Coordinate: {parent_title}",
    }
    return profile_tasks.get(profile, f"{profile}: {parent_title}")


def _subtask_output_required(profile: str) -> str:
    """Return the expected output type for a profile."""
    outputs = {
        "DeepResearch": "research brief with findings",
        "ContentCreator": "content plan with drafts",
        "MarketAnalyst": "market analysis with recommendations",
        "Coder": "implementation with verification",
        "Tutor": "lesson with quiz/diagram",
        "Default": "synthesis and next actions",
    }
    return outputs.get(profile, "completed task output")


def create_workflow(payload: dict) -> dict:
    """Create a multi-profile workflow with parent task and subtasks."""
    title = str(payload.get("title") or "Multi-profile workflow")
    description = str(payload.get("description") or "")
    wf_id = uuid.uuid4().hex[:12]
    coordinator = str(payload.get("coordinator_profile") or COORDINATOR_PROFILE)

    # ── Pre-defined subtasks (from dashboard acceptance tests) ──
    predefined = payload.get("subtasks")
    if predefined and isinstance(predefined, list) and len(predefined) > 0:
        subtasks = []
        for i, st_payload in enumerate(predefined):
            deps = list(st_payload.get("depends_on") or [])
            st_profile = str(st_payload.get("profile") or "Default")
            st_title = str(st_payload.get("title") or f"Subtask {i+1}")
            has_deps = bool(deps)
            subtasks.append({
                "id": st_payload.get("id") or uuid.uuid4().hex[:8],
                "profile": st_profile,
                "title": st_title,
                "depends_on": deps,
                "status": "waiting" if has_deps else "queued",
                "output_required": _subtask_output_required(st_profile),
                "output": None, "error": None, "run_id": None,
                "started_at": None, "completed_at": None, "retries": 0,
                "timeout_seconds": int(st_payload.get("timeout_seconds") or 120),
                "retry_policy": st_payload.get("retry_policy") or {"retry_count": 1, "retry_delay_seconds": 10, "retry_on": ["timeout", "failed", "provider_error", "rate_limited", "nonzero_exit"]},
                "max_retries": int((st_payload.get("retry_policy") or {}).get("retry_count", st_payload.get("max_retries", 1)) or 0),
                "retry_delay_seconds": int((st_payload.get("retry_policy") or {}).get("retry_delay_seconds", st_payload.get("retry_delay_seconds", 10)) or 0),
                "retry_on": list((st_payload.get("retry_policy") or {}).get("retry_on", st_payload.get("retry_on", ["timeout", "failed", "provider_error", "rate_limited", "nonzero_exit"])) or []),
                "failure_reason": None,
                "dispatch_id": None,
                "pid": None,
                "process_status": "queued",
                "attempt_history": [],
                "stdout_tail": [],
                "stderr_tail": [],
                "last_output_chunk": "",
                "last_error_chunk": "",
                "test_mode": str(st_payload.get("test_mode") or ""),
                "prompt": str(st_payload.get("prompt") or ""),
                "order": i + 1,
            })

        routing = {
            "mode": "multi_profile",
            "selected_profile": coordinator,
            "confidence": 1.0,
            "reason": "Pre-defined subtasks from dashboard",
            "matched_signals": ["manual"],
            "alternates": [],
            "steps": [{"profile": s["profile"], "task": s["title"]} for s in subtasks],
        }

        wf = {
            "workflow_id": wf_id, "title": title, "description": description,
            "coordinator_profile": coordinator, "mode": "multi_profile",
            "status": "draft", "subtasks": subtasks, "final_synthesis": None,
            "created_at": now_iso(), "updated_at": now_iso(),
            "started_at": None, "completed_at": None,
            "routing": routing, "telegram_updates": [], "runs": [],
        }

        _save_workflow(wf)
        _wf_telegram(wf, "workflow_created")
        append_action_log({"service": "mission-control", "action": "create_workflow",
                           "risk": "safe", "status": "success",
                           "output": f"Created workflow {wf_id}: {title} ({len(predefined)} pre-defined subtasks)"})
        return {"ok": True, "workflow": wf}

    # ── Auto-detect from title/description (legacy routing) ──
    routing = route_profile_v2({"title": title, "description": description, "trigger_source": "dashboard"})
    steps = routing.get("steps") or []

    # If router didn't detect multi-profile, force decomposition
    if not steps:
        multi = _detect_multi_profile(_tokenize(title + " " + description), {})
        if multi:
            steps = multi
            routing["mode"] = "multi_profile"
            routing["steps"] = steps

    # If still no multi-profile, create single-profile workflow
    if not steps:
        steps = [{"profile": routing.get("selected_profile", "Default"), "task": title}]
        routing["mode"] = "single_profile"

    # Build subtasks with dependencies
    subtasks = []
    for i, step in enumerate(steps):
        depends = []
        if i > 0:
            depends.append(steps[i - 1].get("profile", "Default"))
        step_title = _subtask_title(step.get("profile", "Default"), title)
        st = {
            "id": uuid.uuid4().hex[:8],
            "profile": step.get("profile", "Default"),
            "title": step_title,
            "depends_on": depends,
            "status": "blocked" if depends else "queued",
            "output_required": _subtask_output_required(step.get("profile", "Default")),
            "output": None,
            "error": None,
            "run_id": None,
            "started_at": None,
            "completed_at": None,
            "retries": 0,
            "timeout_seconds": int(step.get("timeout_seconds") or 120),
            "retry_policy": step.get("retry_policy") or {"retry_count": 1, "retry_delay_seconds": 10, "retry_on": ["timeout", "failed", "provider_error", "rate_limited", "nonzero_exit"]},
            "max_retries": int((step.get("retry_policy") or {}).get("retry_count", step.get("max_retries", 1)) or 0),
            "retry_delay_seconds": int((step.get("retry_policy") or {}).get("retry_delay_seconds", step.get("retry_delay_seconds", 10)) or 0),
            "retry_on": list((step.get("retry_policy") or {}).get("retry_on", step.get("retry_on", ["timeout", "failed", "provider_error", "rate_limited", "nonzero_exit"])) or []),
            "failure_reason": None,
            "dispatch_id": None,
            "pid": None,
            "process_status": "queued",
            "attempt_history": [],
            "stdout_tail": [],
            "stderr_tail": [],
            "last_output_chunk": "",
            "last_error_chunk": "",
            "test_mode": str(step.get("test_mode") or ""),
            "prompt": str(step.get("prompt") or ""),
            "order": i + 1,
        }
        subtasks.append(st)

    wf = {
        "workflow_id": wf_id,
        "title": title,
        "description": description,
        "coordinator_profile": coordinator,
        "mode": routing.get("mode", "multi_profile"),
        "status": "draft",
        "subtasks": subtasks,
        "final_synthesis": None,
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "started_at": None,
        "completed_at": None,
        "routing": routing,
        "telegram_updates": [],
        "runs": [],
    }

    # Persist
    wfs = _load_workflows()
    wfs[wf_id] = wf
    _save_workflows(wfs)

    # Notify
    _wf_telegram(wf, "workflow_created")
    append_action_log({"service": "mission-control", "action": "create_workflow", "risk": "safe",
                       "status": "success", "output": f"Created workflow {wf_id}: {title}"})

    return {"ok": True, "workflow": wf}


def get_workflows(status_filter: str = "") -> list[dict]:
    """List all multi-profile workflows, optionally filtered by status."""
    wfs = _load_workflows()
    out = list(wfs.values())
    if status_filter:
        out = [w for w in out if w.get("status") == status_filter]
    out.sort(key=lambda w: w.get("created_at", ""), reverse=True)
    return out


def get_workflow(wf_id: str) -> dict | None:
    """Get a single workflow by ID."""
    wfs = _load_workflows()
    return wfs.get(wf_id)


def _save_workflow(wf: dict) -> dict:
    """Save a single workflow update."""
    wf["updated_at"] = now_iso()
    with WORKFLOW_FILE_LOCK:
        wfs = read_json(WORKFLOWS_MULTI_DATA, {})
        wfs[wf["workflow_id"]] = wf
        write_json(WORKFLOWS_MULTI_DATA, wfs)
    return wf


def start_workflow(wf_id: str, payload: dict = None) -> dict:
    """Start a workflow — set to running, start first unblocked subtask."""
    wf = get_workflow(wf_id)
    if not wf:
        return {"ok": False, "error": "Workflow not found"}
    if wf.get("status") not in {"draft", "paused"}:
        return {"ok": False, "error": f"Workflow is {wf.get('status')}, cannot start"}

    wf["status"] = "running"
    wf["started_at"] = now_iso()

    # Start queued subtasks that aren't blocked
    started = []
    for st in wf.get("subtasks", []):
        if st.get("status") == "queued":
            st["status"] = "running"
            st["started_at"] = now_iso()
            # Create run record
            run = start_run({
                "title": st["title"],
                "trigger_source": "workflow",
                "service": "mission-control",
                "profile": st["profile"],
                "current_step": "executing",
                "related_task_id": st["id"],
                "input": {"workflow_id": wf_id, "subtask_id": st["id"]},
            })
            st["run_id"] = run.get("run_id")
            started.append(st)

    wf = _save_workflow(wf)
    _wf_telegram(wf, "workflow_started")

    return {"ok": True, "workflow": wf, "started_subtasks": len(started)}


def pause_workflow(wf_id: str, payload: dict = None) -> dict:
    """Pause a running workflow."""
    wf = get_workflow(wf_id)
    if not wf:
        return {"ok": False, "error": "Workflow not found"}
    if wf.get("status") != "running":
        return {"ok": False, "error": f"Workflow is {wf.get('status')}, cannot pause"}

    wf["status"] = "paused"
    # Pause running subtasks
    for st in wf.get("subtasks", []):
        if st.get("status") == "running":
            st["status"] = "queued"

    wf = _save_workflow(wf)
    return {"ok": True, "workflow": wf}


def start_subtask(wf_id: str, subtask_id: str, payload: dict = None) -> dict:
    """Start a specific subtask."""
    wf = get_workflow(wf_id)
    if not wf:
        return {"ok": False, "error": "Workflow not found"}

    st = next((s for s in wf.get("subtasks", []) if s.get("id") == subtask_id), None)
    if not st:
        return {"ok": False, "error": "Subtask not found"}

    # Check dependencies
    for dep in st.get("depends_on", []):
        dep_st = next((s for s in wf.get("subtasks", []) if s.get("profile") == dep), None)
        if dep_st and dep_st.get("status") != "completed":
            return {"ok": False, "error": f"Dependency not met: {dep} is {dep_st.get('status')}"}

    if st.get("status") not in {"queued", "blocked", "failed"}:
        return {"ok": False, "error": f"Subtask is {st.get('status')}, cannot start"}

    st["status"] = "running"
    st["started_at"] = now_iso()
    st["retries"] = st.get("retries", 0)

    # Create run record
    run = start_run({
        "title": st["title"],
        "trigger_source": "workflow",
        "service": "mission-control",
        "profile": st["profile"],
        "current_step": "executing",
        "related_task_id": st["id"],
        "input": {"workflow_id": wf_id, "subtask_id": st["id"]},
    })
    st["run_id"] = run.get("run_id")

    # Also update parent workflow status
    if wf.get("status") in {"draft", "paused"}:
        wf["status"] = "running"

    wf = _save_workflow(wf)
    return {"ok": True, "workflow": wf, "subtask": st}


def complete_subtask(wf_id: str, subtask_id: str, payload: dict = None) -> dict:
    """Mark a subtask as completed, unblock dependents."""
    payload = payload or {}
    wf = get_workflow(wf_id)
    if not wf:
        return {"ok": False, "error": "Workflow not found"}

    st = next((s for s in wf.get("subtasks", []) if s.get("id") == subtask_id), None)
    if not st:
        return {"ok": False, "error": "Subtask not found"}

    output = payload.get("output") or {"result": f"Completed by {st.get('profile')}"}
    st["status"] = "completed"
    st["process_status"] = "completed"
    st["completed_at"] = now_iso()
    st["end_time"] = st.get("end_time") or st["completed_at"]
    st["output"] = output
    st["error"] = None
    st["failure_reason"] = None

    # Finish the run
    if st.get("run_id"):
        finish_run(st["run_id"], {"status": "succeeded", "output": output})

    # Unblock subtasks that depend on this profile
    unblocked = 0
    for other in wf.get("subtasks", []):
        if st["profile"] in other.get("depends_on", []) and other.get("status") == "blocked":
            # Check all dependencies
            all_met = True
            for dep in other["depends_on"]:
                dep_st = next((s for s in wf.get("subtasks", []) if s.get("profile") == dep), None)
                if dep_st and dep_st.get("status") != "completed":
                    all_met = False
                    break
            if all_met:
                # Start it if workflow is running
                other["status"] = "running" if wf.get("status") == "running" else "queued"
                other["started_at"] = now_iso()
                unblocked += 1
                # Create run record
                run = start_run({
                    "title": other["title"],
                    "trigger_source": "workflow",
                    "service": "mission-control",
                    "profile": other["profile"],
                    "current_step": "executing",
                    "related_task_id": other["id"],
                    "input": {"workflow_id": wf_id, "subtask_id": other["id"]},
                })
                other["run_id"] = run.get("run_id")

    wf = _save_workflow(wf)
    _wf_telegram(wf, "subtask_completed", f"Subtask: {st['title']}\nProfile: {st['profile']}")

    return {"ok": True, "workflow": wf, "subtask": st, "unblocked": unblocked}


def fail_subtask(wf_id: str, subtask_id: str, payload: dict = None) -> dict:
    """Mark a subtask as failed."""
    payload = payload or {}
    wf = get_workflow(wf_id)
    if not wf:
        return {"ok": False, "error": "Workflow not found"}

    st = next((s for s in wf.get("subtasks", []) if s.get("id") == subtask_id), None)
    if not st:
        return {"ok": False, "error": "Subtask not found"}
    if st.get("status") == "skipped":
        return {"ok": True, "workflow": wf, "subtask": st, "message": "Subtask already skipped; stale failure ignored"}

    error = payload.get("error") or {"message": "Subtask failed"}
    failure_reason = str(payload.get("failure_reason") or error.get("failure_reason") or st.get("failure_reason") or "unknown_error")
    error["failure_reason"] = failure_reason
    st["status"] = payload.get("status") or st.get("status") if st.get("status") in {"timed_out", "cancelled", "retry_exhausted"} else "failed"
    st["process_status"] = st["status"]
    st["failure_reason"] = failure_reason
    st["error"] = error
    st["completed_at"] = now_iso()
    st["end_time"] = st.get("end_time") or st["completed_at"]
    if st.get("started_at") and not st.get("duration_seconds"):
        try:
            st["duration_seconds"] = int(datetime.fromisoformat(st["completed_at"]).timestamp() - datetime.fromisoformat(st["started_at"]).timestamp())
        except Exception:
            pass
    wf["status"] = "cancelled" if failure_reason == "cancelled" else "failed"
    wf["failure_reason"] = failure_reason

    # Finish run as failed
    if st.get("run_id"):
        finish_run(st["run_id"], {"status": "failed", "error": error})

    wf = _save_workflow(wf)
    _wf_telegram(wf, "subtask_failed",
                 f"Subtask: {st['title']}\nProfile: {st['profile']}\nError: {error.get('message', str(error)[:120])}")

    return {"ok": True, "workflow": wf, "subtask": st}


def retry_subtask(wf_id: str, subtask_id: str, payload: dict = None) -> dict:
    """Retry a failed subtask."""
    wf = get_workflow(wf_id)
    if not wf:
        return {"ok": False, "error": "Workflow not found"}

    st = next((s for s in wf.get("subtasks", []) if s.get("id") == subtask_id), None)
    if not st:
        return {"ok": False, "error": "Subtask not found"}
    if st.get("status") != "failed":
        return {"ok": False, "error": f"Subtask is {st.get('status')}, not failed"}

    st.setdefault("resume_history", []).append({"mode": "manual_retry", "previous_dispatch_id": st.get("dispatch_id"), "retried_at": now_iso(), "status_before": st.get("status"), "failure_reason": st.get("failure_reason")})
    st["status"] = "queued"
    st["process_status"] = "queued"
    st["error"] = None
    st["failure_reason"] = None
    st["retries"] = st.get("retries", 0) + 1
    st["run_id"] = None
    st["dispatch_id"] = None
    st["started_at"] = None
    st["completed_at"] = None
    st["end_time"] = None

    if wf.get("status") == "failed":
        wf["status"] = "running"

    wf = _save_workflow(wf)
    return {"ok": True, "workflow": wf, "subtask": st}


def reroute_subtask(wf_id: str, subtask_id: str, payload: dict = None) -> dict:
    """Reroute a subtask to a different profile."""
    payload = payload or {}
    wf = get_workflow(wf_id)
    if not wf:
        return {"ok": False, "error": "Workflow not found"}

    st = next((s for s in wf.get("subtasks", []) if s.get("id") == subtask_id), None)
    if not st:
        return {"ok": False, "error": "Subtask not found"}

    new_profile = str(payload.get("profile") or "").strip()
    if new_profile not in PROFILE_KEYWORDS:
        return {"ok": False, "error": f"Invalid profile: {new_profile}"}

    old_profile = st["profile"]
    st["profile"] = new_profile
    st["status"] = "queued" if st.get("status") != "completed" else st["status"]
    st["run_id"] = None

    wf = _save_workflow(wf)
    _wf_telegram(wf, "subtask_rerouted",
                 f"Subtask: {st['title']}\nFrom: {old_profile} → To: {new_profile}")

    return {"ok": True, "workflow": wf, "subtask": st, "from": old_profile, "to": new_profile}


def synthesize_workflow(wf_id: str, payload: dict = None) -> dict:
    """Create final synthesized output from all subtask results."""
    payload = payload or {}
    wf = get_workflow(wf_id)
    if not wf:
        return {"ok": False, "error": "Workflow not found"}

    subtasks = wf.get("subtasks", [])
    completed_sts = [s for s in subtasks if s.get("status") == "completed"]
    failed_sts = [s for s in subtasks if s.get("status") in {"failed", "timed_out", "retry_exhausted", "cancelled"}]
    total = len(subtasks)

    # Build synthesis from subtask outputs
    outputs = []
    for st in subtasks:
        outputs.append({
            "subtask_id": st["id"],
            "profile": st["profile"],
            "title": st["title"],
            "status": st["status"],
            "output": st.get("output"),
            "error": st.get("error"),
            "failure_reason": st.get("failure_reason"),
            "dispatch_id": st.get("dispatch_id"),
            "retry_attempt": st.get("retry_attempt", st.get("retries", 0)),
            "timeout_seconds": st.get("timeout_seconds"),
            "exit_code": st.get("exit_code"),
        })

    synthesis = {
        "generated_at": now_iso(),
        "coordinator": wf.get("coordinator_profile", "Default"),
        "workflow_title": wf.get("title"),
        "total_subtasks": total,
        "completed": len(completed_sts),
        "failed": len(failed_sts),
        "outputs": outputs,
        "summary": f"Workflow '{wf.get('title')}' completed with {len(completed_sts)}/{total} subtasks successful.",
        "next_action": "Review outputs above and mark workflow as completed or retry failed subtasks.",
        "status": "needs_review" if completed_sts else "incomplete",
    }

    # If all complete, mark workflow
    if len(completed_sts) == total:
        wf["status"] = "completed"
        wf["completed_at"] = now_iso()
        synthesis["status"] = "completed"
        synthesis["summary"] = f"Workflow '{wf.get('title')}' fully completed with all {total} subtasks successful."

    wf["final_synthesis"] = synthesis
    wf = _save_workflow(wf)
    _wf_telegram(wf, "synthesis_ready",
                 f"{len(completed_sts)}/{total} complete · Status: {synthesis['status']}")

    return {"ok": True, "workflow": wf, "synthesis": synthesis}


def _build_routing_reason(profile: str, tokens: list[str]) -> str:
    """Build a human-readable routing reason."""
    keywords = PROFILE_KEYWORDS.get(profile, {}).get("primary", [])[:15]
    text = " ".join(tokens)
    matched = [kw for kw in keywords if ((" " in kw and kw in text) or (" " not in kw and kw in tokens))]
    if matched:
        return f"Task mentions: {', '.join(matched[:4])}."
    return f"Best match: {profile} profile."


# ── Profile settings persistence ──────────────────────────────────────

def _default_profile_settings() -> dict:
    return {
        "profile_mode": "auto",
        "default_profile": "Default",
        "routing_hints": {p: list(k["primary"][:8]) for p, k in PROFILE_KEYWORDS.items()},
        "last_updated": now_iso(),
    }


def get_profile_settings() -> dict:
    if not PROFILE_SETTINGS.exists():
        settings = _default_profile_settings()
        write_json(PROFILE_SETTINGS, settings)
        return settings
    return read_json(PROFILE_SETTINGS, _default_profile_settings())


def save_profile_settings(payload: dict) -> dict:
    settings = get_profile_settings()
    mode = str(payload.get("profile_mode") or settings.get("profile_mode", "auto"))
    if mode in {"auto", "manual"}:
        settings["profile_mode"] = mode
    default_prof = str(payload.get("default_profile") or "")
    if default_prof in PROFILE_KEYWORDS:
        settings["default_profile"] = default_prof
    settings["last_updated"] = now_iso()
    write_json(PROFILE_SETTINGS, settings)
    return settings


# ── Routing history ───────────────────────────────────────────────────

def append_routing_history(entry: dict):
    ROUTING_HISTORY.parent.mkdir(parents=True, exist_ok=True)
    entry.setdefault("timestamp", now_iso())
    with ROUTING_HISTORY.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, default=str) + "\n")


def get_routing_history(limit: int = 50) -> list[dict]:
    if not ROUTING_HISTORY.exists():
        return []
    lines = ROUTING_HISTORY.read_text(encoding="utf-8", errors="replace").splitlines()[-limit:]
    out = []
    for line in reversed(lines):
        try:
            out.append(json.loads(line))
        except Exception:
            continue
    return out


# ── Profile switch for runs ──────────────────────────────────────────

def switch_run_profile(run_id: str, payload: dict) -> dict:
    run = _find_run(run_id)
    if not run:
        return {"ok": False, "error": "Run not found"}
    new_profile = str(payload.get("profile") or "").strip()
    if new_profile not in PROFILE_KEYWORDS:
        return {"ok": False, "error": f"Invalid profile: {new_profile}"}
    current_status = run.get("status", "")
    old_profile = run.get("profile", run.get("selected_profile", "Default"))

    # Handle based on current status
    if current_status in {"running", "in_progress"}:
        action = str(payload.get("switch_action") or "confirm")
        if action == "cancel_and_restart":
            reason = "Cancel and restart with new profile"
        elif action == "create_followup":
            reason = "Create follow-up task with new profile"
        elif action == "add_helper":
            reason = "Add new profile as helper"
        else:
            return {"ok": False, "error": "Running task requires switch_action: cancel_and_restart, create_followup, or add_helper", "requires_confirmation": True}
    else:
        reason = "Direct switch on non-running task"

    switch_entry = {
        "from": old_profile,
        "to": new_profile,
        "reason": reason,
        "switched_at": now_iso(),
        "run_status_at_switch": current_status,
    }
    history = list(run.get("profile_switch_history") or [])
    history.append(switch_entry)
    patch = {
        "profile": new_profile,
        "selected_profile": new_profile,
        "profile_mode": "manual",
        "recommended_profile": run.get("recommended_profile", old_profile),
        "profile_switch_history": history,
    }
    updated = _update_run(run_id, patch)
    _notify_telegram_run(updated, "profile_switch")
    return {"ok": True, "run_id": run_id, "from": old_profile, "to": new_profile, "reason": reason, "run": updated}

def get_skills() -> list[dict]:
    if not SKILLS_DIR.exists():
        return []
    skills = []
    for item in sorted(SKILLS_DIR.iterdir()):
        if item.name.startswith("."):
            continue
        if item.is_dir():
            skill_md = item / "SKILL.md"
            has_skill_md = skill_md.exists()
            skills.append({
                "name": item.name,
                "type": "skill",
                "has_skill_md": has_skill_md,
                "size": skill_md.stat().st_size if has_skill_md else 0,
                "last_modified": datetime.fromtimestamp(item.stat().st_mtime, timezone.utc).isoformat(timespec="seconds") if item.exists() else "",
                "status": "active" if has_skill_md else "no manifest",
            })
    return skills


def get_plugins() -> list[dict]:
    if not PLUGINS_DIR.exists():
        return []
    plugins = []
    for item in sorted(PLUGINS_DIR.iterdir()):
        if item.name.startswith("."):
            continue
        if item.is_dir():
            plugins.append({
                "name": item.name,
                "status": "active",
                "last_modified": datetime.fromtimestamp(item.stat().st_mtime, timezone.utc).isoformat(timespec="seconds") if item.exists() else "",
            })
    return plugins


# ── WebSocket adapter test ───────────────────────────────────────────

def _run_ws_test() -> dict:
    """Test WebSocket connection to Claw3D adapter on :18789."""
    try:
        import asyncio
        async def _ws():
            import websockets
            async with websockets.connect("ws://127.0.0.1:18789/", open_timeout=5) as ws:
                await ws.send('{"type":"ping"}')
                resp = await asyncio.wait_for(ws.recv(), timeout=3)
                return resp
        result = asyncio.run(_ws())
        return {"ok": True, "action": "test_ws_adapter", "output": f"WebSocket connected. Challenge response: {sanitize_output(str(result), 500)}", "ws_available": True, "protocol": "challenge-response"}
    except Exception as e:
        return {"ok": False, "action": "test_ws_adapter", "output": f"WebSocket test failed: {str(e)[:200]}", "ws_available": False}


# ── Kanban task operations ──────────────────────────────────────────

def _find_task(task_id: str) -> dict | None:
    all_tasks = tasks()
    return next((t for t in all_tasks if str(t.get("id")) == task_id), None)


def _move_task(payload: dict) -> dict:
    task_id = str(payload.get("task_id") or "")
    new_status = str(payload.get("status") or "")
    if not task_id or not new_status:
        return {"ok": False, "error": "task_id and status required"}
    task = _find_task(task_id)
    if not task:
        return {"ok": False, "error": "Task not found"}
    old_status = task.get("status", "unknown")
    task["status"] = new_status
    task["moved_at"] = now_iso()
    task["moved_from"] = old_status
    result = save_task(task)
    return {"ok": True, "action": "move_task", "task": result, "from": old_status, "to": new_status}


def _archive_task(payload: dict) -> dict:
    task_id = str(payload.get("task_id") or "")
    if not task_id:
        return {"ok": False, "error": "task_id required"}
    task = _find_task(task_id)
    if not task:
        return {"ok": False, "error": "Task not found"}
    task["status"] = "archived"
    task["archived_at"] = now_iso()
    result = save_task(task)
    return {"ok": True, "action": "archive_task", "task": result}


def _assign_task(payload: dict) -> dict:
    task_id = str(payload.get("task_id") or "")
    profile = str(payload.get("profile") or "")
    if not task_id or not profile:
        return {"ok": False, "error": "task_id and profile required"}
    task = _find_task(task_id)
    if not task:
        return {"ok": False, "error": "Task not found"}
    task["assignee"] = profile
    task["assigned_at"] = now_iso()
    result = save_task(task)
    return {"ok": True, "action": "assign_task", "task": result}


# ── Nightly uploads ─────────────────────────────────────────────────

UPLOAD_DIR = DATA_DIR / "uploads"


def _upload_nightly_attachment(payload: dict) -> dict:
    """Save base64-encoded attachment to upload dir and link to nightly build."""
    build_id = str(payload.get("build_id") or "")
    filename = safe_text(payload.get("filename") or "attachment", 60).replace("/", "_")
    data_b64 = str(payload.get("data") or "")
    if not build_id or not data_b64:
        return {"ok": False, "error": "build_id and data required"}
    builds = nightly_builds()
    build = next((b for b in builds if str(b.get("id")) == build_id), None)
    if not build:
        return {"ok": False, "error": "Nightly build not found"}
    try:
        raw = __import__("base64").b64decode(data_b64)
    except Exception:
        return {"ok": False, "error": "Invalid base64 data"}
    if len(raw) > 5_000_000:
        return {"ok": False, "error": "File too large (max 5MB)"}
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = f"{build_id}_{filename}"
    filepath = UPLOAD_DIR / safe_name
    filepath.write_bytes(raw)
    screenshots = list(build.get("screenshots") or [])
    entry = {"filename": filename, "path": str(filepath), "size": len(raw), "uploaded_at": now_iso()}
    screenshots.append(entry)
    build["screenshots"] = screenshots[-10:]
    write_json(NIGHTLY_DATA, builds)
    return {"ok": True, "action": "upload_nightly_attachment", "build_id": build_id, "file": entry}


# ── Profile operations ──────────────────────────────────────────────

def _edit_profile(payload: dict) -> dict:
    name = str(payload.get("profile") or "").strip()
    desc = str(payload.get("description") or "").strip()
    if not name or not desc:
        return {"ok": False, "error": "profile and description required"}
    name_lower = name.lower()
    pdir = PROFILES_DIR / name_lower
    if name == "Default" or not pdir.exists():
        return {"ok": False, "error": f"Profile {name} directory not found at {pdir}"}
    soul_path = pdir / "SOUL.md"
    if not soul_path.exists():
        return {"ok": False, "error": f"No SOUL.md found for profile {name}"}
    content = soul_path.read_text(encoding="utf-8")
    # Replace or append description
    desc_line = f"Description: {desc}"
    if "\nDescription:" in content or content.startswith("Description:"):
        content = __import__("re").sub(r"^Description:.*$", desc_line, content, flags=__import__("re").MULTILINE)
    else:
        content = f"{desc_line}\n\n{content}"
    soul_path.write_text(content, encoding="utf-8")
    return {"ok": True, "action": "edit_profile", "profile": name, "description": desc, "path": str(soul_path)}


def _test_profile_routing(payload: dict) -> dict:
    name = str(payload.get("profile") or "").strip()
    if not name:
        return {"ok": False, "error": "profile name required"}
    name_lower = name.lower()
    pdir = PROFILES_DIR / name_lower
    if name == "Default" or not pdir.exists():
        return {"ok": False, "error": f"Profile {name} directory not found"}
    soul_path = pdir / "SOUL.md"
    if not soul_path.exists():
        return {"ok": False, "error": f"No SOUL.md for {name}"}
    # Check basic routing metadata
    content = soul_path.read_text(encoding="utf-8")
    has_trigger = "trigger" in content.lower() or "route" in content.lower()
    size = len(content)
    skills_dir = pdir / "skills"
    has_skills = skills_dir.exists() and any(skills_dir.iterdir())
    return {"ok": True, "action": "test_profile_routing", "profile": name, "soul_size": size, "has_routing_hints": has_trigger, "has_profile_skills": has_skills, "message": f"Profile {name}: SOUL.md {size}B, routing hints: {has_trigger}, local skills: {has_skills}"}


def _reload_profile(payload: dict) -> dict:
    name = str(payload.get("profile") or "").strip()
    if not name:
        return {"ok": False, "error": "profile name required"}
    name_lower = name.lower()
    pdir = PROFILES_DIR / name_lower
    if name == "Default":
        return {"ok": True, "action": "reload_profile", "profile": name, "message": "Default profile is built-in; reload not applicable"}
    if not pdir.exists():
        return {"ok": False, "error": f"Profile {name} directory not found"}
    # Reload: touch SOUL.md timestamp and verify it's readable
    soul_path = pdir / "SOUL.md"
    if not soul_path.exists():
        return {"ok": False, "error": f"No SOUL.md for {name}"}
    soul_path.touch()
    try:
        content = soul_path.read_text(encoding="utf-8")
        return {"ok": True, "action": "reload_profile", "profile": name, "message": f"Profile {name} SOUL.md touched ({len(content)}B). Hermes will pick up on next session.", "verified": True}
    except Exception as e:
        return {"ok": False, "error": f"Failed to read SOUL.md: {e}"}


def list_logs(service: str, lines: int = 120) -> dict:
    service = service if service in SERVICE_ALLOWLIST else "mission-control.service"
    lines = max(20, min(int(lines or 120), 400))
    code, out = run(["journalctl", "-u", service, "-n", str(lines), "--no-pager"], timeout=10)
    return {"service": service, "ok": code == 0, "logs": sanitize_output(out, 30000), "last_checked": now_iso()}


def nightly_builds() -> list[dict]:
    return read_json(NIGHTLY_DATA, [])


def save_nightly_build(payload: dict) -> dict:
    builds = nightly_builds()
    build_id = str(payload.get("id") or uuid.uuid4().hex[:10])
    existing = next((b for b in builds if str(b.get("id")) == build_id), None)
    allowed_statuses = {"Idea", "Built", "Testing", "Needs Fix", "Good Candidate", "Promoted", "Rejected", "Archived"}
    patch = {
        "id": build_id,
        "name": safe_text(payload.get("name") or "Untitled nightly build", 120),
        "date": safe_text(payload.get("date") or now_iso()[:10], 20),
        "problem_solved": safe_text(payload.get("problem_solved") or "", 500),
        "feature_type": safe_text(payload.get("feature_type") or "workflow", 80),
        "linked_files": [safe_text(x, 180) for x in payload.get("linked_files", [])[:12]] if isinstance(payload.get("linked_files"), list) else [],
        "service_affected": safe_text(payload.get("service_affected") or "mission-control", 80),
        "how_to_test": safe_text(payload.get("how_to_test") or "", 500),
        "feedback": safe_text(payload.get("feedback") or "", 1000),
        "bugs": safe_text(payload.get("bugs") or "", 1000),
        "status": payload.get("status") if payload.get("status") in allowed_statuses else "Idea",
        "updated_at": now_iso(),
    }
    # Keep existing test_history and checklist if present
    if existing:
        patch.setdefault("test_history", existing.get("test_history", []))
        patch.setdefault("checklist", existing.get("checklist", {}))
        patch.setdefault("screenshots", existing.get("screenshots", []))
        patch.setdefault("rollback", existing.get("rollback", ""))
    else:
        patch.setdefault("test_history", [])
        patch.setdefault("checklist", {"tests_passed": False, "no_major_errors": False, "documented": False, "rollback_clear": False, "linked_to_feature": False})
        patch.setdefault("screenshots", [])
        patch.setdefault("rollback", "")
    if existing:
        existing.update({k: v for k, v in patch.items() if v not in ("", []) or k in {"status", "updated_at", "checklist", "test_history", "screenshots"}})
        result = existing
    else:
        patch["created_at"] = now_iso()
        builds.insert(0, patch)
        result = patch
    write_json(NIGHTLY_DATA, builds)
    append_action_log({"service": "mission-control", "action": "save_nightly_build", "risk": "safe", "status": "success", "output": f"Saved nightly build {build_id}"})
    return result


def get_nightly_builds_enhanced() -> list[dict]:
    """Return nightly builds with test_history and checklist, enriched with linked runs."""
    builds = nightly_builds()
    all_runs = get_runs(limit=400)
    for build in builds:
        bid = build.get("id", "")
        build["linked_runs"] = [r for r in all_runs if r.get("related_nightly_build_id") == bid][:8]
        build.setdefault("test_history", [])
        build.setdefault("checklist", {"tests_passed": False, "no_major_errors": False, "documented": False, "rollback_clear": False, "linked_to_feature": False})
        build.setdefault("screenshots", [])
        build.setdefault("rollback", "")
    return builds


def tasks() -> list[dict]:
    return read_json(TASKS_DATA, [])


def save_task(payload: dict) -> dict:
    items = tasks()
    task_id = str(payload.get("id") or uuid.uuid4().hex[:10])
    existing = next((t for t in items if str(t.get("id")) == task_id), None)
    patch = {"id": task_id, "title": safe_text(payload.get("title") or "Untitled task", 160), "status": safe_text(payload.get("status") or "draft", 40), "assignee": safe_text(payload.get("assignee") or "Hermes", 80), "priority": safe_text(payload.get("priority") or "normal", 40), "notes": safe_text(payload.get("notes") or "", 1000), "updated_at": now_iso()}
    if existing:
        existing.update(patch)
        result = existing
    else:
        patch["created_at"] = now_iso()
        items.insert(0, patch)
        result = patch
    write_json(TASKS_DATA, items)
    append_action_log({"service": "mission-control", "action": "save_task", "risk": "safe", "status": "success", "output": f"Saved task {task_id}"})
    return result


def execute_safe_action(action: str, payload: dict) -> dict:
    if action == "refresh_all_status":
        return {"ok": True, "action": action, "data": service_inventory()}
    if action == "view_service_logs":
        return {"ok": True, "action": action, **list_logs(str(payload.get("service") or "mission-control.service"), int(payload.get("lines") or 120))}
    if action == "test_adapter":
        probe = http_probe("http://127.0.0.1:18789/")
        return {"ok": bool(probe.get("ok")), "action": action, "output": probe.get("summary"), "probe": probe}
    if action == "export_status_report":
        return {"ok": True, "action": action, "report": api_status(include_heavy=False)}
    if action == "create_task" or action == "update_task":
        return {"ok": True, "action": action, "task": save_task(payload)}
    if action == "create_nightly_build" or action == "update_nightly_build":
        return {"ok": True, "action": action, "build": save_nightly_build(payload)}
    if action == "open_output":
        job_id = str(payload.get("job_id") or "")
        path = latest_output_file(job_id)
        if not path:
            return {"ok": False, "error": "No output file found for this job"}
        return {"ok": True, "action": action, "job_id": job_id, "path": str(path), "content": sanitize_output(path.read_text(encoding="utf-8", errors="replace"), 12000)}
    if action == "fix_prompt":
        job_id = str(payload.get("job_id") or "")
        job = find_job(job_id)
        if not job:
            return {"ok": False, "error": "Unknown job_id"}
        path = latest_output_file(job_id)
        excerpt = sanitize_output(path.read_text(encoding="utf-8", errors="replace"), 6000) if path else ""
        return {"ok": True, "action": action, "job_id": job_id, "prompt": build_fix_prompt(job, excerpt)}
    if action == "test_ws_adapter":
        return _run_ws_test()
    if action == "move_task":
        return _move_task(payload)
    if action == "archive_task":
        return _archive_task(payload)
    if action == "assign_task":
        return _assign_task(payload)
    if action == "upload_nightly_attachment":
        return _upload_nightly_attachment(payload)
    if action == "edit_profile":
        return _edit_profile(payload)
    if action == "test_profile_routing":
        return _test_profile_routing(payload)
    if action == "create_workflow":
        return create_workflow(payload)
    if action == "synthesize_workflow":
        return synthesize_workflow(str(payload.get("workflow_id") or ""))
    if action == "retry_dispatch":
        return dispatch_retry(str(payload.get("dispatch_id") or ""))
    if action == "cancel_dispatch":
        return dispatch_cancel(str(payload.get("dispatch_id") or ""))
    return {"ok": False, "error": "Unsupported safe action"}


def execute_medium_action(action: str, payload: dict) -> dict:
    job_id = str(payload.get("job_id") or "")
    if action in {"run_cron", "pause_cron", "resume_cron"}:
        if not find_job(job_id):
            return {"ok": False, "error": "Unknown job_id"}
        cmd = {"run_cron": ["hermes", "cron", "run", job_id], "pause_cron": ["hermes", "cron", "pause", job_id], "resume_cron": ["hermes", "cron", "resume", job_id]}[action]
        code, out = run(cmd, timeout=60)
        return {"ok": code == 0, "action": action, "job_id": job_id, "output": sanitize_output(out, 6000)}
    if action == "send_telegram_summary":
        p = subprocess.run(["hermes", "send", "--to", "telegram", "--subject", "[Mission Control]"], input=cron_summary_text(), text=True, capture_output=True, timeout=60)
        return {"ok": p.returncode == 0, "action": action, "output": sanitize_output((p.stdout + p.stderr).strip(), 4000)}
    if action == "restart_service":
        service = str(payload.get("service") or "")
        if service not in SAFE_SYSTEMD_RESTARTS:
            return {"ok": False, "error": "Service restart not allowed from Mission Control"}
        code, out = run(["systemctl", "restart", service], timeout=30)
        active = service_status(service)
        return {"ok": code == 0 and active.get("ok"), "action": action, "service": service, "output": out, "status": active}
    if action == "run_claw3d_standup":
        probe = http_probe("http://127.0.0.1:3000/api/office/standup/meeting")
        return {"ok": bool(probe.get("ok")), "action": action, "output": "Claw3D standup endpoint checked. Full run payload contract requires next integration pass.", "probe": probe}
    if action == "reload_profile":
        return _reload_profile(payload)
    if action == "dispatch_workflow" or action == "dispatch_subtask":
        return enqueue_dispatch(payload)
    return {"ok": False, "error": "Unsupported medium action"}


def run_action(action: str, payload: dict, force: bool = False) -> dict:
    meta = ACTION_DEFS.get(action)
    if not meta:
        return {"ok": False, "error": "Unsupported action"}
    if meta["risk"] == "safe":
        result = execute_safe_action(action, payload)
    elif force:
        result = execute_medium_action(action, payload)
    else:
        return {"ok": False, "error": "Confirmation required", "risk": meta["risk"]}
    append_action_log({"service": safe_text(payload.get("service") or payload.get("target") or "mission-control", 80), "action": action, "risk": meta["risk"], "status": "success" if result.get("ok") else "error", "output": sanitize_output(result.get("output") or result.get("error") or meta["label"], 1000)})
    return result


def prepare_action(payload: dict) -> dict:
    action = str(payload.get("action") or "")
    meta = ACTION_DEFS.get(action)
    if not meta:
        return {"ok": False, "error": "Unsupported action"}
    if meta["risk"] == "high":
        return {"ok": False, "error": "High-risk action blocked"}
    code = f"{secrets.randbelow(1000000):06d}"
    approval_id = secrets.token_urlsafe(16)
    details = {"action": action, "label": meta["label"], "risk": meta["risk"], "payload": payload, "expires_at": time.time() + APPROVAL_TTL_SECONDS}
    PENDING_APPROVALS[approval_id] = {"code": code, "details": details}
    return {"ok": True, "approval_id": approval_id, "approval_code": code, "details": details, "message": f"Type approval code {code} to confirm: {meta['label']}."}


def execute_action(payload: dict) -> dict:
    approval_id = str(payload.get("approval_id") or "")
    code = str(payload.get("approval_code") or "")
    pending = PENDING_APPROVALS.get(approval_id)
    if not pending:
        return {"ok": False, "error": "Approval not found or already used"}
    if time.time() > pending["details"].get("expires_at", 0):
        PENDING_APPROVALS.pop(approval_id, None)
        return {"ok": False, "error": "Approval expired"}
    if code != pending.get("code"):
        return {"ok": False, "error": "Approval code mismatch"}
    PENDING_APPROVALS.pop(approval_id, None)
    d = pending["details"]
    return run_action(str(d["action"]), dict(d.get("payload") or {}), force=True)


def api_status(include_heavy: bool = True) -> dict:
    cfg = read_json(WORKFLOWS_DATA, {"workflows": [], "agents": []})
    workflows = cfg.get("workflows", [])
    services_from_workflows = sorted({svc for w in workflows for svc in w.get("services", [])})
    ports = sorted({port for w in workflows for port in w.get("ports", [])})
    service_map = {s: service_status(s) for s in services_from_workflows}
    port_map = {str(p): port_status(p) for p in ports}
    for workflow in workflows:
        svc_results = [service_map[s] for s in workflow.get("services", [])]
        port_results = [port_map[str(p)] for p in workflow.get("ports", [])]
        if svc_results and all(s["ok"] for s in svc_results):
            runtime_state = "online"
        elif svc_results and any(s["ok"] for s in svc_results):
            runtime_state = "partial"
        elif workflow.get("status") in {"blocked", "scheduled", "idle"}:
            runtime_state = workflow.get("status")
        else:
            runtime_state = "unknown"
        workflow["runtime_state"] = runtime_state
        workflow["service_status"] = svc_results
        workflow["port_status"] = port_results
    jobs = load_cron_jobs()
    summarized_jobs = [summarize_job(j) for j in jobs]
    stats = session_stats()
    review_items = [j for j in summarized_jobs if j["needs_review"]][:8]
    enabled_jobs = [j for j in summarized_jobs if j["enabled"]]
    services = service_inventory() if include_heavy else []
    return {
        "generated_at": now_iso(),
        "workflows": workflows,
        "agents": cfg.get("agents", []),
        "services": services,
        "dashboards": services,
        "profiles": get_profiles(),
        "skills": get_skills(),
        "plugins": get_plugins(),
        "active_runs": get_active_runs(),
        "recent_runs": get_runs(limit=20),
        "cron_preview": [],
        "scheduled_tasks": summarized_jobs[:20],
        "review_queue": review_items,
        "task_board": build_task_board(workflows, jobs),
        "recent_files": recent_files(),
        "nightly_builds": get_nightly_builds_enhanced()[:20],
        "tasks": tasks()[:30],
        "workflows_multi": get_workflows(),
        "action_history": action_history(20),
        "docs": read_json(DOCS_DATA, {}),
        "governance": {"security_score": 90 if not review_items else 75, "posture": "good" if not review_items else "watch", "checks": [{"label": "Action safety", "value": "Safe direct, medium confirmed, high blocked"}, {"label": "Secrets exposure", "value": "redacted and excluded"}, {"label": "Service registry", "value": f"{len(services) if services else len(load_services())} services"}]},
        "cost_tracker": {"estimated_cost_usd": stats.get("cost", 0.0), "tokens": stats.get("tokens", 0), "models": stats.get("models", [])},
        "summary": {"online_workflows": sum(1 for w in workflows if w.get("runtime_state") == "online"), "blocked_workflows": sum(1 for w in workflows if w.get("runtime_state") in {"blocked", "partial"} or w.get("blocker")), "enabled_crons": len(enabled_jobs), "review_items": len(review_items), "sessions": stats.get("sessions", 0), "messages": stats.get("messages", 0), "tokens": stats.get("tokens", 0), "cost": stats.get("cost", 0.0), "services_online": sum(1 for s in services if s.get("status") == "online") if services else None},
        "links": {svc.get("name"): svc.get("public_url") or svc.get("url") for svc in load_services()},
        "action_defs": ACTION_DEFS,
    }


# ── Agent Dispatch Queue ──────────────────────────────────────────────

DISPATCH_STATUSES = {"queued", "dispatched", "running", "completed", "failed", "cancelled"}
DISPATCH_TIMEOUT = 120  # seconds
DISPATCH_MAX_TURNS = 10

# Profile name normalization — the UI/router uses title-case names, but
# `hermes -p` only accepts lowercase CLI aliases. Tutor has no profile on
# disk; it maps to default.
PROFILE_CLI_ALIAS = {
    "default": "default",
    "coder": "coder",
    "contentcreator": "contentcreator",
    "deepresearch": "deepresearch",
    "marketanalyst": "marketanalyst",
    "tutor": "default",
}
VALID_CLI_PROFILES = frozenset({"default", "coder", "contentcreator", "deepresearch", "marketanalyst"})


def _normalize_cli_profile(profile_name: str) -> str:
    """Map any profile name (title-case, mixed-case) to a valid hermes -p alias."""
    key = profile_name.strip().lower()
    return PROFILE_CLI_ALIAS.get(key, "default")


def _run_hermes_dispatch(profile: str, prompt: str, toolsets: str = "") -> tuple[int, str, str]:
    """Execute hermes -p <profile> chat -q <prompt> --quiet --max-turns N.
    Returns (exit_code, session_id, response)."""
    cli_profile = _normalize_cli_profile(profile)
    cmd = ["hermes", "-p", cli_profile, "chat", "-q", prompt, "--quiet", f"--max-turns={DISPATCH_MAX_TURNS}"]
    if toolsets:
        cmd.extend(["-t", toolsets])
    try:
        # Legacy fallback only. The active dispatch engine uses Popen streaming.
        p = subprocess.Popen(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = p.communicate(timeout=DISPATCH_TIMEOUT)
        output = sanitize_output(((stdout or "") + (stderr or "")).strip(), 12000)
        # Extract session_id from anywhere in output (it may be first or last line)
        session_id = ""
        response = output
        import re as _re
        m = _re.search(r'session_id:\s*(\S+)', output)
        if m:
            session_id = m.group(1)
            # Remove the session_id line from response
            response = _re.sub(r'\n?\s*session_id:\s*\S+\s*', '', output).strip()
        return p.returncode, session_id, response
    except subprocess.TimeoutExpired:
        try:
            p.kill()
        except Exception:
            pass
        return -1, "", f"Dispatch timed out after {DISPATCH_TIMEOUT}s"
    except Exception as e:
        return -2, "", f"Dispatch failed: {str(e)[:300]}"


def _load_dispatch_queue() -> list[dict]:
    if not DISPATCH_DATA.exists():
        return []
    items = []
    for line in DISPATCH_DATA.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            items.append(json.loads(line))
        except Exception:
            continue
    return items


def _append_dispatch(item: dict) -> dict:
    item.setdefault("dispatch_id", uuid.uuid4().hex[:12])
    item.setdefault("created_at", now_iso())
    DISPATCH_DATA.parent.mkdir(parents=True, exist_ok=True)
    with DISPATCH_DATA.open("a", encoding="utf-8") as f:
        f.write(json.dumps(item, default=str) + "\n")
    return item


def _update_dispatch(dispatch_id: str, patch: dict) -> dict:
    items = _load_dispatch_queue()
    updated = {}
    new_lines = []
    for item in items:
        if item.get("dispatch_id") == dispatch_id:
            item.update(patch)
            item["updated_at"] = now_iso()
            updated = item
        new_lines.append(json.dumps(item, default=str) + "\n")
    DISPATCH_DATA.write_text("".join(new_lines), encoding="utf-8")
    return updated


def _find_dispatch(dispatch_id: str) -> dict | None:
    items = _load_dispatch_queue()
    for item in items:
        if item.get("dispatch_id") == dispatch_id:
            return item
    return None


def _dispatch_telegram(dispatch: dict, event: str) -> None:
    wf_id = dispatch.get("workflow_id", "?")
    title = dispatch.get("workflow_title", dispatch.get("title", "?"))
    profile = dispatch.get("profile", "Default")
    status = dispatch.get("status", "?")
    d_id = dispatch.get("dispatch_id", "?")

    if event == "dispatched":
        msg = f"""🚀 *Dispatch Started*
Workflow: *{title}*
Profile: {profile}
Dispatch ID: `{d_id}`

[Dashboard →]({DASHBOARD_URL})"""
    elif event == "completed":
        msg = f"""✅ *Dispatch Completed*
Workflow: *{title}*
Profile: {profile}
Status: completed

[Dashboard →]({DASHBOARD_URL})"""
    elif event == "failed":
        err = dispatch.get("error", {})
        msg = f"""❌ *Dispatch Failed*
Workflow: *{title}*
Profile: {profile}
Error: {safe_text(err.get('message', str(err)[:200]), 200)}

[Dashboard →]({DASHBOARD_URL})"""
    elif event == "cancelled":
        msg = f"""🚫 *Dispatch Cancelled*
Workflow: *{title}*
Profile: {profile}

[Dashboard →]({DASHBOARD_URL})"""
    else:
        return

    _send_telegram(msg)


def build_dispatch_prompt(profile: str, title: str, context: dict = None) -> str:
    """Build a profile-specific dispatch prompt."""
    context = context or {}
    templates = {
        "Coder": f"""You are the Coder profile of Hermes. Execute this task:\n\nTask: {title}\n\nFollow best practices: read context first, test your changes, verify with real output.\nReport: what you did, what changed, what to check.\nFiles: {context.get('files_affected', 'unknown')}\nRepo: {context.get('repo_path', '/root')}\n\nKeep it concise. Produce working artifacts, not explanations.""",
        "ContentCreator": f"""You are the ContentCreator profile of Hermes. Create content for this task:\n\nTask: {title}\n\nPlatform: {context.get('platform', 'x')}\nAudience: {context.get('audience', 'devops')}\nFormat: {context.get('format', 'post')}\nTone: {context.get('tone', 'practical')}\n\nProduce publish-ready content with hooks, captions, and image prompts if needed.""",
        "DeepResearch": f"""You are the DeepResearch profile of Hermes. Research this topic:\n\nQuestion: {title}\n\nDecision to support: {context.get('decision', 'general knowledge')}\nSource requirements: {context.get('source_requirements', 'primary preferred')}\nOutput format: {context.get('output_format', 'brief')}\n\nProduce a structured research brief with findings, sources, and recommendations.""",
        "MarketAnalyst": f"""You are the MarketAnalyst profile of Hermes. Analyze this:\n\nTask: {title}\n\nAsset type: {context.get('asset_type', 'stock')}\nMarket: {context.get('market', 'nse')}\nTime horizon: {context.get('time_horizon', 'medium')}\nAnalysis type: {context.get('analysis_type', 'fundamental')}\n\nProduce analysis with key metrics, technicals if relevant, and clear recommendations.""",
        "Tutor": f"""You are the Tutor profile of Hermes. Teach this topic:\n\nTopic: {title}\n\nDifficulty: {context.get('difficulty_level', 'intermediate')}\nInclude quiz: {context.get('quiz_required', False)}\nInclude diagrams: {context.get('diagram_required', False)}\n\nUse simple sections, examples, memory hooks, and a quiz at the end. Teach, don't lecture.""",
    }
    return sanitize_output(templates.get(profile, f"Execute this task as {profile} profile:\n\n{title}"), 5000)


def enqueue_dispatch(payload: dict) -> dict:
    """Queue a dispatch for a workflow subtask or standalone task."""
    wf_id = str(payload.get("workflow_id") or "")
    st_id = str(payload.get("subtask_id") or "")
    profile = str(payload.get("profile") or "Default")
    title = str(payload.get("title") or "Dispatch task")
    ptype = str(payload.get("type") or "subtask")  # subtask or standalone

    # Get workflow context
    wf = get_workflow(wf_id) if wf_id else None
    workflow_title = wf.get("title", title) if wf else title

    # Build prompt
    context = payload.get("context") or {}
    prompt = build_dispatch_prompt(profile, title, context)

    # Detect if real dispatch is possible (hermes agent dispatch)
    try:
        p = subprocess.run(["which", "hermes"], capture_output=True, text=True, timeout=3)
        hermes_available = p.returncode == 0
    except Exception:
        hermes_available = False

    dispatch = {
        "dispatch_id": str(payload.get("dispatch_id") or uuid.uuid4().hex[:12]),
        "workflow_id": wf_id,
        "subtask_id": st_id,
        "type": ptype,
        "workflow_title": workflow_title,
        "title": title,
        "profile": profile,
        "prompt": prompt,
        "status": "queued",
        "hermes_available": hermes_available,
        "dispatch_method": "hermes_profile" if hermes_available else "manual",
        "created_at": now_iso(),
        "started_at": None,
        "finished_at": None,
        "output": {},
        "error": {},
        "run_id": None,
        "telegram_sent": False,
    }

    result = _append_dispatch(dispatch)

    # Notify Telegram
    _dispatch_telegram(result, "dispatched")

    append_action_log({"service": "mission-control", "action": "enqueue_dispatch", "risk": "safe",
                       "status": "success", "output": f"Dispatch {result['dispatch_id']} queued for {profile}"})

    return {"ok": True, "dispatch": result, "hermes_available": hermes_available}


def get_dispatches(status_filter: str = "") -> list[dict]:
    items = _load_dispatch_queue()
    if status_filter:
        items = [i for i in items if i.get("status") == status_filter]
    items.sort(key=lambda i: i.get("created_at", ""), reverse=True)
    return items


def get_dispatch(dispatch_id: str) -> dict | None:
    return _find_dispatch(dispatch_id)


def dispatch_start(dispatch_id: str) -> dict:
    """Execute dispatch via hermes -p <profile> chat -q."""
    disp = _find_dispatch(dispatch_id)
    if not disp:
        return {"ok": False, "error": "Dispatch not found"}
    if disp.get("status") not in ("queued", "failed"):
        return {"ok": False, "error": f"Dispatch is {disp.get('status')}"}

    profile = disp.get("profile", "Default")
    prompt = disp.get("prompt", "")
    patch = {"status": "running", "started_at": now_iso(), "dispatch_method": "hermes_cli"}

    # Create run record
    run = start_run({
        "title": disp.get("title", "Dispatch"),
        "trigger_source": "dispatch",
        "service": "mission-control",
        "profile": profile,
        "current_step": "executing",
        "input": {"dispatch_id": dispatch_id},
    })
    patch["run_id"] = run.get("run_id")

    # Execute real CLI dispatch
    exit_code, session_id, response = _run_hermes_dispatch(profile, prompt)

    if exit_code == 0 and session_id:
        patch["status"] = "completed"
        patch["session_id"] = session_id
        patch["output"] = {"session_id": session_id, "response": sanitize_output(response, 8000)}
        patch["error"] = {}
        patch["finished_at"] = now_iso()

        # Finish run
        finish_run(run["run_id"], {"status": "succeeded", "output": patch["output"]})

        # Auto-complete linked subtask
        wf_id = disp.get("workflow_id", "")
        st_id = disp.get("subtask_id", "")
        if wf_id and st_id:
            try:
                complete_subtask(wf_id, st_id, {"output": patch["output"]})
            except Exception:
                pass

        updated = _update_dispatch(dispatch_id, patch)
        _dispatch_telegram(updated, "completed")
        return {"ok": True, "dispatch": updated, "exit_code": exit_code, "session_id": session_id}
    else:
        # Failed — mark as failed
        error_msg = response if response else f"Exit code {exit_code}"
        patch["status"] = "failed"
        patch["error"] = {"message": error_msg[:500]}
        patch["output"] = {"response": sanitize_output(response, 4000)} if response else {}
        patch["finished_at"] = now_iso()

        finish_run(run["run_id"], {"status": "failed", "error": patch["error"], "output": patch["output"]})

        # Auto-fail linked subtask
        wf_id = disp.get("workflow_id", "")
        st_id = disp.get("subtask_id", "")
        if wf_id and st_id:
            try:
                fail_subtask(wf_id, st_id, {"error": patch["error"]})
            except Exception:
                pass

        updated = _update_dispatch(dispatch_id, patch)
        _dispatch_telegram(updated, "failed")
        return {"ok": False, "dispatch": updated, "exit_code": exit_code, "error": patch["error"]}


def dispatch_complete(dispatch_id: str, payload: dict = None) -> dict:
    """Mark dispatch as completed."""
    payload = payload or {}
    disp = _find_dispatch(dispatch_id)
    if not disp:
        return {"ok": False, "error": "Dispatch not found"}

    output = payload.get("output") or disp.get("output") or {}
    patch = {
        "status": "completed",
        "finished_at": now_iso(),
        "output": output,
        "error": {},
    }

    # Finish the run if exists
    if disp.get("run_id"):
        finish_run(disp["run_id"], {"status": "succeeded", "output": output})

    updated = _update_dispatch(dispatch_id, patch)
    _dispatch_telegram(updated, "completed")

    # If this is a subtask dispatch, auto-complete the subtask
    wf_id = disp.get("workflow_id", "")
    st_id = disp.get("subtask_id", "")
    if wf_id and st_id:
        try:
            complete_subtask(wf_id, st_id, {"output": output})
        except Exception:
            pass

    return {"ok": True, "dispatch": updated}


def dispatch_fail(dispatch_id: str, payload: dict = None) -> dict:
    """Mark dispatch as failed."""
    payload = payload or {}
    disp = _find_dispatch(dispatch_id)
    if not disp:
        return {"ok": False, "error": "Dispatch not found"}

    error = payload.get("error") or {"message": "Dispatch failed"}
    patch = {
        "status": "failed",
        "finished_at": now_iso(),
        "error": error,
    }

    if disp.get("run_id"):
        finish_run(disp["run_id"], {"status": "failed", "error": error})

    updated = _update_dispatch(dispatch_id, patch)
    _dispatch_telegram(updated, "failed")

    # Auto-fail the subtask
    wf_id = disp.get("workflow_id", "")
    st_id = disp.get("subtask_id", "")
    if wf_id and st_id:
        try:
            fail_subtask(wf_id, st_id, {"error": error})
        except Exception:
            pass

    return {"ok": True, "dispatch": updated}


def dispatch_retry(dispatch_id: str) -> dict:
    """Retry a failed dispatch."""
    disp = _find_dispatch(dispatch_id)
    if not disp:
        return {"ok": False, "error": "Dispatch not found"}
    if disp.get("status") != "failed":
        return {"ok": False, "error": f"Dispatch is {disp.get('status')}, not failed"}

    patch = {"status": "queued", "error": {}, "started_at": None, "finished_at": None}
    updated = _update_dispatch(dispatch_id, patch)
    return {"ok": True, "dispatch": updated}


def dispatch_cancel(dispatch_id: str) -> dict:
    """Cancel a pending dispatch."""
    disp = _find_dispatch(dispatch_id)
    if not disp:
        return {"ok": False, "error": "Dispatch not found"}
    if disp.get("status") not in {"queued", "running"}:
        return {"ok": False, "error": f"Dispatch is {disp.get('status')}, cannot cancel"}

    patch = {"status": "cancelled", "finished_at": now_iso()}
    updated = _update_dispatch(dispatch_id, patch)
    _dispatch_telegram(updated, "cancelled")
    return {"ok": True, "dispatch": updated}


def dispatch_manual_output(dispatch_id: str, payload: dict = None) -> dict:
    """Accept manual output for a dispatch (fallback when CLI fails)."""
    payload = payload or {}
    disp = _find_dispatch(dispatch_id)
    if not disp:
        return {"ok": False, "error": "Dispatch not found"}
    if disp.get("status") not in {"queued", "running", "failed"}:
        return {"ok": False, "error": f"Dispatch is {disp.get('status')}"}

    output = payload.get("output") or {"manual": True, "result": "Manually completed"}
    patch = {
        "status": "completed",
        "finished_at": now_iso(),
        "dispatch_method": "manual",
        "output": output,
        "error": {},
    }

    if disp.get("run_id"):
        finish_run(disp["run_id"], {"status": "succeeded", "output": output})

    updated = _update_dispatch(dispatch_id, patch)
    _dispatch_telegram(updated, "completed")

    # Complete subtask
    wf_id = disp.get("workflow_id", "")
    st_id = disp.get("subtask_id", "")
    if wf_id and st_id:
        try:
            complete_subtask(wf_id, st_id, {"output": output})
        except Exception:
            pass

    return {"ok": True, "dispatch": updated}


def get_active_dispatches() -> list[dict]:
    """Get currently active dispatches."""
    return get_dispatches("running") + get_dispatches("queued")


def get_dispatch_logs(dispatch_id: str) -> dict:
    """Get session logs from journal if available."""
    disp = _find_dispatch(dispatch_id)
    if not disp:
        return {"ok": False, "error": "Dispatch not found"}
    session_id = disp.get("session_id", "")
    logs = ""
    if session_id:
        # Try to find session in state.db
        code, out = run(["bash", "-lc", f"sqlite3 {STATE_DB} \"select content from messages where session_id=(select id from sessions where session_id='{session_id}' limit 1) order by id desc limit 20\" 2>/dev/null"], timeout=5)
        if code == 0 and out:
            logs = sanitize_output(out, 5000)
    return {"ok": True, "dispatch_id": dispatch_id, "session_id": session_id, "logs": logs or "No session logs available", "has_logs": bool(logs)}


def workflow_dispatch_all_ready(wf_id: str) -> dict:
    """Dispatch all ready (queued, unblocked) subtasks in a workflow."""
    wf = get_workflow(wf_id)
    if not wf:
        return {"ok": False, "error": "Workflow not found"}

    if wf.get("status") not in {"draft", "paused", "running"}:
        return {"ok": False, "error": f"Workflow is {wf.get('status')}"}

    # Start workflow if needed
    if wf.get("status") in {"draft", "paused"}:
        start_workflow(wf_id)

    results = []
    for st in wf.get("subtasks", []):
        if st.get("status") not in {"queued"}:
            continue

        # Check dependencies
        deps_met = True
        for dep in st.get("depends_on", []):
            dep_st = next((s for s in wf.get("subtasks", []) if s.get("profile") == dep), None)
            if dep_st and dep_st.get("status") != "completed":
                deps_met = False
                break

        if not deps_met:
            continue

        # Start the subtask and create dispatch
        start_subtask(wf_id, st["id"])

        # Create dispatch
        disp = enqueue_dispatch({
            "workflow_id": wf_id,
            "subtask_id": st["id"],
            "profile": st["profile"],
            "title": st["title"],
            "type": "subtask",
        })
        dispatch_id = disp["dispatch"]["dispatch_id"]

        # Execute dispatch immediately
        result = dispatch_start(dispatch_id)
        results.append({
            "subtask_id": st["id"],
            "profile": st["profile"],
            "dispatch_id": dispatch_id,
            "ok": result.get("ok", False),
            "session_id": result.get("session_id", ""),
        })

    wf = get_workflow(wf_id)  # Reload
    return {"ok": True, "workflow": wf, "dispatched": len(results), "results": results}


def workflow_dispatch_next(wf_id: str) -> dict:
    """Dispatch the next ready subtask in a workflow."""
    wf = get_workflow(wf_id)
    if not wf:
        return {"ok": False, "error": "Workflow not found"}

    for st in wf.get("subtasks", []):
        if st.get("status") not in {"queued"}:
            continue
        deps_met = True
        for dep in st.get("depends_on", []):
            dep_st = next((s for s in wf.get("subtasks", []) if s.get("profile") == dep), None)
            if dep_st and dep_st.get("status") != "completed":
                deps_met = False
                break
        if not deps_met:
            continue

        start_subtask(wf_id, st["id"])
        disp = enqueue_dispatch({
            "workflow_id": wf_id,
            "subtask_id": st["id"],
            "profile": st["profile"],
            "title": st["title"],
            "type": "subtask",
        })
        result = dispatch_start(disp["dispatch"]["dispatch_id"])
        return {"ok": result.get("ok", False), "workflow": get_workflow(wf_id),
                "subtask_id": st["id"], "profile": st["profile"],
                "dispatch_id": disp["dispatch"]["dispatch_id"],
                "session_id": result.get("session_id", "")}

    return {"ok": False, "error": "No ready subtasks found"}


# ── Wire dispatch engine callbacks ─────────────────────────────────
dispatch_engine.set_run_fns(start_run, finish_run)
dispatch_engine.set_wf_fns(get_workflow, complete_subtask, fail_subtask,
                           start_subtask, synthesize_workflow)
dispatch_engine.set_telegram_fn(_send_telegram)
dispatch_engine.set_action_log_fn(append_action_log)

# Replace inline dispatch functions with engine versions
from dispatch_engine import (
    workflow_dispatch_parallel, workflow_dispatch_all_ready, workflow_dispatch_next,
    enqueue_dispatch, get_dispatches, get_dispatch, get_active_dispatches,
    dispatch_start, dispatch_complete, dispatch_fail, dispatch_retry,
    dispatch_cancel, dispatch_manual_output, get_dispatch_logs, get_dispatch_live,
    get_workflow_timeline, get_reliability_limits, resume_workflow, cancel_workflow,
    get_profile_gateways,
    profile_gateway_test, profile_gateway_start, profile_gateway_stop, profile_gateway_restart,
)


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(STATIC), **kwargs)

    def log_message(self, fmt, *args):
        print("%s - %s" % (self.address_string(), fmt % args))

    def do_POST(self):
        parsed = urlparse(self.path)
        payload = read_json_body(self)
        if parsed.path == "/api/actions/prepare":
            return json_response(self, prepare_action(payload))
        if parsed.path == "/api/actions/execute":
            return json_response(self, execute_action(payload))
        if parsed.path == "/api/actions/run":
            return json_response(self, run_action(str(payload.get("action") or ""), payload, force=False))
        if parsed.path == "/api/runs/start":
            return json_response(self, start_run(payload))
        if parsed.path.startswith("/api/runs/") and parsed.path.endswith("/log"):
            run_id = parsed.path.split("/")[3]
            return json_response(self, append_run_log(run_id, payload))
        if parsed.path.startswith("/api/runs/") and parsed.path.endswith("/status"):
            run_id = parsed.path.split("/")[3]
            return json_response(self, update_run_status(run_id, payload))
        if parsed.path.startswith("/api/runs/") and parsed.path.endswith("/finish"):
            run_id = parsed.path.split("/")[3]
            return json_response(self, finish_run(run_id, payload))
        if parsed.path == "/api/nightly-builds":
            return json_response(self, save_nightly_build(payload))
        if parsed.path == "/api/nightly-builds/upload":
            return json_response(self, _upload_nightly_attachment(payload))
        if parsed.path == "/api/tasks":
            return json_response(self, save_task(payload))
        if parsed.path == "/api/tasks/move":
            return json_response(self, _move_task(payload))
        if parsed.path == "/api/tasks/archive":
            return json_response(self, _archive_task(payload))
        if parsed.path == "/api/tasks/assign":
            return json_response(self, _assign_task(payload))
        if parsed.path == "/api/profiles/edit":
            return json_response(self, _edit_profile(payload))
        if parsed.path == "/api/routing/recommend":
            return json_response(self, route_profile_v2(payload))
        if parsed.path == "/api/routing/feedback":
            payload["status"] = "feedback"
            append_routing_history(payload)
            return json_response(self, {"ok": True, "message": "Feedback recorded"})
        if parsed.path == "/api/tasks/decompose":
            return json_response(self, decompose_task(payload))
        if parsed.path == "/api/profiles/reindex":
            profile = str(payload.get("profile") or "")
            if profile:
                return json_response(self, reindex_profile(profile))
            return json_response(self, index_all_profiles())
        if parsed.path == "/api/settings/routing-threshold":
            return json_response(self, save_routing_threshold(payload))
        if parsed.path.startswith("/api/runs/") and parsed.path.endswith("/profile-switch"):
            run_id = parsed.path.split("/")[3]
            return json_response(self, switch_run_profile(run_id, payload))
        if parsed.path == "/api/settings/profile-mode":
            return json_response(self, save_profile_settings(payload))
        if parsed.path == "/api/tasks/profile":
            task_id = str(payload.get("task_id") or "")
            profile = str(payload.get("profile") or "")
            return json_response(self, _assign_task({"task_id": task_id, "profile": profile}))
        # ── Multi-profile workflow endpoints ──
        if parsed.path == "/api/workflows/create":
            return json_response(self, create_workflow(payload))
        match = re.match(r"^/api/workflows/([^/]+)/start$", parsed.path)
        if match:
            return json_response(self, start_workflow(match.group(1)))
        match = re.match(r"^/api/workflows/([^/]+)/pause$", parsed.path)
        if match:
            return json_response(self, pause_workflow(match.group(1)))
        match = re.match(r"^/api/workflows/([^/]+)/cancel$", parsed.path)
        if match:
            return json_response(self, cancel_workflow(match.group(1), payload))
        match = re.match(r"^/api/workflows/([^/]+)/resume$", parsed.path)
        if match:
            return json_response(self, resume_workflow(match.group(1), payload))
        match = re.match(r"^/api/workflows/([^/]+)/synthesize$", parsed.path)
        if match:
            return json_response(self, synthesize_workflow(match.group(1)))
        match = re.match(r"^/api/workflows/([^/]+)/subtasks/([^/]+)/start$", parsed.path)
        if match:
            return json_response(self, start_subtask(match.group(1), match.group(2)))
        match = re.match(r"^/api/workflows/([^/]+)/subtasks/([^/]+)/complete$", parsed.path)
        if match:
            return json_response(self, complete_subtask(match.group(1), match.group(2), payload))
        match = re.match(r"^/api/workflows/([^/]+)/subtasks/([^/]+)/fail$", parsed.path)
        if match:
            return json_response(self, fail_subtask(match.group(1), match.group(2), payload))
        match = re.match(r"^/api/workflows/([^/]+)/subtasks/([^/]+)/retry$", parsed.path)
        if match:
            return json_response(self, retry_subtask(match.group(1), match.group(2)))
        match = re.match(r"^/api/workflows/([^/]+)/subtasks/([^/]+)/reroute$", parsed.path)
        if match:
            return json_response(self, reroute_subtask(match.group(1), match.group(2), payload))
        # ── Dispatch endpoints ──
        if parsed.path == "/api/dispatch/enqueue":
            return json_response(self, enqueue_dispatch(payload))
        match = re.match(r"^/api/dispatch/([^/]+)/start$", parsed.path)
        if match:
            return json_response(self, dispatch_start(match.group(1)))
        match = re.match(r"^/api/dispatch/([^/]+)/complete$", parsed.path)
        if match:
            return json_response(self, dispatch_complete(match.group(1), payload))
        match = re.match(r"^/api/dispatch/([^/]+)/fail$", parsed.path)
        if match:
            return json_response(self, dispatch_fail(match.group(1), payload))
        match = re.match(r"^/api/dispatch/([^/]+)/retry$", parsed.path)
        if match:
            return json_response(self, dispatch_retry(match.group(1)))
        match = re.match(r"^/api/dispatch/([^/]+)/cancel$", parsed.path)
        if match:
            return json_response(self, dispatch_cancel(match.group(1)))
        match = re.match(r"^/api/dispatch/([^/]+)/manual-output$", parsed.path)
        if match:
            return json_response(self, dispatch_manual_output(match.group(1), payload))
        match = re.match(r"^/api/dispatch/([^/]+)/logs$", parsed.path)
        if match:
            return json_response(self, get_dispatch_logs(match.group(1)))
        # ── Workflow dispatch endpoints ──
        match = re.match(r"^/api/workflows/([^/]+)/dispatch-parallel$", parsed.path)
        if match:
            return json_response(self, workflow_dispatch_parallel(match.group(1)))
        match = re.match(r"^/api/workflows/([^/]+)/dispatch$", parsed.path)
        if match:
            return json_response(self, workflow_dispatch_all_ready(match.group(1)))
        match = re.match(r"^/api/workflows/([^/]+)/dispatch-next$", parsed.path)
        if match:
            return json_response(self, workflow_dispatch_next(match.group(1)))
        # ── Profile gateway controls ──
        match = re.match(r"^/api/profile-gateways/([^/]+)/test$", parsed.path)
        if match:
            return json_response(self, profile_gateway_test(match.group(1)))
        match = re.match(r"^/api/profile-gateways/([^/]+)/start$", parsed.path)
        if match:
            return json_response(self, profile_gateway_start(match.group(1)))
        match = re.match(r"^/api/profile-gateways/([^/]+)/stop$", parsed.path)
        if match:
            return json_response(self, profile_gateway_stop(match.group(1)))
        match = re.match(r"^/api/profile-gateways/([^/]+)/restart$", parsed.path)
        if match:
            return json_response(self, profile_gateway_restart(match.group(1)))
        return json_response(self, {"ok": False, "error": "Not found"}, status=404)

    def do_GET(self):
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)
        if parsed.path == "/api/status":
            return json_response(self, api_status())
        if parsed.path == "/api/services":
            return json_response(self, load_services())
        if parsed.path == "/api/services/health":
            return json_response(self, service_inventory())
        if parsed.path == "/api/nightly-builds":
            return json_response(self, nightly_builds())
        if parsed.path == "/api/tasks":
            return json_response(self, tasks())
        if parsed.path == "/api/actions/history":
            return json_response(self, action_history())
        if parsed.path == "/api/runs/active":
            return json_response(self, get_active_runs())
        if parsed.path == "/api/runs":
            limit = int(query.get("limit", ["50"])[0])
            status_filter = query.get("status", [""])[0]
            return json_response(self, get_runs(limit=limit, status_filter=status_filter))
        if parsed.path.startswith("/api/runs/"):
            run_id = parsed.path.split("/")[3]
            run = get_run(run_id)
            if not run:
                return json_response(self, {"ok": False, "error": "Run not found"}, status=404)
            return json_response(self, run)
        if parsed.path == "/api/profiles":
            return json_response(self, get_profiles())
        if parsed.path == "/api/skills":
            return json_response(self, get_skills())
        if parsed.path == "/api/plugins":
            return json_response(self, get_plugins())
        if parsed.path == "/api/logs":
            service = query.get("service", ["mission-control.service"])[0]
            lines = int(query.get("lines", ["120"])[0])
            return json_response(self, list_logs(service, lines))
        if parsed.path == "/api/docs":
            return json_response(self, read_json(DOCS_DATA, {}))
        if parsed.path == "/api/settings/profile-mode":
            return json_response(self, get_profile_settings())
        if parsed.path == "/api/routing/history":
            limit = int(query.get("limit", ["50"])[0])
            feedback_only = query.get("feedback", ["0"])[0] == "1"
            history = get_routing_history(limit=limit)
            if feedback_only:
                history = [h for h in history if h.get("status") == "feedback"]
            return json_response(self, history)
        if parsed.path == "/api/profiles/routing-index":
            profile = query.get("profile", [""])[0]
            idx = get_routing_index()
            if profile:
                return json_response(self, idx.get(profile, {"error": "Profile not in index"}))
            return json_response(self, idx)
        if parsed.path == "/api/settings/routing-threshold":
            return json_response(self, get_routing_threshold())
        if parsed.path == "/api/reliability/limits":
            return json_response(self, get_reliability_limits())
        if parsed.path == "/api/workflows":
            status_filter = query.get("status", [""])[0]
            return json_response(self, get_workflows(status_filter))
        if parsed.path.startswith("/api/workflows/"):
            wf_id = parsed.path.split("/")[3]
            if parsed.path.endswith("/timeline"):
                return json_response(self, get_workflow_timeline(wf_id))
            if parsed.path.endswith("/dispatch-state"):
                wf = get_workflow(wf_id)
                if not wf:
                    return json_response(self, {"ok": False, "error": "Workflow not found"}, status=404)
                ready = sum(1 for s in wf.get("subtasks", []) if s.get("status") == "queued")
                running = sum(1 for s in wf.get("subtasks", []) if s.get("status") in ("running", "retrying"))
                waiting = sum(1 for s in wf.get("subtasks", []) if s.get("status") == "waiting")
                return json_response(self, {"ok": True, "workflow_id": wf_id, "ready": ready, "running": running, "waiting": waiting, "status": wf.get("status")})
            wf = get_workflow(wf_id)
            if not wf:
                return json_response(self, {"ok": False, "error": "Workflow not found"}, status=404)
            return json_response(self, wf)
        if parsed.path == "/api/dispatch":
            status_filter = query.get("status", [""])[0]
            return json_response(self, get_dispatches(status_filter))
        if parsed.path == "/api/dispatch/active":
            return json_response(self, get_active_dispatches())
        if parsed.path.startswith("/api/dispatch/"):
            disp_id = parsed.path.split("/")[3]
            if parsed.path.endswith("/live"):
                return json_response(self, get_dispatch_live(disp_id))
            disp = get_dispatch(disp_id)
            if not disp:
                return json_response(self, {"ok": False, "error": "Dispatch not found"}, status=404)
            return json_response(self, disp)
        if parsed.path == "/api/profile-gateways":
            return json_response(self, get_profile_gateways())
        if parsed.path == "/healthz":
            body = b"ok\n"
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if parsed.path == "/":
            self.path = "/index.html"
        return super().do_GET()


def main():
    host = os.environ.get("MISSION_CONTROL_HOST", "127.0.0.1")
    port = int(os.environ.get("MISSION_CONTROL_PORT", "8090"))
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    httpd = ThreadingHTTPServer((host, port), Handler)
    print(f"Mission Control running at http://{host}:{port}")
    httpd.serve_forever()


if __name__ == "__main__":
    main()
