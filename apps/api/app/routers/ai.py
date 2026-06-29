"""AI service — ask, search, RCA, recommendations."""

from app.services import today_service
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/ai", tags=["ai"])


class AskRequest(BaseModel):
    message: str
    conversation_id: str | None = None


class SearchRequest(BaseModel):
    query: str
    limit: int = 10


class RCARequest(BaseModel):
    source_type: str
    source_id: str


@router.post("/ask")
def ask(req: AskRequest):
    today = today_service.build_today()
    return {
        "answer": (
            f"Based on current dashboard state: {today['attention_count']} items need attention. "
            f"Active agents: {today['metrics']['agents_active']}. "
            f"(Full LLM integration connects via Hermes CLI in Phase 4.)"
        ),
        "citations": [{"type": "today", "id": "briefing"}],
        "conversation_id": req.conversation_id,
    }


@router.post("/search")
def search(req: SearchRequest):
    return {
        "query": req.query,
        "results": [],
        "note": "pgvector semantic search enabled after embedding pipeline runs",
    }


@router.post("/rca")
def rca(req: RCARequest):
    return {
        "summary": "Automated root cause analysis pending LLM integration",
        "source_type": req.source_type,
        "source_id": req.source_id,
        "recommendation": "Check stderr tail and retry with backoff",
        "confidence": 0.5,
    }


@router.get("/recommendations")
def recommendations():
    today = today_service.build_today()
    return {"items": today.get("recommendations", [])}
