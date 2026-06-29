"""SSE event stream for realtime updates."""

import asyncio
import json
from datetime import datetime, timezone

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

router = APIRouter(prefix="/stream", tags=["stream"])


async def event_generator():
    while True:
        payload = {"ts": datetime.now(timezone.utc).isoformat()}
        yield f"event: heartbeat\ndata: {json.dumps(payload)}\n\n"
        await asyncio.sleep(30)


@router.get("/events")
async def stream_events():
    return StreamingResponse(event_generator(), media_type="text/event-stream")
