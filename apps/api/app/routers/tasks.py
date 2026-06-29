from app.services import legacy_adapter
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/tasks", tags=["tasks"])


class MoveBody(BaseModel):
    id: str
    lane: str


class ArchiveBody(BaseModel):
    id: str


@router.get("")
def list_tasks():
    return {"items": legacy_adapter.list_tasks()}


@router.post("/move")
def move_task(body: MoveBody):
    tasks = legacy_adapter.list_tasks()
    updated = None
    for t in tasks:
        if str(t.get("id")) == body.id:
            t["lane"] = body.lane
            updated = t
            break
    if not updated:
        raise HTTPException(status_code=404, detail="Task not found")
    legacy_adapter.write_json("tasks.json", tasks)
    return {"ok": True, "task": updated}


@router.post("/archive")
def archive_task(body: ArchiveBody):
    return move_task(MoveBody(id=body.id, lane="archived"))
