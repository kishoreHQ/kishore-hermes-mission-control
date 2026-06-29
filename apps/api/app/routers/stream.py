"""SSE event stream with JSONL file watcher."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from app.config import settings
from app.services import event_bus, legacy_adapter
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

router = APIRouter(prefix="/stream", tags=["stream"])


async def _file_watcher():
    path = legacy_adapter.dispatch_file_path()
    last_size = path.stat().st_size if path.exists() else 0
    while True:
        await asyncio.sleep(2)
        if not path.exists():
            continue
        size = path.stat().st_size
        if size != last_size:
            last_size = size
            event_bus.publish("dispatch.updated", {})


async def event_generator():
    q = event_bus.subscribe()
    watcher = asyncio.create_task(_file_watcher())
    try:
        while True:
            try:
                data = await asyncio.wait_for(q.get(), timeout=30.0)
                yield f"event: {data['type']}\ndata: {json.dumps(data['payload'])}\n\n"
            except asyncio.TimeoutError:
                yield "event: heartbeat\ndata: {}\n\n"
    finally:
        event_bus.unsubscribe(q)
        watcher.cancel()


@router.get("/events")
async def stream_events():
    return StreamingResponse(event_generator(), media_type="text/event-stream")
