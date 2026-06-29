"""Action prepare/execute with safety tiers (PRD §10)."""

from __future__ import annotations

import secrets
import time
import uuid

from app.services import legacy_adapter
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/actions", tags=["actions"])

_PENDING: dict[str, dict] = {}

RISK = {
    "refresh": "safe",
    "view_logs": "safe",
    "retry_dispatch": "safe",
    "restart_service": "medium",
    "run_cron": "medium",
}


class PrepareBody(BaseModel):
    action: str
    payload: dict | None = None


class ExecuteBody(BaseModel):
    approval_id: str
    approval_code: str


@router.post("/prepare")
def prepare_action(body: PrepareBody):
    risk = RISK.get(body.action, "medium")
    approval_id = uuid.uuid4().hex[:12]
    code = f"{secrets.randbelow(900000) + 100000}"
    details = {
        "action": body.action,
        "payload": body.payload or {},
        "risk": risk,
        "expires_at": time.time() + 600,
    }
    _PENDING[approval_id] = {"code": code, "details": details}
    if risk == "safe":
        return {"ok": True, "risk": risk, "auto_execute": True, "approval_id": approval_id, "approval_code": code}
    return {
        "ok": True,
        "risk": risk,
        "approval_id": approval_id,
        "message": f"Enter code {code} to confirm {body.action}",
    }


@router.post("/execute")
def execute_action(body: ExecuteBody):
    pending = _PENDING.get(body.approval_id)
    if not pending:
        return {"ok": False, "error": "Approval not found"}
    if time.time() > pending["details"].get("expires_at", 0):
        _PENDING.pop(body.approval_id, None)
        return {"ok": False, "error": "Approval expired"}
    if body.approval_code != pending.get("code"):
        return {"ok": False, "error": "Code mismatch"}
    action = pending["details"]["action"]
    payload = pending["details"].get("payload") or {}
    _PENDING.pop(body.approval_id, None)
    legacy_adapter.append_jsonl(
        "action_log.jsonl",
        {"action": action, "payload": payload, "result": "accepted"},
    )
    return {"ok": True, "action": action, "message": f"Action {action} recorded (bridge to V1 for full execution)"}
