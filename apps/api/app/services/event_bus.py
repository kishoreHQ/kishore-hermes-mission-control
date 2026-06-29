"""In-memory event bus for SSE."""

from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Any

_subscribers: list[asyncio.Queue] = []


def subscribe() -> asyncio.Queue:
    q: asyncio.Queue = asyncio.Queue(maxsize=100)
    _subscribers.append(q)
    return q


def unsubscribe(q: asyncio.Queue) -> None:
    if q in _subscribers:
        _subscribers.remove(q)


def publish(event_type: str, payload: dict[str, Any] | None = None) -> None:
    data = {"type": event_type, "payload": payload or {}}
    dead: list[asyncio.Queue] = []
    for q in _subscribers:
        try:
            q.put_nowait(data)
        except asyncio.QueueFull:
            dead.append(q)
    for q in dead:
        unsubscribe(q)
