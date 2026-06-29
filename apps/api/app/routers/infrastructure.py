from app.services import legacy_adapter
from fastapi import APIRouter

router = APIRouter(tags=["infrastructure"])


@router.get("/services")
def list_services():
    return {"items": legacy_adapter.list_services()}


@router.get("/services/health")
def services_health():
    services = legacy_adapter.list_services()
    healthy = sum(1 for s in services if s.get("health") != "degraded")
    return {
        "summary": f"{healthy}/{len(services)} healthy",
        "items": services,
    }


@router.get("/logs")
def get_logs(service: str = "mission-control", lines: int = 100):
    return {
        "service": service,
        "lines": lines,
        "content": "[Log viewer connects to journalctl on VPS deployment]",
    }
