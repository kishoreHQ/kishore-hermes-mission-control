"""Dispatch — JSONL reads; mutations via dispatch_engine when available."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.services import dispatch_bridge, dispatch_service, event_bus, legacy_adapter
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/dispatch", tags=["dispatch"])


class EnqueueBody(BaseModel):
    profile: str
    prompt: str
    toolsets: str = ""
    title: str = "Dispatch task"


@router.get("")
def list_dispatch(limit: int = 100):
    return {"items": dispatch_service.list_all(limit)}


@router.get("/active")
def list_active():
    return {"items": dispatch_service.list_active()}


@router.post("/enqueue")
def enqueue_dispatch(body: EnqueueBody):
    payload = {
        "profile": body.profile,
        "prompt": body.prompt,
        "title": body.title or body.prompt[:80],
        "type": "manual",
    }
    if dispatch_bridge.available():
        result = dispatch_bridge.enqueue(payload)
        if not result.get("ok", True) and result.get("error"):
            raise HTTPException(status_code=400, detail=result.get("error"))
        dispatch = result.get("dispatch") or result
        event_bus.publish("dispatch.updated", {"dispatch_id": dispatch.get("dispatch_id")})
        return {"ok": True, "dispatch": dispatch}

    dispatch_id = uuid.uuid4().hex[:12]
    record = {
        "dispatch_id": dispatch_id,
        "profile": body.profile,
        "prompt": body.prompt,
        "toolsets": body.toolsets,
        "title": body.title,
        "status": "queued",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    legacy_adapter.append_jsonl("dispatch_queue.jsonl", record)
    event_bus.publish("dispatch.updated", {"dispatch_id": dispatch_id})
    return {"ok": True, "dispatch": record}


@router.get("/{dispatch_id}")
def get_dispatch(dispatch_id: str):
    item = dispatch_service.get(dispatch_id)
    if not item:
        raise HTTPException(status_code=404, detail="Dispatch not found")
    return item


@router.get("/{dispatch_id}/live")
def get_dispatch_live(dispatch_id: str):
    if dispatch_bridge.available():
        result = dispatch_bridge.live(dispatch_id)
        if not result.get("ok", True):
            raise HTTPException(status_code=404, detail=result.get("error", "Not found"))
        return result
    item = dispatch_service.get(dispatch_id)
    if not item:
        raise HTTPException(status_code=404, detail="Dispatch not found")
    return {
        "dispatch_id": dispatch_id,
        "status": item.get("status"),
        "stdout_tail": item.get("stdout_tail", ""),
        "stderr_tail": item.get("stderr_tail", ""),
        "process_status": item.get("process_status"),
    }


@router.post("/{dispatch_id}/start")
def start_dispatch(dispatch_id: str):
    if not dispatch_bridge.available():
        raise HTTPException(status_code=503, detail="dispatch_engine unavailable")
    result = dispatch_bridge.start(dispatch_id)
    if not result.get("ok", True):
        raise HTTPException(status_code=400, detail=result.get("error", "Start failed"))
    event_bus.publish("dispatch.updated", {"dispatch_id": dispatch_id})
    return result


@router.post("/{dispatch_id}/retry")
def retry_dispatch(dispatch_id: str):
    if not dispatch_bridge.available():
        raise HTTPException(status_code=503, detail="dispatch_engine unavailable")
    result = dispatch_bridge.retry(dispatch_id)
    if not result.get("ok", True):
        raise HTTPException(status_code=400, detail=result.get("error", "Retry failed"))
    event_bus.publish("dispatch.updated", {"dispatch_id": dispatch_id})
    return result


@router.post("/{dispatch_id}/cancel")
def cancel_dispatch(dispatch_id: str):
    if dispatch_bridge.available():
        result = dispatch_bridge.cancel(dispatch_id)
        if not result.get("ok", True):
            raise HTTPException(status_code=400, detail=result.get("error", "Cancel failed"))
        event_bus.publish("dispatch.updated", {"dispatch_id": dispatch_id})
        return result

    item = dispatch_service.get(dispatch_id)
    if not item:
        raise HTTPException(status_code=404, detail="Dispatch not found")
    item = dict(item)
    item["status"] = "cancelled"
    item["updated_at"] = datetime.now(timezone.utc).isoformat()
    legacy_adapter.append_jsonl("dispatch_queue.jsonl", item)
    event_bus.publish("dispatch.updated", {"dispatch_id": dispatch_id})
    return {"ok": True, "dispatch": item}
