from app.services import today_service
from fastapi import APIRouter

router = APIRouter(prefix="/today", tags=["today"])


@router.get("")
def get_today():
    return today_service.build_today()


@router.get("/attention")
def get_attention():
    data = today_service.build_today()
    return {"items": data["attention"], "count": data["attention_count"]}
