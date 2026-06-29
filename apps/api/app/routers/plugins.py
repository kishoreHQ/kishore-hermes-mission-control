from app.services import hermes_adapter
from fastapi import APIRouter

router = APIRouter(prefix="/plugins", tags=["plugins"])

_REGISTRY = [
    {"id": "today-briefing", "name": "Today Briefing", "space": "today", "enabled": True},
    {"id": "dispatch-queue", "name": "Dispatch Queue", "space": "agents", "enabled": True},
    {"id": "content-pipeline", "name": "Content Pipeline", "space": "create", "enabled": True},
    {"id": "cost-insights", "name": "Cost Insights", "space": "insights", "enabled": True},
]


@router.get("")
def list_plugins():
    dynamic = [{"id": p["name"], "name": p["name"], "space": "system", "enabled": True} for p in hermes_adapter.list_plugins()]
    return {"items": _REGISTRY + dynamic}


@router.get("/widgets/today")
def today_widgets():
    return {"items": [p for p in _REGISTRY if p.get("space") == "today" and p.get("enabled")]}
