from app.services import contentforge_adapter
from fastapi import APIRouter

router = APIRouter(prefix="/content", tags=["content"])


@router.get("/queue")
def content_queue():
    return {"items": contentforge_adapter.queue()}


@router.get("/published")
def content_published():
    return {"items": contentforge_adapter.published()}


@router.get("/metrics")
def content_metrics():
    return contentforge_adapter.metrics()
