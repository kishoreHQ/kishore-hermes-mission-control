from app.services import dispatch_service, legacy_adapter
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/dispatch", tags=["dispatch"])


@router.get("")
def list_dispatch(limit: int = 100):
    return {"items": dispatch_service.list_all(limit)}


@router.get("/active")
def list_active():
    return {"items": dispatch_service.list_active()}


@router.get("/{dispatch_id}")
def get_dispatch(dispatch_id: str):
    item = dispatch_service.get(dispatch_id)
    if not item:
        raise HTTPException(status_code=404, detail="Dispatch not found")
    return item


@router.get("/{dispatch_id}/live")
def get_dispatch_live(dispatch_id: str):
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
