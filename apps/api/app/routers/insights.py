from app.services import metrics_store
from fastapi import APIRouter

router = APIRouter(prefix="/insights", tags=["insights"])


@router.get("/cost")
def cost_summary(days: int = 7):
    return metrics_store.cost_summary(days)


@router.get("/anomalies")
def anomalies(limit: int = 20):
    return {"items": metrics_store.list_anomalies(limit)}


@router.get("/repos")
def repos_summary():
    """Repository health — set GITHUB_TOKEN in .env for live GitHub API reads."""
    return {"items": metrics_store.list_repos()}
