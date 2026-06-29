from app.services import hermes_adapter, legacy_adapter
from fastapi import APIRouter

router = APIRouter(tags=["agents"])


@router.get("/profiles")
def list_profiles():
    profiles = hermes_adapter.list_profiles()
    if profiles:
        return {"items": profiles}
    return {"items": legacy_adapter.list_profiles_from_workflows()}


@router.get("/workflows")
def list_workflows():
    data = legacy_adapter.list_workflows()
    if isinstance(data, dict):
        return {"items": list(data.values())}
    return {"items": data}


@router.get("/workflows/{workflow_id}/timeline")
def workflow_timeline(workflow_id: str):
    events = [
        e for e in legacy_adapter.list_workflow_events(500) if str(e.get("workflow_id")) == workflow_id
    ]
    return {"items": events[-50:]}


@router.get("/cron")
def list_cron():
    return {"items": hermes_adapter.list_cron_summaries()}
