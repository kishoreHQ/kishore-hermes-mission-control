#!/usr/bin/env python3
"""
Mission Control — Dispatch Engine
=================================
Parallel dispatch, live heartbeat, automated retry, workflow timeline,
profile gateway controls.

Imported by server.py; callbacks are registered via set_wf_fns() etc.
"""
from __future__ import annotations

import json
import os
import queue
import re
import signal
import shutil
import subprocess
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

# ── runtime configuration (set by server.py import) ──────────────
ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
DISPATCH_DATA = DATA_DIR / "dispatch_queue.jsonl"
WF_EVENTS_DATA = DATA_DIR / "workflow_events.jsonl"
HERMES_HOME = Path(os.environ.get("HERMES_HOME", "/root/.hermes"))
PROFILES_DIR = HERMES_HOME / "profiles"
DASHBOARD_URL = "https://gcp-hermes.tail57c68b.ts.net:8090/"

DISPATCH_TIMEOUT = 120
DISPATCH_MAX_TURNS = 10
MAX_PARALLEL = 3
MAX_RETRIES = 1
RETRY_DELAY = 10  # seconds

# VM-safe limits for e2-medium (2 vCPU / 4 GB RAM)
MAX_CONCURRENT_DISPATCHES = int(os.environ.get("MC_MAX_CONCURRENT_DISPATCHES", "3"))
MAX_QUEUED_DISPATCHES = int(os.environ.get("MC_MAX_QUEUED_DISPATCHES", "25"))
MAX_CONCURRENT_WORKFLOWS = int(os.environ.get("MC_MAX_CONCURRENT_WORKFLOWS", "2"))
MAX_WORKFLOW_RUNTIME_SECONDS = int(os.environ.get("MC_MAX_WORKFLOW_RUNTIME_SECONDS", "3600"))
MAX_RETRIES_PER_WORKFLOW = int(os.environ.get("MC_MAX_RETRIES_PER_WORKFLOW", "6"))
TERMINAL_STATUSES = {"completed", "failed", "cancelled", "timed_out", "retry_exhausted", "skipped"}
RETRYABLE_FAILURES_DEFAULT = ["timeout", "failed", "provider_error", "rate_limited", "nonzero_exit"]
FAILURE_REASONS = {
    "timeout", "cancelled", "command_not_found", "provider_error", "rate_limited",
    "permission_error", "empty_output", "nonzero_exit", "validation_error", "unknown_error"
}

SECRET_RE = re.compile(
    r'(token|secret|auth|credential|key|password|cookie)[=:"\s]*([^\s",;}\]]{4,})',
    re.IGNORECASE,
)
SAFE_SYSTEMD_RESTARTS = {
    "mission-control.service", "hermes-webui.service",
    "claw3d-studio.service", "claw3d-adapter.service",
}

PROFILE_CLI_ALIAS = {
    "default": "default", "coder": "coder",
    "contentcreator": "contentcreator", "deepresearch": "deepresearch",
    "marketanalyst": "marketanalyst", "tutor": "default",
}
VALID_CLI_PROFILES = frozenset({"default", "coder", "contentcreator", "deepresearch", "marketanalyst"})

# ── thread safety ─────────────────────────────────────────────────
_dispatch_monitors: dict[str, dict] = {}
_monitor_lock = threading.Lock()
_parallel_semaphore = threading.BoundedSemaphore(MAX_PARALLEL)
dispatch_file_lock = threading.Lock()

# ── callbacks (set by server.py) ──────────────────────────────────
_get_workflow_fn = None
_complete_subtask_fn = None
_fail_subtask_fn = None
_start_subtask_fn = None
_synthesize_workflow_fn = None
_start_run_fn = None
_finish_run_fn = None
_send_telegram_fn = None
_append_action_log_fn = None


def set_wf_fns(get_fn, complete_fn, fail_fn, start_fn, synth_fn):
    global _get_workflow_fn, _complete_subtask_fn, _fail_subtask_fn, _start_subtask_fn, _synthesize_workflow_fn
    _get_workflow_fn = get_fn
    _complete_subtask_fn = complete_fn
    _fail_subtask_fn = fail_fn
    _start_subtask_fn = start_fn
    _synthesize_workflow_fn = synth_fn


def set_run_fns(start_fn, finish_fn):
    global _start_run_fn, _finish_run_fn
    _start_run_fn = start_fn
    _finish_run_fn = finish_fn


def set_telegram_fn(fn):
    global _send_telegram_fn
    _send_telegram_fn = fn


def set_action_log_fn(fn):
    global _append_action_log_fn
    _append_action_log_fn = fn


# ── helpers ───────────────────────────────────────────────────────
def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def sanitize_output(text: object, max_len: int = 12000) -> str:
    text = "" if text is None else str(text)
    text = SECRET_RE.sub(r"\1=[REDACTED]", text)
    return text[-max_len:] if len(text) > max_len else text


def safe_text(value: object, max_len: int = 160) -> str:
    text = "" if value is None else str(value)
    text = " ".join(text.split())
    return sanitize_output(text[:max_len], max_len)


def _normalize_cli_profile(profile_name: str) -> str:
    return PROFILE_CLI_ALIAS.get(profile_name.strip().lower(), "default")


def _run(cmd: list[str], timeout: int = 10) -> tuple[int, str]:
    try:
        p = subprocess.Popen(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = p.communicate(timeout=timeout)
        return p.returncode, sanitize_output((out or "") + (err or ""), 12000)
    except subprocess.TimeoutExpired:
        try:
            p.kill()
        except Exception:
            pass
        return -1, f"Command timed out after {timeout}s"
    except Exception as e:
        return -1, str(e)


# ── JSONL helpers ─────────────────────────────────────────────────
def _load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    items = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            items.append(json.loads(line))
        except Exception:
            continue
    return items


def _append_jsonl(path: Path, item: dict) -> dict:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(item, default=str) + "\n")
    return item


# ── dispatch queue persistence ────────────────────────────────────
def _load_dispatch_queue() -> list[dict]:
    return _load_jsonl(DISPATCH_DATA)


def _append_dispatch(item: dict) -> dict:
    item.setdefault("dispatch_id", uuid.uuid4().hex[:12])
    item.setdefault("created_at", now_iso())
    # Must share the update lock. Otherwise a concurrent _update_dispatch()
    # can rewrite dispatch_queue.jsonl while enqueue appends, dropping the new row
    # before /start can read it.
    with dispatch_file_lock:
        DISPATCH_DATA.parent.mkdir(parents=True, exist_ok=True)
        with DISPATCH_DATA.open("a", encoding="utf-8") as f:
            f.write(json.dumps(item, default=str) + "\n")
            f.flush()
            os.fsync(f.fileno())
    return item


def _update_dispatch(dispatch_id: str, patch: dict) -> dict:
    with dispatch_file_lock:
        items = _load_jsonl(DISPATCH_DATA)
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
    for item in _load_dispatch_queue():
        if item.get("dispatch_id") == dispatch_id:
            return item
    return None


# ── workflow helpers ──────────────────────────────────────────────
def _load_workflows() -> dict[str, dict]:
    wf_file = DATA_DIR / "workflows_multi.json"
    if not wf_file.exists():
        return {}
    with dispatch_file_lock:
        try:
            return json.loads(wf_file.read_text() or "{}")
        except Exception:
            return {}


def _save_workflow(wf: dict):
    wf_id = wf.get("workflow_id", "")
    wf["updated_at"] = now_iso()
    wf_file = DATA_DIR / "workflows_multi.json"
    with dispatch_file_lock:
        try:
            wfs = json.loads(wf_file.read_text() or "{}") if wf_file.exists() else {}
        except Exception:
            wfs = {}
        if not isinstance(wfs, dict):
            wfs = {}
        wfs[wf_id] = wf
        wf_file.write_text(json.dumps(wfs, indent=2, default=str))



# ── reliability helpers ─────────────────────────────────────────────
def _parse_iso(ts: str) -> float | None:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(str(ts).replace("Z", "+00:00")).timestamp()
    except Exception:
        return None


def _pid_alive(pid) -> bool:
    try:
        pid = int(pid or 0)
    except Exception:
        return False
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _active_dispatch_count() -> int:
    # Count live monitor slots and recent "starting" claims. dispatch_start() writes
    # status=running/process_status=starting before the monitor thread has a PID; that
    # claim must consume capacity immediately or a fast fourth start can race through.
    # Older historical rows may still say "running", so PID-less claims only count
    # for a short startup window.
    with _monitor_lock:
        live_monitors = set(_dispatch_monitors.keys())
    total = 0
    now = time.time()
    for d in _load_dispatch_queue():
        if d.get("dispatch_id") in live_monitors:
            total += 1
            continue
        if d.get("status") not in {"running", "retrying", "cancelling"}:
            continue
        if d.get("process_status") not in {"starting", "running", "retrying", "cancelling"}:
            continue
        if _pid_alive(d.get("pid")):
            total += 1
            continue
        started = _parse_iso(d.get("started_at"))
        if d.get("is_live") and started and (now - started) < 90:
            total += 1
    return total


def _queued_dispatch_count() -> int:
    return sum(1 for d in _load_dispatch_queue() if d.get("status") == "queued")


def _active_workflow_count() -> int:
    # Count workflows consuming live execution capacity, not stale/queued records.
    # Queued dispatches are guarded separately by MAX_QUEUED_DISPATCHES.
    live_dispatch_ids = set()
    with _monitor_lock:
        live_dispatch_ids.update(_dispatch_monitors.keys())
    for d in _load_dispatch_queue():
        if d.get("status") in {"running", "retrying", "cancelling"} and d.get("process_status") in {"starting", "running", "retrying", "cancelling"} and _pid_alive(d.get("pid")):
            live_dispatch_ids.add(d.get("dispatch_id"))
    active_wfs = set()
    for w in _load_workflows().values():
        if w.get("status") != "running" or _wf_elapsed_seconds(w) > MAX_WORKFLOW_RUNTIME_SECONDS:
            continue
        for s in w.get("subtasks", []):
            if s.get("dispatch_id") in live_dispatch_ids:
                active_wfs.add(w.get("workflow_id"))
                break
    return len(active_wfs)


def _workflow_retry_count(wf_id: str) -> int:
    if not wf_id:
        return 0
    total = 0
    for d in _load_dispatch_queue():
        if d.get("workflow_id") == wf_id:
            total += int(d.get("retry_count") or 0)
    return total


def _wf_elapsed_seconds(wf: dict) -> int:
    start_ts = _parse_iso(wf.get("started_at"))
    if not start_ts:
        return 0
    return int(time.time() - start_ts)


def _limit_check(action: str, wf_id: str = "") -> dict:
    if action == "enqueue":
        queued = _queued_dispatch_count()
        if queued >= MAX_QUEUED_DISPATCHES:
            return {"ok": False, "reason": "max_queued_dispatches", "message": f"Queue limit reached: {queued}/{MAX_QUEUED_DISPATCHES}", "queued": queued, "limit": MAX_QUEUED_DISPATCHES}
    if action == "start":
        running = _active_dispatch_count()
        if running >= MAX_CONCURRENT_DISPATCHES:
            return {"ok": False, "reason": "max_concurrent_dispatches", "message": f"Dispatch concurrency limit reached: {running}/{MAX_CONCURRENT_DISPATCHES}", "running": running, "limit": MAX_CONCURRENT_DISPATCHES}
    if action == "workflow_start":
        running = _active_workflow_count()
        # allow an already-running workflow to continue dispatching its ready steps
        if wf_id:
            wf = _get_workflow_fn(wf_id) if _get_workflow_fn else None
            if wf and wf.get("status") == "running":
                return {"ok": True}
        if running >= MAX_CONCURRENT_WORKFLOWS:
            return {"ok": False, "reason": "max_concurrent_workflows", "message": f"Workflow concurrency limit reached: {running}/{MAX_CONCURRENT_WORKFLOWS}", "running": running, "limit": MAX_CONCURRENT_WORKFLOWS}
    if action == "workflow_runtime" and wf_id:
        wf = _get_workflow_fn(wf_id) if _get_workflow_fn else None
        if wf and wf.get("status") == "running" and _wf_elapsed_seconds(wf) > MAX_WORKFLOW_RUNTIME_SECONDS:
            return {"ok": False, "reason": "max_workflow_runtime_seconds", "message": f"Workflow runtime exceeded {MAX_WORKFLOW_RUNTIME_SECONDS}s", "elapsed_seconds": _wf_elapsed_seconds(wf), "limit": MAX_WORKFLOW_RUNTIME_SECONDS}
    if action == "workflow_retry" and wf_id:
        retries = _workflow_retry_count(wf_id)
        if retries >= MAX_RETRIES_PER_WORKFLOW:
            return {"ok": False, "reason": "max_retries_per_workflow", "message": f"Workflow retry limit reached: {retries}/{MAX_RETRIES_PER_WORKFLOW}", "retry_count": retries, "limit": MAX_RETRIES_PER_WORKFLOW}
    return {"ok": True}


def _step_retry_policy(st: dict | None, payload: dict | None = None) -> dict:
    payload = payload or {}
    st = st or {}
    policy = dict(st.get("retry_policy") or {})
    policy.update(payload.get("retry_policy") or {})
    return {
        "retry_count": int(policy.get("retry_count", st.get("max_retries", MAX_RETRIES)) or 0),
        "retry_delay_seconds": int(policy.get("retry_delay_seconds", st.get("retry_delay_seconds", RETRY_DELAY)) or 0),
        "retry_on": list(policy.get("retry_on", st.get("retry_on", RETRYABLE_FAILURES_DEFAULT)) or []),
    }


def _normalize_failure_reason(reason: str) -> str:
    reason = str(reason or "unknown_error").strip().lower()
    return reason if reason in FAILURE_REASONS else "unknown_error"


def _classify_failure(status: str, exit_code=None, stdout_tail=None, stderr_tail=None, error_message: str = "") -> str:
    text = "\n".join([str(error_message or ""), "\n".join(stdout_tail or []), "\n".join(stderr_tail or [])]).lower()
    if status == "timed_out" or "timed out" in text or "timeout" in text:
        return "timeout"
    if status == "cancelled" or "cancel" in text:
        return "cancelled"
    if exit_code == 127 or "command not found" in text or "no such file or directory" in text:
        return "command_not_found"
    if "rate limit" in text or "429" in text or "too many requests" in text:
        return "rate_limited"
    if "permission denied" in text or "forbidden" in text or "unauthorized" in text or "401" in text or "403" in text:
        return "permission_error"
    if "provider" in text or "model" in text or "openrouter" in text or "anthropic" in text or "deepseek" in text:
        return "provider_error"
    if exit_code not in (None, 0):
        return "nonzero_exit"
    if status == "failed" and not (stdout_tail or stderr_tail or error_message):
        return "empty_output"
    if status == "failed":
        return "unknown_error"
    return _normalize_failure_reason(status)


def _find_subtask(wf: dict, st_id: str) -> dict | None:
    return next((s for s in wf.get("subtasks", []) if s.get("id") == st_id), None)


def _duration_seconds(start_time: str, end_time: str = "") -> int:
    start = _parse_iso(start_time)
    end = _parse_iso(end_time) or time.time()
    return int(end - start) if start else 0


def _sync_step_from_dispatch(dispatch_id: str, patch: dict | None = None, event_type: str = "step_update"):
    disp = _find_dispatch(dispatch_id)
    if not disp or not disp.get("workflow_id") or not disp.get("subtask_id") or not _get_workflow_fn:
        return
    wf = _get_workflow_fn(disp.get("workflow_id"))
    if not wf:
        return
    st = _find_subtask(wf, disp.get("subtask_id"))
    if not st:
        return
    if st.get("status") == "skipped":
        return
    snapshot = {
        "step_id": st.get("id"),
        "step_name": st.get("title"),
        "status": disp.get("status", st.get("status")),
        "process_status": disp.get("process_status"),
        "dispatch_id": dispatch_id,
        "pid": disp.get("pid"),
        "start_time": disp.get("started_at") or st.get("started_at"),
        "end_time": disp.get("finished_at") or st.get("completed_at"),
        "duration_seconds": disp.get("elapsed_seconds") if disp.get("elapsed_seconds") is not None else _duration_seconds(st.get("started_at")),
        "timeout_seconds": disp.get("timeout_seconds"),
        "exit_code": disp.get("exit_code"),
        "retry_attempt": int(disp.get("retry_count") or 0),
        "max_retries": int(disp.get("max_retries") or 0),
        "failure_reason": disp.get("failure_reason") or st.get("failure_reason"),
        "last_output_chunk": disp.get("last_output_chunk", ""),
        "last_error_chunk": disp.get("last_error_chunk", ""),
        "stdout_tail": disp.get("stdout_tail", []),
        "stderr_tail": disp.get("stderr_tail", []),
    }
    if patch:
        snapshot.update(patch)
    st.update(snapshot)
    st.setdefault("attempt_history", [])
    if event_type in {"dispatch_completed", "dispatch_failed", "dispatch_timed_out", "dispatch_cancelled", "dispatch_retrying", "step_skipped"}:
        st["attempt_history"].append(dict(snapshot, event_type=event_type, recorded_at=now_iso()))
    if snapshot.get("status") in {"failed", "timed_out", "retry_exhausted", "cancelled"}:
        st["status"] = snapshot.get("status")
    elif snapshot.get("status") == "completed":
        st["status"] = "completed"
    elif snapshot.get("status") in {"running", "retrying", "cancelling"}:
        st["status"] = snapshot.get("status")
    _save_workflow(wf)


def _event_snapshot(dispatch_id: str) -> dict:
    disp = _find_dispatch(dispatch_id) or {}
    return {
        "pid": disp.get("pid"),
        "process_status": disp.get("process_status"),
        "start_time": disp.get("started_at"),
        "end_time": disp.get("finished_at"),
        "duration_seconds": disp.get("elapsed_seconds"),
        "timeout_seconds": disp.get("timeout_seconds"),
        "exit_code": disp.get("exit_code"),
        "retry_attempt": int(disp.get("retry_count") or 0),
        "max_retries": int(disp.get("max_retries") or 0),
        "failure_reason": disp.get("failure_reason"),
        "last_output_chunk": disp.get("last_output_chunk", ""),
        "last_error_chunk": disp.get("last_error_chunk", ""),
        "stdout_tail": disp.get("stdout_tail", []),
        "stderr_tail": disp.get("stderr_tail", []),
    }


def _should_retry(disp: dict, failure_reason: str) -> tuple[bool, str]:
    if failure_reason == "cancelled" or disp.get("status") == "cancelled":
        return False, "cancelled steps are not retried"
    retry_count = int(disp.get("retry_count") or 0)
    max_retries = int(disp.get("max_retries") or 0)
    retry_on = list(disp.get("retry_on") or [])
    wf_id = disp.get("workflow_id", "")
    if retry_count >= max_retries:
        return False, "max step retries reached"
    if failure_reason not in retry_on:
        return False, f"failure_reason {failure_reason} not in retry_on"
    if failure_reason in {"validation_error", "command_not_found", "permission_error"} and failure_reason not in retry_on:
        return False, f"{failure_reason} requires explicit retry_on"
    limit = _limit_check("workflow_retry", wf_id)
    if not limit.get("ok"):
        return False, limit.get("message", "workflow retry limit reached")
    return True, "retry allowed"

# ═══════════════════════════════════════════════════════════════════
# PARALLEL DISPATCH (Phase 1)
# ═══════════════════════════════════════════════════════════════════

def workflow_dispatch_parallel(wf_id: str) -> dict:
    """Dispatch ALL ready (unblocked, queued) subtasks in parallel.
    Independent subtasks run simultaneously. Dependent subtasks wait.
    Returns immediately — execution happens in background threads."""
    if not _get_workflow_fn:
        return {"ok": False, "error": "Workflow functions not registered"}

    wf = _get_workflow_fn(wf_id)
    if not wf:
        return {"ok": False, "error": "Workflow not found"}

    if wf.get("status") not in {"draft", "paused", "running"}:
        return {"ok": False, "error": f"Workflow is {wf.get('status')}"}
    limit = _limit_check("workflow_start", wf_id)
    if not limit.get("ok"):
        return {"ok": False, "blocked_by": limit.get("reason"), "error": limit.get("message"), "limits": limit}
    runtime_limit = _limit_check("workflow_runtime", wf_id)
    if not runtime_limit.get("ok"):
        wf["status"] = "failed"
        wf["failure_reason"] = runtime_limit.get("reason")
        wf["error"] = {"message": runtime_limit.get("message")}
        _save_workflow(wf)
        return {"ok": False, "blocked_by": runtime_limit.get("reason"), "error": runtime_limit.get("message"), "workflow": wf}

    # Start workflow if needed
    if wf.get("status") in {"draft", "paused"}:
        wf["status"] = "running"
        wf["started_at"] = now_iso()
        _save_workflow(wf)
        _emit_wf_event(wf_id, "", "", "coordinator", "workflow_started", "running",
                       f"Parallel dispatch started: {wf.get('title', '?')}")
        _send_parallel_start_telegram(wf)

    # Find ready (unblocked) subtasks
    ready = []
    for st in wf.get("subtasks", []):
        if st.get("status") != "queued":
            continue
        deps_met = True
        for dep in st.get("depends_on", []):
            dep_st = next((s for s in wf.get("subtasks", [])
                          if s.get("profile") == dep or s.get("id") == dep), None)
            if dep_st and dep_st.get("status") not in ("completed",):
                deps_met = False
                if st.get("status") != "waiting":
                    st["status"] = "waiting"
                    _emit_wf_event(wf_id, "", st.get("id", ""), st.get("profile", "?"),
                                   "dependency_waiting", "waiting",
                                   f"Waiting for: {', '.join(st.get('depends_on', []))}")
                break
        if deps_met:
            ready.append(st)

    if not ready:
        waiting = sum(1 for s in wf.get("subtasks", []) if s.get("status") == "waiting")
        return {"ok": True, "workflow": wf, "dispatched": 0,
                "message": f"No unblocked subtasks ({waiting} waiting)" if waiting else "No ready subtasks"}

    # Mark ready subtasks as running BEFORE spawning threads (race-safe)
    for st in ready[:MAX_PARALLEL]:
        st["status"] = "running"
        st["started_at"] = now_iso()
    _save_workflow(wf)

    # Dispatch in parallel threads
    results = []
    threads = []

    def _dispatch_one(subtask):
        _parallel_semaphore.acquire()
        try:
            if _start_run_fn:
                _start_run_fn({
                    "title": subtask["title"],
                    "trigger_source": "workflow",
                    "service": "mission-control",
                    "profile": subtask["profile"],
                    "current_step": "executing",
                    "related_task_id": subtask["id"],
                    "input": {"workflow_id": wf_id, "subtask_id": subtask["id"]},
                })
            policy = _step_retry_policy(subtask)
            enq = enqueue_dispatch({
                "workflow_id": wf_id,
                "subtask_id": subtask["id"],
                "profile": subtask["profile"],
                "title": subtask["title"],
                "type": "subtask",
                "timeout_seconds": subtask.get("timeout_seconds"),
                "retry_policy": policy,
                "test_mode": subtask.get("test_mode", ""),
                "prompt": subtask.get("prompt", ""),
            })
            if not enq.get("ok"):
                return {"subtask_id": subtask["id"], "profile": subtask["profile"], "ok": False, "error": enq.get("error"), "blocked_by": enq.get("blocked_by")}
            did = enq["dispatch"]["dispatch_id"]
            subtask["dispatch_id"] = did
            result = dispatch_start(did)
            return {"subtask_id": subtask["id"], "profile": subtask["profile"],
                    "dispatch_id": did, "ok": result.get("ok", False), "error": result.get("error"), "blocked_by": result.get("blocked_by")}
        finally:
            _parallel_semaphore.release()

    for st in ready[:MAX_PARALLEL]:
        t = threading.Thread(target=lambda s=st: results.append(_dispatch_one(s)), daemon=True)
        t.start()
        threads.append(t)

    # Do not join background dispatch threads here. API callers need an immediate
    # response; live status and step timeline are updated by each monitor thread.
    return {"ok": True, "workflow": wf, "dispatched": len(ready[:MAX_PARALLEL]), "results": results,
            "message": f"Started {len(ready[:MAX_PARALLEL])} subtasks in background (max {MAX_PARALLEL})"}


# Legacy sequential API — routes to parallel now
workflow_dispatch_all_ready = workflow_dispatch_parallel


def workflow_dispatch_next(wf_id: str) -> dict:
    """Dispatch the next single ready subtask."""
    if not _get_workflow_fn:
        return {"ok": False, "error": "Workflow functions not registered"}
    wf = _get_workflow_fn(wf_id)
    if not wf:
        return {"ok": False, "error": "Workflow not found"}

    for st in wf.get("subtasks", []):
        if st.get("status") != "queued":
            continue
        deps_met = True
        for dep in st.get("depends_on", []):
            dep_st = next((s for s in wf.get("subtasks", [])
                          if s.get("profile") == dep or s.get("id") == dep), None)
            if dep_st and dep_st.get("status") != "completed":
                deps_met = False
                break
        if not deps_met:
            continue

        if _start_subtask_fn:
            _start_subtask_fn(wf_id, st["id"])
        policy = _step_retry_policy(st)
        enq = enqueue_dispatch({
            "workflow_id": wf_id, "subtask_id": st["id"],
            "profile": st["profile"], "title": st["title"], "type": "subtask",
            "timeout_seconds": st.get("timeout_seconds"),
            "retry_policy": policy,
            "test_mode": st.get("test_mode", ""),
            "prompt": st.get("prompt", ""),
        })
        if not enq.get("ok"):
            return {"ok": False, "error": enq.get("error"), "blocked_by": enq.get("blocked_by"), "limits": enq.get("limits")}
        did = enq["dispatch"]["dispatch_id"]
        st["dispatch_id"] = did
        _save_workflow(wf)
        result = dispatch_start(did)
        return {"ok": result.get("ok", False), "dispatch_id": did, "result": result}

    return {"ok": False, "error": "No ready subtasks"}


# ═══════════════════════════════════════════════════════════════════
# PROMPT BUILDING
# ═══════════════════════════════════════════════════════════════════

def build_dispatch_prompt(profile: str, title: str, context: dict = None) -> str:
    context = context or {}
    templates = {
        "Coder": f"""You are the Coder profile of Hermes. Execute this task:\n\nTask: {title}\n\nFollow best practices: read context first, test your changes, verify with real output.\nReport: what you did, what changed, what to check.\nFiles: {context.get('files_affected', 'unknown')}\nRepo: {context.get('repo_path', '/root')}\n\nKeep it concise. Produce working artifacts, not explanations.""",
        "ContentCreator": f"""You are the ContentCreator profile of Hermes. Create content for this task:\n\nTask: {title}\n\nPlatform: {context.get('platform', 'x')}\nAudience: {context.get('audience', 'devops')}\nFormat: {context.get('format', 'post')}\nTone: {context.get('tone', 'practical')}\n\nProduce publish-ready content with hooks, captions, and image prompts if needed.""",
        "DeepResearch": f"""You are the DeepResearch profile of Hermes. Research this topic:\n\nQuestion: {title}\n\nDecision to support: {context.get('decision', 'general knowledge')}\nSource requirements: {context.get('source_requirements', 'primary preferred')}\nOutput format: {context.get('output_format', 'brief')}\n\nProduce a structured research brief with findings, sources, and recommendations.""",
        "MarketAnalyst": f"""You are the MarketAnalyst profile of Hermes. Analyze this:\n\nTask: {title}\n\nAsset type: {context.get('asset_type', 'stock')}\nMarket: {context.get('market', 'nse')}\nTime horizon: {context.get('time_horizon', 'medium')}\nAnalysis type: {context.get('analysis_type', 'fundamental')}\n\nProduce analysis with key metrics, technicals if relevant, and clear recommendations.""",
        "Tutor": f"""You are the Tutor profile of Hermes. Teach this topic:\n\nTopic: {title}\n\nDifficulty: {context.get('difficulty_level', 'intermediate')}\nInclude quiz: {context.get('quiz_required', False)}\nInclude diagrams: {context.get('diagram_required', False)}\n\nUse simple sections, examples, memory hooks, and a quiz at the end. Teach, don't lecture.""",
    }
    return sanitize_output(
        templates.get(profile, f"Execute this task as {profile} profile:\n\n{title}"), 5000)


# ═══════════════════════════════════════════════════════════════════
# DISPATCH QUEUE / LIFECYCLE
# ═══════════════════════════════════════════════════════════════════

def enqueue_dispatch(payload: dict) -> dict:
    wf_id = str(payload.get("workflow_id") or "")
    st_id = str(payload.get("subtask_id") or "")
    profile = str(payload.get("profile") or "Default")
    title = str(payload.get("title") or "Dispatch task")
    ptype = str(payload.get("type") or "subtask")

    limit = _limit_check("enqueue", wf_id)
    if not limit.get("ok"):
        return {"ok": False, "blocked_by": limit.get("reason"), "error": limit.get("message"), "limits": limit}
    wf = _get_workflow_fn(wf_id) if wf_id and _get_workflow_fn else None
    workflow_title = wf.get("title", title) if wf else title
    st = _find_subtask(wf, st_id) if wf and st_id else None
    retry_policy = _step_retry_policy(st, payload)

    prompt = str(payload.get("prompt") or (st or {}).get("prompt") or build_dispatch_prompt(profile, title, payload.get("context") or {}))

    hermes_available = shutil.which("hermes") is not None

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
        "is_live": False,
        "retry_count": 0,
        "max_retries": retry_policy["retry_count"],
        "retry_delay_seconds": retry_policy["retry_delay_seconds"],
        "retry_on": retry_policy["retry_on"],
        "retry_policy": retry_policy,
        "retry_history": [],
        "failure_reason": None,
        "pid": None,
        "process_status": "queued",
        "elapsed_seconds": 0,
        "timeout_seconds": int(payload.get("timeout_seconds") or (st or {}).get("timeout_seconds") or DISPATCH_TIMEOUT),
        "exit_code": None,
        "last_heartbeat_at": None,
        "last_output_chunk": "",
        "last_error_chunk": "",
        "stdout_tail": [],
        "stderr_tail": [],
        "test_mode": str(payload.get("test_mode") or ""),
    }

    result = _append_dispatch(dispatch)

    # Fire-and-forget telegram (hermes send can block)
    threading.Thread(target=lambda: _dispatch_telegram(result, "dispatched"), daemon=True).start()

    if _append_action_log_fn:
        _append_action_log_fn({
            "service": "mission-control", "action": "enqueue_dispatch", "risk": "safe",
            "status": "success",
            "output": f"Dispatch {result['dispatch_id']} queued for {profile}"
        })

    _emit_wf_event(wf_id, result["dispatch_id"], st_id, profile,
                   "dispatch_queued", "queued", f"Dispatch queued: {title}")

    return {"ok": True, "dispatch": result, "hermes_available": hermes_available}


def get_dispatches(status_filter: str = "") -> list[dict]:
    items = _load_dispatch_queue()
    if status_filter:
        items = [i for i in items if i.get("status") == status_filter]
    items.sort(key=lambda i: i.get("created_at", ""), reverse=True)
    return items


def get_dispatch(dispatch_id: str) -> dict | None:
    return _find_dispatch(dispatch_id)


def get_active_dispatches() -> list[dict]:
    return [d for d in _load_dispatch_queue()
            if d.get("status") in ("queued", "running", "retrying")]


def dispatch_start(dispatch_id: str) -> dict:
    """Start a dispatch (non-blocking — returns immediately after spawning monitor)."""
    disp = _find_dispatch(dispatch_id)
    if not disp:
        return {"ok": False, "error": "Dispatch not found"}
    if disp.get("status") not in ("queued", "failed", "retrying"):
        return {"ok": False, "error": f"Dispatch is {disp.get('status')}"}
    limit = _limit_check("start", disp.get("workflow_id", ""))
    if not limit.get("ok"):
        _update_dispatch(dispatch_id, {"blocked_by": limit.get("reason"), "blocked_reason": limit.get("message"), "process_status": "queued"})
        return {"ok": False, "blocked_by": limit.get("reason"), "error": limit.get("message"), "limits": limit}

    profile = disp.get("profile", "Default")
    prompt = disp.get("prompt", "")

    patch = {
        "status": "running",
        "process_status": "starting",
        "started_at": now_iso(),
        "finished_at": None,
        "dispatch_method": "hermes_cli",
        "is_live": True,
        "pid": None,
        "exit_code": None,
        "elapsed_seconds": 0,
        "timeout_seconds": int(disp.get("timeout_seconds") or DISPATCH_TIMEOUT),
        "last_heartbeat_at": now_iso(),
        "last_output_chunk": "",
        "last_error_chunk": "",
        "stdout_tail": [],
        "stderr_tail": [],
    }
    _update_dispatch(dispatch_id, patch)
    _sync_step_from_dispatch(dispatch_id, event_type="dispatch_started")

    if _start_run_fn:
        run = _start_run_fn({
            "title": disp.get("title", "Dispatch"),
            "trigger_source": "dispatch",
            "service": "mission-control",
            "profile": profile,
            "current_step": "executing",
            "input": {"dispatch_id": dispatch_id},
        })
        _update_dispatch(dispatch_id, {"run_id": run.get("run_id")})

    _emit_wf_event(disp.get("workflow_id", ""), dispatch_id,
                   disp.get("subtask_id", ""), profile,
                   "dispatch_started", "running",
                   f"Dispatch started: {profile}")

    # Start monitor in background
    _start_hermes_dispatch(dispatch_id, profile, prompt, disp)

    return {"ok": True, "dispatch": disp, "message": "Dispatch started in background"}


# ═══════════════════════════════════════════════════════════════════
# NEAR-LIVE STATUS (Phase 2) — background subprocess with heartbeat
# ═══════════════════════════════════════════════════════════════════

def _build_dispatch_command(profile: str, prompt: str, disp: dict) -> tuple[list[str], int, str]:
    """Build command for dispatch. Default is the real Hermes CLI command.

    Test modes are only for safe streaming verification and never replace the real default:
    hermes -p <profile> chat -q "<prompt>" --quiet --max-turns=10
    """
    test_mode = str(disp.get("test_mode") or "").strip().lower()
    timeout = int(disp.get("timeout_seconds") or DISPATCH_TIMEOUT)
    if test_mode == "success":
        return ["python3", "-u", "-c", "print('step-success', flush=True)"], timeout, "success_test"
    if test_mode == "streaming":
        return ["python3", "-u", "-c", "import time; [print(f'stream-line-{i}', flush=True) or time.sleep(2) for i in range(5)]"], timeout, "streaming_test"
    if test_mode == "stderr":
        return ["python3", "-u", "-c", "import sys,time; [print(f'err-line-{i}', file=sys.stderr, flush=True) or time.sleep(1) for i in range(3)]"], timeout, "stderr_test"
    if test_mode == "timeout":
        return ["python3", "-u", "-c", "import time; print('timeout-start', flush=True); time.sleep(60); print('timeout-end', flush=True)"], timeout, "timeout_test"
    if test_mode == "fail_once":
        retry_count = int(disp.get("retry_count") or 0)
        if retry_count <= 0:
            return ["python3", "-u", "-c", "import sys; print('first-attempt-failed', file=sys.stderr, flush=True); sys.exit(2)"], timeout, "fail_once_test"
        return ["python3", "-u", "-c", "print('retry-success', flush=True)"], timeout, "fail_once_test"
    if test_mode == "fail_always":
        return ["python3", "-u", "-c", "import sys; print('always-fails', file=sys.stderr, flush=True); sys.exit(2)"], timeout, "fail_always_test"
    if test_mode == "rate_limited":
        return ["python3", "-u", "-c", "import sys; print('429 rate limit from provider', file=sys.stderr, flush=True); sys.exit(2)"], timeout, "rate_limit_test"
    if test_mode == "empty_output":
        return ["python3", "-u", "-c", ""], timeout, "empty_output_test"
    cli_profile = _normalize_cli_profile(profile)
    return ["hermes", "-p", cli_profile, "chat", "-q", prompt, "--quiet", f"--max-turns={DISPATCH_MAX_TURNS}"], timeout, "hermes_cli"


def _start_hermes_dispatch(dispatch_id: str, profile: str, prompt: str, disp: dict | None = None):
    """Launch dispatch command in a Popen-backed monitor thread."""
    disp = disp or _find_dispatch(dispatch_id) or {}
    cmd, timeout, method = _build_dispatch_command(profile, prompt, disp)
    state = {
        "dispatch_id": dispatch_id,
        "profile": profile,
        "cmd": cmd,
        "timeout_seconds": timeout,
        "dispatch_method": method,
        "started": time.time(),
        "process": None,
        "cancel_requested": threading.Event(),
    }
    with _monitor_lock:
        _dispatch_monitors[dispatch_id] = state
    monitor = threading.Thread(target=_monitor_dispatch, args=(state,), daemon=True)
    state["thread"] = monitor
    monitor.start()


def _reader_thread(stream, stream_name: str, line_queue: queue.Queue):
    try:
        for line in iter(stream.readline, ''):
            if line == '':
                break
            line_queue.put((stream_name, line.rstrip('\n')))
    except Exception as e:
        line_queue.put((stream_name, f"[reader-error] {e}"))
    finally:
        try:
            stream.close()
        except Exception:
            pass


def _tail_append(tail: list[str], line: str, limit: int = 80) -> list[str]:
    tail = list(tail or [])
    tail.append(sanitize_output(line, 2000))
    return tail[-limit:]


def _terminate_process(proc: subprocess.Popen, grace_seconds: float = 3.0) -> str:
    if proc.poll() is not None:
        return "already_exited"
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except Exception:
        try:
            proc.terminate()
        except Exception:
            pass
    deadline = time.time() + grace_seconds
    while time.time() < deadline:
        if proc.poll() is not None:
            return "terminated"
        time.sleep(0.1)
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass
    return "killed"


def _monitor_dispatch(state: dict):
    """Run subprocess.Popen, stream stdout/stderr, enforce timeout and cancel."""
    dispatch_id = state["dispatch_id"]
    cmd = state["cmd"]
    start = state["started"]
    timeout = int(state.get("timeout_seconds") or DISPATCH_TIMEOUT)
    line_queue: queue.Queue = queue.Queue()
    stdout_tail: list[str] = []
    stderr_tail: list[str] = []
    final_status = "failed"
    exit_code = None
    combined_output = ""
    final_error = ""
    proc = None
    try:
        _update_dispatch(dispatch_id, {
            "process_status": "starting",
            "timeout_seconds": timeout,
            "dispatch_method": state.get("dispatch_method", "hermes_cli"),
            "command": " ".join(cmd[:4]) + " ..." if len(cmd) > 4 else " ".join(cmd),
            "is_live": True,
            "last_heartbeat_at": now_iso(),
        })
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.DEVNULL,
            text=True,
            bufsize=1,
            universal_newlines=True,
            start_new_session=True,
        )
        state["process"] = proc
        _update_dispatch(dispatch_id, {
            "pid": proc.pid,
            "process_status": "running",
            "status": "running",
            "is_live": True,
            "last_heartbeat_at": now_iso(),
        })
        for stream, name in ((proc.stdout, "stdout"), (proc.stderr, "stderr")):
            threading.Thread(target=_reader_thread, args=(stream, name, line_queue), daemon=True).start()

        last_heartbeat_elapsed = -1
        while True:
            drained = False
            while True:
                try:
                    stream_name, line = line_queue.get_nowait()
                except queue.Empty:
                    break
                drained = True
                combined_output += line + "\n"
                elapsed = int(time.time() - start)
                if stream_name == "stdout":
                    stdout_tail = _tail_append(stdout_tail, line)
                    _update_dispatch(dispatch_id, {
                        "stdout_tail": stdout_tail,
                        "last_output_chunk": line,
                        "elapsed_seconds": elapsed,
                        "last_heartbeat_at": now_iso(),
                        "is_live": True,
                        "process_status": "running",
                    })
                    _sync_step_from_dispatch(dispatch_id, event_type="step_output")
                else:
                    stderr_tail = _tail_append(stderr_tail, line)
                    _update_dispatch(dispatch_id, {
                        "stderr_tail": stderr_tail,
                        "last_error_chunk": line,
                        "elapsed_seconds": elapsed,
                        "last_heartbeat_at": now_iso(),
                        "is_live": True,
                        "process_status": "running",
                    })
                    _sync_step_from_dispatch(dispatch_id, event_type="step_error")

            elapsed = int(time.time() - start)
            current = _find_dispatch(dispatch_id) or {}
            cancel_requested = bool(state.get("cancel_requested") and state["cancel_requested"].is_set())
            cancel_requested = cancel_requested or current.get("process_status") == "cancelling" or current.get("status") == "cancelling"
            if cancel_requested:
                _update_dispatch(dispatch_id, {"process_status": "cancelling", "status": "cancelling", "elapsed_seconds": elapsed})
                _terminate_process(proc)
                exit_code = proc.poll()
                final_status = "cancelled"
                break
            if elapsed >= timeout and proc.poll() is None:
                _update_dispatch(dispatch_id, {"process_status": "timed_out", "elapsed_seconds": elapsed})
                _terminate_process(proc)
                exit_code = proc.poll()
                final_status = "timed_out"
                final_error = f"Dispatch timed out after {timeout}s"
                break
            exit_code = proc.poll()
            if exit_code is not None:
                final_status = "completed" if exit_code == 0 else "failed"
                break
            if not drained:
                if elapsed != last_heartbeat_elapsed:
                    _update_dispatch(dispatch_id, {
                        "elapsed_seconds": elapsed,
                        "last_heartbeat_at": now_iso(),
                        "is_live": True,
                        "process_status": "running",
                    })
                    _sync_step_from_dispatch(dispatch_id, event_type="step_heartbeat")
                    last_heartbeat_elapsed = elapsed
                time.sleep(0.2)

        time.sleep(0.1)
        while True:
            try:
                stream_name, line = line_queue.get_nowait()
            except queue.Empty:
                break
            combined_output += line + "\n"
            if stream_name == "stdout":
                stdout_tail = _tail_append(stdout_tail, line)
            else:
                stderr_tail = _tail_append(stderr_tail, line)
        exit_code = proc.poll() if proc else exit_code
        elapsed = int(time.time() - start)
        _update_dispatch(dispatch_id, {
            "exit_code": exit_code,
            "elapsed_seconds": elapsed,
            "stdout_tail": stdout_tail,
            "stderr_tail": stderr_tail,
            "last_output_chunk": stdout_tail[-1] if stdout_tail else "",
            "last_error_chunk": stderr_tail[-1] if stderr_tail else "",
            "is_live": False if final_status in {"completed", "failed", "cancelled", "timed_out"} else True,
        })
        if final_status == "completed":
            session_id, response = _extract_session(combined_output)
            _finalize_dispatch(dispatch_id, "completed", session_id, response or "Process completed")
            _update_dispatch(dispatch_id, {"process_status": "completed", "exit_code": exit_code})
        elif final_status == "cancelled":
            _finalize_cancelled(dispatch_id, exit_code, stdout_tail, stderr_tail)
        elif final_status == "timed_out":
            _finalize_timed_out(dispatch_id, final_error, exit_code, stdout_tail, stderr_tail)
        else:
            err = "\n".join(stderr_tail[-20:]).strip() or f"Exit code {exit_code}"
            reason = _classify_failure("failed", exit_code=exit_code, stdout_tail=stdout_tail, stderr_tail=stderr_tail, error_message=err)
            _update_dispatch(dispatch_id, {"failure_reason": reason})
            _finalize_dispatch(dispatch_id, "failed", "", err, failure_reason=reason)
            _update_dispatch(dispatch_id, {"process_status": "failed", "exit_code": exit_code})
    except FileNotFoundError as e:
        _update_dispatch(dispatch_id, {"process_status": "failed", "is_live": False, "last_error_chunk": str(e)[:500], "failure_reason": "command_not_found"})
        _finalize_dispatch(dispatch_id, "failed", "", f"Command not found: {str(e)[:300]}", failure_reason="command_not_found")
    except Exception as e:
        reason = _classify_failure("failed", error_message=str(e))
        _update_dispatch(dispatch_id, {"process_status": "failed", "is_live": False, "last_error_chunk": str(e)[:500], "failure_reason": reason})
        _finalize_dispatch(dispatch_id, "failed", "", f"Monitor error: {str(e)[:300]}", failure_reason=reason)
    finally:
        with _monitor_lock:
            _dispatch_monitors.pop(dispatch_id, None)


def _finalize_cancelled(dispatch_id: str, exit_code, stdout_tail: list[str], stderr_tail: list[str]):
    disp = _find_dispatch(dispatch_id)
    if not disp:
        return
    patch = {
        "status": "cancelled",
        "process_status": "cancelled",
        "exit_code": exit_code,
        "finished_at": now_iso(),
        "is_live": False,
        "stdout_tail": stdout_tail,
        "stderr_tail": stderr_tail,
        "error": {},
        "failure_reason": "cancelled",
    }
    updated = _update_dispatch(dispatch_id, patch)
    if disp.get("run_id") and _finish_run_fn:
        _finish_run_fn(disp["run_id"], {"status": "cancelled", "output": {"stdout_tail": stdout_tail, "stderr_tail": stderr_tail}})
    _dispatch_telegram(updated, "cancelled")
    _sync_step_from_dispatch(dispatch_id, {"failure_reason": "cancelled"}, event_type="dispatch_cancelled")
    _emit_wf_event(disp.get("workflow_id", ""), dispatch_id, disp.get("subtask_id", ""),
                   disp.get("profile", "?"), "dispatch_cancelled", "cancelled", "Dispatch cancelled")
    _auto_fail_subtask(dict(disp, error={"message": "Dispatch cancelled", "failure_reason": "cancelled"}, failure_reason="cancelled"))


def _finalize_timed_out(dispatch_id: str, message: str, exit_code, stdout_tail: list[str], stderr_tail: list[str]):
    disp = _find_dispatch(dispatch_id)
    if not disp:
        return
    error = {"message": sanitize_output(message, 500), "failure_reason": "timeout"}
    patch = {
        "status": "timed_out",
        "process_status": "timed_out",
        "exit_code": exit_code,
        "finished_at": now_iso(),
        "is_live": False,
        "stdout_tail": stdout_tail,
        "stderr_tail": stderr_tail,
        "error": error,
        "output": {"response": sanitize_output("\n".join(stdout_tail[-40:]), 4000)},
        "failure_reason": "timeout",
    }
    updated = _update_dispatch(dispatch_id, patch)
    if disp.get("run_id") and _finish_run_fn:
        _finish_run_fn(disp["run_id"], {"status": "failed", "error": error, "output": patch["output"]})
    _dispatch_telegram(updated, "failed")
    _sync_step_from_dispatch(dispatch_id, {"failure_reason": "timeout"}, event_type="dispatch_timed_out")
    _emit_wf_event(disp.get("workflow_id", ""), dispatch_id, disp.get("subtask_id", ""),
                   disp.get("profile", "?"), "dispatch_timed_out", "timed_out", message)
    retry_ok, retry_reason = _should_retry(updated, "timeout")
    if retry_ok:
        _schedule_retry(updated, "timeout", message)
    else:
        _auto_fail_subtask(dict(updated, error=error, failure_reason="timeout"))
        _check_wf_deps(updated)


def _extract_session(output: str) -> tuple[str, str]:
    m = re.search(r'session_id:\s*(\S+)', output)
    if m:
        session_id = m.group(1)
        response = re.sub(r'\n?\s*session_id:\s*\S+\s*', '', output).strip()
        return session_id, response
    return "", output.strip()


def get_dispatch_live(dispatch_id: str) -> dict:
    """Return live status for a running dispatch."""
    disp = _find_dispatch(dispatch_id)
    if not disp:
        return {"ok": False, "error": "Dispatch not found"}
    return {
        "ok": True,
        "dispatch_id": dispatch_id,
        "status": disp.get("status"),
        "is_live": disp.get("is_live", False),
        "elapsed_seconds": disp.get("elapsed_seconds", 0),
        "last_heartbeat_at": disp.get("last_heartbeat_at"),
        "pid": disp.get("pid"),
        "process_status": disp.get("process_status"),
        "timeout_seconds": disp.get("timeout_seconds", DISPATCH_TIMEOUT),
        "exit_code": disp.get("exit_code"),
        "last_output_chunk": disp.get("last_output_chunk", ""),
        "last_error_chunk": disp.get("last_error_chunk", ""),
        "stdout_tail": disp.get("stdout_tail", []),
        "stderr_tail": disp.get("stderr_tail", []),
        "retry_count": disp.get("retry_count", 0),
        "max_retries": disp.get("max_retries", 0),
        "retry_on": disp.get("retry_on", []),
        "failure_reason": disp.get("failure_reason"),
    }


def get_dispatch_logs(dispatch_id: str) -> dict:
    disp = _find_dispatch(dispatch_id)
    if not disp:
        return {"ok": False, "error": "Dispatch not found"}
    session_id = disp.get("session_id", "")
    logs = ""
    if session_id:
        state_db = HERMES_HOME / "state.db"
        if state_db.exists():
            code, out = _run(
                ["bash", "-lc",
                 f"sqlite3 {state_db} \"select content from messages where session_id=(select id from sessions where session_id='{session_id}' limit 1) order by id desc limit 20\" 2>/dev/null"],
                timeout=5)
            if code == 0 and out:
                logs = sanitize_output(out, 5000)
    return {
        "ok": True, "dispatch_id": dispatch_id, "session_id": session_id,
        "logs": logs or "No session logs available", "has_logs": bool(logs),
        "stdout_tail": disp.get("stdout_tail", ""),
        "stderr_tail": disp.get("stderr_tail", ""),
    }


# ═══════════════════════════════════════════════════════════════════
# AUTOMATED RETRY (Phase 3)
# ═══════════════════════════════════════════════════════════════════

def _finalize_dispatch(dispatch_id: str, status: str, session_id: str, output_or_error: str, failure_reason: str = ""):
    """Finalize a dispatch: success or check retry policy."""
    disp = _find_dispatch(dispatch_id)
    if not disp:
        return

    if status == "completed":
        patch = {
            "status": "completed",
            "session_id": session_id,
            "output": {"session_id": session_id, "response": sanitize_output(output_or_error, 8000)} if output_or_error else {},
            "error": {},
            "finished_at": now_iso(),
            "is_live": False,
            "process_status": "completed",
            "failure_reason": None,
        }
        updated = _update_dispatch(dispatch_id, patch)

        if disp.get("run_id") and _finish_run_fn:
            _finish_run_fn(disp["run_id"], {"status": "succeeded", "output": patch["output"]})

        _sync_step_from_dispatch(dispatch_id, event_type="dispatch_completed")
        _auto_complete_subtask(updated)
        _dispatch_telegram(updated, "completed")
        _emit_wf_event(updated.get("workflow_id", ""), dispatch_id, updated.get("subtask_id", ""),
                       updated.get("profile", "?"), "dispatch_completed", "completed",
                       f"Dispatch completed: {session_id}")
        _check_wf_deps(updated)

    elif status == "failed":
        reason = _normalize_failure_reason(failure_reason or _classify_failure("failed", exit_code=disp.get("exit_code"), stdout_tail=disp.get("stdout_tail"), stderr_tail=disp.get("stderr_tail"), error_message=str(output_or_error)))
        error = {"message": sanitize_output(str(output_or_error), 500), "failure_reason": reason}
        patch = {
            "status": "failed",
            "error": error,
            "output": {"response": sanitize_output(str(output_or_error), 4000)} if output_or_error else {},
            "finished_at": now_iso(),
            "is_live": False,
            "process_status": "failed",
            "failure_reason": reason,
        }
        updated = _update_dispatch(dispatch_id, patch)
        _sync_step_from_dispatch(dispatch_id, {"failure_reason": reason}, event_type="dispatch_failed")

        if disp.get("run_id") and _finish_run_fn:
            _finish_run_fn(disp["run_id"], {"status": "failed", "error": error})

        retry_ok, retry_note = _should_retry(updated, reason)
        if retry_ok:
            _schedule_retry(updated, reason, error["message"])
        else:
            if int(updated.get("retry_count") or 0) >= int(updated.get("max_retries") or 0) and int(updated.get("max_retries") or 0) > 0:
                updated = _update_dispatch(dispatch_id, {"status": "retry_exhausted", "process_status": "failed", "failure_reason": reason, "retry_stop_reason": retry_note})
                _dispatch_telegram(updated, "retry_exhausted")
            else:
                _update_dispatch(dispatch_id, {"retry_stop_reason": retry_note})
                _dispatch_telegram(updated, "failed")
            _auto_fail_subtask(dict(updated, error=error, failure_reason=reason))
            _emit_wf_event(updated.get("workflow_id", ""), dispatch_id, updated.get("subtask_id", ""),
                           updated.get("profile", "?"), "dispatch_failed", "failed",
                           f"Dispatch failed ({reason}): {error['message'][:100]}")
            _check_wf_deps(updated)


def _schedule_retry(disp: dict, failure_reason: str, error_message: str):
    dispatch_id = disp.get("dispatch_id")
    retry_count = int(disp.get("retry_count") or 0)
    max_retries = int(disp.get("max_retries") or 0)
    delay = int(disp.get("retry_delay_seconds") or RETRY_DELAY)
    retry_history = list(disp.get("retry_history") or [])
    retry_history.append({
        "attempt": retry_count + 1,
        "failed_at": now_iso(),
        "failure_reason": failure_reason,
        "error": sanitize_output(error_message, 300),
        "dispatch_id": dispatch_id,
    })
    retry_patch = {
        "status": "retrying",
        "process_status": "retrying",
        "retry_count": retry_count + 1,
        "retry_history": retry_history,
        "failure_reason": failure_reason,
        "retry_scheduled_at": now_iso(),
        "retry_next_at": now_iso(),
    }
    updated = _update_dispatch(dispatch_id, retry_patch)
    _sync_step_from_dispatch(dispatch_id, {"failure_reason": failure_reason}, event_type="dispatch_retrying")
    _dispatch_telegram(updated, "retrying")
    _emit_wf_event(disp.get("workflow_id", ""), dispatch_id, disp.get("subtask_id", ""),
                   disp.get("profile", "?"), "dispatch_retrying", "retrying",
                   f"Retry {retry_count + 1}/{max_retries} after {failure_reason}")
    threading.Timer(delay, _execute_retry, args=[dispatch_id]).start()


def _execute_retry(dispatch_id: str):
    """Execute retry by resetting to running and starting CLI again."""
    disp = _find_dispatch(dispatch_id)
    if not disp:
        return

    limit = _limit_check("start", disp.get("workflow_id", ""))
    if not limit.get("ok"):
        _update_dispatch(dispatch_id, {"status": "queued", "process_status": "queued", "blocked_by": limit.get("reason"), "blocked_reason": limit.get("message")})
        return
    patch = {"status": "running", "process_status": "starting", "started_at": now_iso(), "finished_at": None, "is_live": True, "error": {}, "stdout_tail": [], "stderr_tail": [], "last_output_chunk": "", "last_error_chunk": "", "exit_code": None}
    _update_dispatch(dispatch_id, patch)
    _sync_step_from_dispatch(dispatch_id, event_type="dispatch_retry_executing")

    profile = disp.get("profile", "Default")
    prompt = disp.get("prompt", "")

    if _start_run_fn:
        run = _start_run_fn({
            "title": f"[Retry {disp.get('retry_count', 0)}] {disp.get('title', 'Dispatch')}",
            "trigger_source": "dispatch_retry",
            "service": "mission-control",
            "profile": profile,
            "current_step": "executing",
            "input": {"dispatch_id": dispatch_id},
        })
        _update_dispatch(dispatch_id, {"run_id": run.get("run_id")})

    _emit_wf_event(disp.get("workflow_id", ""), dispatch_id, disp.get("subtask_id", ""),
                   profile, "dispatch_retry_executing", "running",
                   f"Retry executing: attempt {disp.get('retry_count', 0)}")
    _start_hermes_dispatch(dispatch_id, profile, prompt, disp)


# ── subtask auto-complete / auto-fail ─────────────────────────────

def _auto_complete_subtask(disp: dict):
    wf_id = disp.get("workflow_id", "")
    st_id = disp.get("subtask_id", "")
    if wf_id and st_id and _complete_subtask_fn:
        try:
            _complete_subtask_fn(wf_id, st_id, {"output": disp.get("output", {})})
        except Exception:
            pass


def _auto_fail_subtask(disp: dict):
    wf_id = disp.get("workflow_id", "")
    st_id = disp.get("subtask_id", "")
    if wf_id and st_id and _fail_subtask_fn:
        try:
            _fail_subtask_fn(wf_id, st_id, {"error": disp.get("error", {}), "failure_reason": disp.get("failure_reason")})
        except Exception:
            pass


# ── manual dispatch operations ────────────────────────────────────

def dispatch_complete(dispatch_id: str, payload: dict = None) -> dict:
    payload = payload or {}
    disp = _find_dispatch(dispatch_id)
    if not disp:
        return {"ok": False, "error": "Dispatch not found"}
    output = payload.get("output") or disp.get("output") or {}
    patch = {"status": "completed", "process_status": "completed", "finished_at": now_iso(), "output": output, "error": {}, "is_live": False, "failure_reason": None}
    if disp.get("run_id") and _finish_run_fn:
        _finish_run_fn(disp["run_id"], {"status": "succeeded", "output": output})
    updated = _update_dispatch(dispatch_id, patch)
    _dispatch_telegram(updated, "completed")
    _sync_step_from_dispatch(dispatch_id, event_type="dispatch_completed")
    _auto_complete_subtask(updated)
    _check_wf_deps(updated)
    return {"ok": True, "dispatch": updated}


def dispatch_fail(dispatch_id: str, payload: dict = None) -> dict:
    payload = payload or {}
    disp = _find_dispatch(dispatch_id)
    if not disp:
        return {"ok": False, "error": "Dispatch not found"}
    error = payload.get("error") or {"message": "Dispatch failed"}
    reason = _normalize_failure_reason(payload.get("failure_reason") or error.get("failure_reason") or _classify_failure("failed", error_message=error.get("message", "")))
    error["failure_reason"] = reason
    patch = {"status": "failed", "process_status": "failed", "finished_at": now_iso(), "error": error, "is_live": False, "failure_reason": reason}
    if disp.get("run_id") and _finish_run_fn:
        _finish_run_fn(disp["run_id"], {"status": "failed", "error": error})
    updated = _update_dispatch(dispatch_id, patch)
    _dispatch_telegram(updated, "failed")
    _sync_step_from_dispatch(dispatch_id, {"failure_reason": reason}, event_type="dispatch_failed")
    _auto_fail_subtask(dict(disp, error=error, failure_reason=reason))
    return {"ok": True, "dispatch": updated}


def dispatch_retry(dispatch_id: str) -> dict:
    disp = _find_dispatch(dispatch_id)
    if not disp:
        return {"ok": False, "error": "Dispatch not found"}
    if disp.get("status") not in ("failed", "retry_exhausted"):
        return {"ok": False, "error": f"Dispatch is {disp.get('status')}, not failed"}
    patch = {"status": "queued", "error": {}, "started_at": None, "finished_at": None, "is_live": False}
    updated = _update_dispatch(dispatch_id, patch)
    return {"ok": True, "dispatch": updated}


def dispatch_cancel(dispatch_id: str) -> dict:
    disp = _find_dispatch(dispatch_id)
    if not disp:
        return {"ok": False, "error": "Dispatch not found"}
    if disp.get("status") not in {"queued", "running", "retrying", "cancelling"}:
        return {"ok": False, "error": f"Dispatch is {disp.get('status')}, cannot cancel"}
    with _monitor_lock:
        state = _dispatch_monitors.get(dispatch_id)
        if state and state.get("cancel_requested"):
            state["cancel_requested"].set()
    if disp.get("status") == "queued" or not state:
        patch = {"status": "cancelled", "process_status": "cancelled", "finished_at": now_iso(), "is_live": False}
    else:
        patch = {"status": "cancelling", "process_status": "cancelling", "is_live": True, "updated_at": now_iso()}
    updated = _update_dispatch(dispatch_id, patch)
    return {"ok": True, "dispatch": updated, "message": "Cancellation requested"}


def dispatch_manual_output(dispatch_id: str, payload: dict = None) -> dict:
    payload = payload or {}
    disp = _find_dispatch(dispatch_id)
    if not disp:
        return {"ok": False, "error": "Dispatch not found"}
    if disp.get("status") not in {"queued", "running", "failed", "retrying", "retry_exhausted"}:
        return {"ok": False, "error": f"Dispatch is {disp.get('status')}"}
    output = payload.get("output") or {"manual": True, "result": "Manually completed"}
    patch = {"status": "completed", "process_status": "completed", "finished_at": now_iso(), "dispatch_method": "manual",
             "output": output, "error": {}, "is_live": False, "failure_reason": None}
    if disp.get("run_id") and _finish_run_fn:
        _finish_run_fn(disp["run_id"], {"status": "succeeded", "output": output})
    updated = _update_dispatch(dispatch_id, patch)
    _dispatch_telegram(updated, "completed")
    _sync_step_from_dispatch(dispatch_id, event_type="dispatch_completed")
    _auto_complete_subtask(updated)
    _check_wf_deps(updated)
    return {"ok": True, "dispatch": updated}


# ═══════════════════════════════════════════════════════════════════
# DEPENDENCY UNBLOCKING
# ═══════════════════════════════════════════════════════════════════

def _check_wf_deps(disp: dict):
    """After a dispatch completes/fails, check if dependent subtasks can now start.
    If all subtasks done, trigger synthesis."""
    wf_id = disp.get("workflow_id", "")
    if not wf_id or not _get_workflow_fn:
        return

    wf = _get_workflow_fn(wf_id)
    if not wf:
        return

    # Mark any subtasks whose deps are now met as unblocked
    for st in wf.get("subtasks", []):
        if st.get("status") != "waiting":
            continue
        deps_met = True
        for dep in st.get("depends_on", []):
            dep_st = next((s for s in wf.get("subtasks", [])
                          if s.get("profile") == dep or s.get("id") == dep), None)
            if dep_st and dep_st.get("status") not in ("completed",):
                deps_met = False
                break
        if deps_met:
            st["status"] = "queued"
            st["unblocked_at"] = now_iso()
            _save_workflow(wf)
            _emit_wf_event(wf_id, "", st.get("id", ""), st.get("profile", "?"),
                           "dependency_unblocked", "queued",
                           f"Dependencies met for: {st.get('title', '?')}")
            # Auto-enqueue dispatch for unblocked subtask
            policy = _step_retry_policy(st)
            enq = enqueue_dispatch({
                "workflow_id": wf_id,
                "subtask_id": st["id"],
                "profile": st["profile"],
                "title": st["title"],
                "type": "subtask",
                "timeout_seconds": st.get("timeout_seconds"),
                "retry_policy": policy,
                "test_mode": st.get("test_mode", ""),
                "prompt": st.get("prompt", ""),
            })
            if enq.get("ok"):
                st["dispatch_id"] = enq["dispatch"]["dispatch_id"]
                _save_workflow(wf)
                dispatch_start(st["dispatch_id"])

    # Check if all subtasks are done
    all_done = all(s.get("status") in ("completed", "failed", "timed_out", "retry_exhausted", "cancelled", "skipped")
                   for s in wf.get("subtasks", []))
    if all_done and _synthesize_workflow_fn:
        _synthesize_workflow_fn(wf_id)
        _emit_wf_event(wf_id, "", "", "?", "synthesis_complete",
                       "completed", "All subtasks done, synthesis complete")


# ═══════════════════════════════════════════════════════════════════
# TELEGRAM NOTIFICATIONS
# ═══════════════════════════════════════════════════════════════════

def _dispatch_telegram(dispatch: dict, event: str) -> None:
    if not _send_telegram_fn:
        return
    wf_id = dispatch.get("workflow_id", "")
    title = dispatch.get("workflow_title", dispatch.get("title", "?"))
    profile = dispatch.get("profile", "Default")
    d_id = dispatch.get("dispatch_id", "?")

    if event == "dispatched":
        msg = f"""🚀 *Dispatch Started*\nWorkflow: *{title}*\nProfile: {profile}\nDispatch ID: `{d_id}`\n\n[Dashboard →]({DASHBOARD_URL})"""
    elif event == "completed":
        msg = f"""✅ *Dispatch Completed*\nWorkflow: *{title}*\nProfile: {profile}\nStatus: completed\n\n[Dashboard →]({DASHBOARD_URL})"""
    elif event == "failed":
        err = dispatch.get("error", {})
        msg = f"""❌ *Dispatch Failed*\nWorkflow: *{title}*\nProfile: {profile}\nError: {safe_text(err.get('message', str(err)[:200]), 200)}\n\n[Dashboard →]({DASHBOARD_URL})"""
    elif event == "cancelled":
        msg = f"""🚫 *Dispatch Cancelled*\nWorkflow: *{title}*\nProfile: {profile}\n\n[Dashboard →]({DASHBOARD_URL})"""
    elif event == "retrying":
        rc = dispatch.get("retry_count", 0)
        mr = dispatch.get("max_retries", 1)
        msg = f"""🔄 *Dispatch Retrying*\nWorkflow: *{title}*\nProfile: {profile}\nAttempt: {rc}/{mr}\n\n[Dashboard →]({DASHBOARD_URL})"""
    elif event == "retry_exhausted":
        rc = dispatch.get("retry_count", 0)
        err = dispatch.get("error", {})
        msg = f"""💀 *Retries Exhausted*\nWorkflow: *{title}*\nProfile: {profile}\nAfter {rc} retries\nError: {safe_text(err.get('message', str(err)[:200]), 200)}\n\n[Dashboard →]({DASHBOARD_URL})"""
    else:
        return

    # Fire-and-forget to avoid blocking callers
    threading.Thread(target=lambda: _send_telegram_fn(msg), daemon=True).start()


def _send_parallel_start_telegram(wf: dict):
    if not _send_telegram_fn:
        return
    profiles = [s["profile"] for s in wf.get("subtasks", [])]
    msg = f"""⚡ *Parallel Workflow Started*\nWorkflow: *{wf.get('title', '?')}*\nProfiles: {', '.join(profiles)}\nSubtasks: {len(wf.get('subtasks', []))}\nMax parallel: {MAX_PARALLEL}\n\n[Dashboard →]({DASHBOARD_URL})"""
    threading.Thread(target=lambda: _send_telegram_fn(msg), daemon=True).start()


# ═══════════════════════════════════════════════════════════════════
# WORKFLOW TIMELINE (Phase 4)
# ═══════════════════════════════════════════════════════════════════

def _emit_wf_event(wf_id: str, dispatch_id: str, subtask_id: str,
                   profile: str, event_type: str, status: str, message: str):
    """Emit a workflow lifecycle event to the timeline."""
    if not wf_id:
        return
    snap = _event_snapshot(dispatch_id) if dispatch_id else {}
    step_name = ""
    if wf_id and subtask_id and _get_workflow_fn:
        wf = _get_workflow_fn(wf_id)
        st = _find_subtask(wf, subtask_id) if wf else None
        step_name = st.get("title", "") if st else ""
    event = {
        "event_id": uuid.uuid4().hex[:12],
        "workflow_id": wf_id,
        "step_id": subtask_id,
        "subtask_id": subtask_id,
        "step_name": step_name,
        "dispatch_id": dispatch_id,
        "profile": profile,
        "event_type": event_type,
        "status": status,
        "message": sanitize_output(message, 300),
        "created_at": now_iso(),
        **snap,
    }
    _append_jsonl(WF_EVENTS_DATA, event)


def get_workflow_timeline(wf_id: str) -> dict:
    """Get workflow timeline with step snapshots and events."""
    events = [e for e in _load_jsonl(WF_EVENTS_DATA) if e.get("workflow_id") == wf_id]
    events.sort(key=lambda e: e.get("created_at", ""))
    wf = _get_workflow_fn(wf_id) if _get_workflow_fn else None
    steps = []
    if wf:
        for st in wf.get("subtasks", []):
            steps.append({
                "step_id": st.get("id"),
                "step_name": st.get("title"),
                "status": st.get("status"),
                "process_status": st.get("process_status"),
                "dispatch_id": st.get("dispatch_id"),
                "pid": st.get("pid"),
                "start_time": st.get("start_time") or st.get("started_at"),
                "end_time": st.get("end_time") or st.get("completed_at"),
                "duration_seconds": st.get("duration_seconds"),
                "timeout_seconds": st.get("timeout_seconds"),
                "exit_code": st.get("exit_code"),
                "retry_attempt": st.get("retry_attempt", st.get("retries", 0)),
                "max_retries": st.get("max_retries", 0),
                "failure_reason": st.get("failure_reason"),
                "last_output_chunk": st.get("last_output_chunk", ""),
                "last_error_chunk": st.get("last_error_chunk", ""),
                "stdout_tail": st.get("stdout_tail", []),
                "stderr_tail": st.get("stderr_tail", []),
                "attempt_history": st.get("attempt_history", []),
            })
    return {"ok": True, "workflow_id": wf_id, "workflow_status": (wf or {}).get("status"), "current_step": next((s for s in steps if s.get("status") in {"running", "retrying", "cancelling"}), None), "steps": steps, "events": events, "limits": get_reliability_limits()}


def get_reliability_limits() -> dict:
    return {
        "max_concurrent_dispatches": MAX_CONCURRENT_DISPATCHES,
        "max_queued_dispatches": MAX_QUEUED_DISPATCHES,
        "max_concurrent_workflows": MAX_CONCURRENT_WORKFLOWS,
        "max_workflow_runtime_seconds": MAX_WORKFLOW_RUNTIME_SECONDS,
        "max_retries_per_workflow": MAX_RETRIES_PER_WORKFLOW,
        "active_dispatches": _active_dispatch_count(),
        "queued_dispatches": _queued_dispatch_count(),
        "active_workflows": _active_workflow_count(),
    }




def cancel_workflow(wf_id: str, payload: dict = None) -> dict:
    """Cancel a workflow and any live step dispatches."""
    wf = _get_workflow_fn(wf_id) if _get_workflow_fn else None
    if not wf:
        return {"ok": False, "error": "Workflow not found"}
    cancelled_dispatches = []
    for st in wf.get("subtasks", []):
        if st.get("status") in {"running", "retrying", "queued", "waiting", "blocked"}:
            did = st.get("dispatch_id")
            if did:
                res = dispatch_cancel(did)
                cancelled_dispatches.append({"step_id": st.get("id"), "dispatch_id": did, "result": res})
            st["status"] = "cancelled"
            st["process_status"] = "cancelled"
            st["failure_reason"] = "cancelled"
            st["completed_at"] = now_iso()
    wf["status"] = "cancelled"
    wf["failure_reason"] = "cancelled"
    wf["completed_at"] = now_iso()
    _save_workflow(wf)
    _emit_wf_event(wf_id, "", "", "coordinator", "workflow_cancelled", "cancelled", "Workflow cancelled")
    return {"ok": True, "workflow": wf, "cancelled_dispatches": cancelled_dispatches}

# ═══════════════════════════════════════════════════════════════════
# WORKFLOW RESUME
# ═══════════════════════════════════════════════════════════════════

def _enqueue_step_for_resume(wf: dict, st: dict, mode: str) -> dict:
    previous = st.get("dispatch_id")
    st.setdefault("resume_history", []).append({"mode": mode, "previous_dispatch_id": previous, "resumed_at": now_iso(), "status_before": st.get("status")})
    st["status"] = "queued"
    st["process_status"] = "queued"
    st["started_at"] = None
    st["completed_at"] = None
    st["end_time"] = None
    st["error"] = None
    st["failure_reason"] = None
    st["dispatch_id"] = None
    _save_workflow(wf)
    policy = _step_retry_policy(st)
    enq = enqueue_dispatch({
        "workflow_id": wf["workflow_id"],
        "subtask_id": st["id"],
        "profile": st["profile"],
        "title": st["title"],
        "type": "subtask",
        "timeout_seconds": st.get("timeout_seconds"),
        "retry_policy": policy,
        "test_mode": st.get("test_mode", ""),
        "prompt": st.get("prompt", ""),
    })
    if enq.get("ok"):
        st["dispatch_id"] = enq["dispatch"]["dispatch_id"]
        wf["status"] = "running"
        _save_workflow(wf)
        _emit_wf_event(wf["workflow_id"], st["dispatch_id"], st["id"], st.get("profile", "?"), "workflow_resumed", "queued", f"{mode}: {st.get('title')}")
    return enq


def resume_workflow(wf_id: str, payload: dict = None) -> dict:
    payload = payload or {}
    mode = str(payload.get("mode") or "resume_from_failed_step")
    selected = str(payload.get("step_id") or payload.get("subtask_id") or "")
    wf = _get_workflow_fn(wf_id) if _get_workflow_fn else None
    if not wf:
        return {"ok": False, "error": "Workflow not found"}
    subtasks = wf.get("subtasks", [])
    target = None
    if mode == "rerun_selected_step":
        target = _find_subtask(wf, selected)
        if not target:
            return {"ok": False, "error": "Selected step not found"}
    elif mode == "resume_from_next_step":
        failed = next((s for s in subtasks if s.get("status") in {"failed", "timed_out", "retry_exhausted", "cancelled"}), None)
        if not failed:
            return {"ok": False, "error": "No failed step found"}
        failed["status"] = "skipped"
        failed["process_status"] = "skipped"
        failed["skipped_at"] = now_iso()
        failed["failure_reason"] = failed.get("failure_reason") or "validation_error"
        _emit_wf_event(wf_id, failed.get("dispatch_id", ""), failed.get("id", ""), failed.get("profile", "?"), "step_skipped", "skipped", "Resume from next step skipped failed step")
        target = next((s for s in subtasks if int(s.get("order", 0)) > int(failed.get("order", 0)) and s.get("status") in {"queued", "waiting", "blocked"}), None)
        if not target:
            wf["status"] = "completed"
            _save_workflow(wf)
            return {"ok": True, "workflow": wf, "message": "No next step; workflow marked completed"}
    else:
        target = next((s for s in subtasks if s.get("status") in {"failed", "timed_out", "retry_exhausted", "cancelled"}), None)
        if not target:
            return {"ok": False, "error": "No failed step found"}
    result = _enqueue_step_for_resume(wf, target, mode)
    if payload.get("start", True) and result.get("ok"):
        start_result = dispatch_start(result["dispatch"]["dispatch_id"])
        result["start_result"] = start_result
    return {"ok": result.get("ok", False), "mode": mode, "workflow": _get_workflow_fn(wf_id), "step": target, "dispatch": result.get("dispatch"), "result": result}

# ═══════════════════════════════════════════════════════════════════
# PROFILE GATEWAY CONTROLS (Phase 5)
# ═══════════════════════════════════════════════════════════════════

def get_profile_gateways() -> list[dict]:
    """Get profile gateway status for all profiles."""
    profiles = []
    profile_info = [
        ("Default", "default", "running", True),
        ("Coder", "coder", None, False),
        ("ContentCreator", "contentcreator", None, False),
        ("DeepResearch", "deepresearch", None, False),
        ("MarketAnalyst", "marketanalyst", None, False),
        ("Tutor", "default", "running", True),
    ]
    for display_name, cli_alias, svc_status, is_default in profile_info:
        pdir = PROFILES_DIR / cli_alias if cli_alias != "default" else None
        has_profile_dir = pdir.exists() if pdir else True

        skills_count = 0
        if has_profile_dir and pdir:
            skills_dir = pdir / "skills"
            if skills_dir.exists():
                skills_count = len(list(skills_dir.glob("**/SKILL.md")))

        dispatches = _load_dispatch_queue()
        profile_dispatches = [d for d in dispatches
                             if _normalize_cli_profile(d.get("profile", "")) == cli_alias]
        last_dispatch = profile_dispatches[0] if profile_dispatches else None
        last_success = next((d for d in profile_dispatches
                            if d.get("status") == "completed"), None)

        profiles.append({
            "name": display_name,
            "cli_alias": cli_alias,
            "gateway_status": svc_status or "stopped",
            "is_default": is_default,
            "has_profile_dir": has_profile_dir,
            "skills_count": skills_count,
            "last_dispatch_at": last_dispatch.get("created_at") if last_dispatch else None,
            "last_dispatch_status": last_dispatch.get("status") if last_dispatch else "never",
            "last_success_at": last_success.get("finished_at") if last_success else None,
            "cold_start_warning": bool(svc_status != "running" and cli_alias != "default"),
            "can_control_gateway": bool(svc_status is not None and not is_default),
            "gateway_control_note": "Built-in (no separate gateway)" if is_default else (
                "Gateway can be started/stopped" if svc_status is not None
                else "No dedicated gateway service"
            ),
        })
    return profiles


def profile_gateway_test(profile_name: str) -> dict:
    """Test dispatch for a profile."""
    enq = enqueue_dispatch({
        "profile": profile_name,
        "title": f"Gateway test: {profile_name}",
        "type": "standalone",
        "prompt": "Respond with: ready",
    })
    did = enq["dispatch"]["dispatch_id"]
    result = dispatch_start(did)
    return {"ok": True, "profile": profile_name, "dispatch_id": did, "result": result}


def profile_gateway_start(profile_name: str) -> dict:
    """Start a profile gateway if applicable."""
    cli_alias = _normalize_cli_profile(profile_name)
    if cli_alias == "default":
        return {"ok": False, "error": "Cannot start default profile gateway — it handles main operations"}
    svc_name = f"hermes-gateway-{cli_alias}"
    code, out = _run(["systemctl", "is-active", svc_name], timeout=5)
    if code == 0:
        return {"ok": True, "profile": profile_name, "message": "Gateway already running"}
    code, out = _run(["systemctl", "start", svc_name], timeout=15)
    if code == 0:
        return {"ok": True, "profile": profile_name, "message": f"Gateway {svc_name} started"}
    return {"ok": False, "error": f"Could not start gateway: {out[:200]}"}


def profile_gateway_stop(profile_name: str) -> dict:
    """Stop a profile gateway if applicable."""
    cli_alias = _normalize_cli_profile(profile_name)
    if cli_alias == "default":
        return {"ok": False, "error": "Cannot stop default profile gateway — it handles main operations"}
    svc_name = f"hermes-gateway-{cli_alias}"
    code, out = _run(["systemctl", "stop", svc_name], timeout=15)
    if code == 0:
        return {"ok": True, "profile": profile_name, "message": f"Gateway {svc_name} stopped"}
    return {"ok": False, "error": f"Could not stop gateway: {out[:200]}"}


def profile_gateway_restart(profile_name: str) -> dict:
    """Restart a profile gateway if applicable."""
    cli_alias = _normalize_cli_profile(profile_name)
    if cli_alias == "default":
        return {"ok": False, "error": "Cannot restart default profile gateway — it handles main operations"}
    svc_name = f"hermes-gateway-{cli_alias}"
    code, out = _run(["systemctl", "restart", svc_name], timeout=15)
    if code == 0:
        return {"ok": True, "profile": profile_name, "message": f"Gateway {svc_name} restarted"}
    return {"ok": False, "error": f"Could not restart gateway: {out[:200]}"}
