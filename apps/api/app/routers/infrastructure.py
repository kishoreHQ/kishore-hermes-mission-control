from app.services import legacy_adapter, probes
from fastapi import APIRouter

router = APIRouter(tags=["infrastructure"])

LOG_ALLOWLIST = {
    "mission-control.service",
    "hermes-os-api.service",
    "hermes-os-web.service",
    "hermes-webui.service",
}


@router.get("/services")
def list_services():
    return {"items": legacy_adapter.list_services()}


@router.get("/services/health")
def services_health():
    services = [probes.probe_service(s) for s in legacy_adapter.list_services()]
    healthy = sum(1 for s in services if s.get("status") == "online")
    return {
        "summary": f"{healthy}/{len(services)} online",
        "items": services,
    }


@router.get("/logs")
def get_logs(service: str = "hermes-os-api.service", lines: int = 100):
    if service not in LOG_ALLOWLIST:
        return {"service": service, "content": "Service not in allowlist", "lines": 0}
    import subprocess

    p = subprocess.run(
        ["journalctl", "-u", service, "-n", str(min(lines, 500)), "--no-pager"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    return {"service": service, "lines": lines, "content": p.stdout or p.stderr or ""}
