from app.services import status_service
from fastapi import APIRouter

router = APIRouter(tags=["status"])


@router.get("/status")
def get_status(heavy: bool = True):
    return status_service.build_status(include_heavy=heavy)
