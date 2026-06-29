from app.services import legacy_adapter
from fastapi import APIRouter

router = APIRouter(tags=["agents"])


@router.get("/profiles")
def list_profiles():
    return {"items": legacy_adapter.list_profiles_from_workflows()}


@router.get("/workflows")
def list_workflows():
    data = legacy_adapter.list_workflows()
    if isinstance(data, dict):
        return {"items": list(data.values())}
    return {"items": data}


@router.get("/tasks")
def list_tasks():
    return {"items": legacy_adapter.list_tasks()}


@router.get("/cron")
def list_cron():
    return {
        "items": [],
        "note": "Connect HERMES_HOME cron jobs.json on VPS for live cron data",
    }
