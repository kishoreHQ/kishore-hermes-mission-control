"""Plugin and widget registry."""

from fastapi import APIRouter

router = APIRouter(prefix="/plugins", tags=["plugins"])

_REGISTRY = [
    {
        "id": "contentforge-queue",
        "space": "create",
        "module": "content-studio",
        "todayWidget": True,
        "name": "Content Queue",
        "status": "planned",
    },
    {
        "id": "stock-dashboard",
        "space": "wealth",
        "module": "stocks",
        "todayWidget": True,
        "name": "Stock Pulse",
        "status": "planned",
    },
    {
        "id": "knowledge-graph",
        "space": "knowledge",
        "module": "graph",
        "todayWidget": False,
        "name": "Knowledge Graph",
        "status": "planned",
    },
]


@router.get("")
def list_plugins():
    return {"items": _REGISTRY}


@router.get("/widgets/today")
def today_widgets():
    return {"items": [p for p in _REGISTRY if p.get("todayWidget")]}
