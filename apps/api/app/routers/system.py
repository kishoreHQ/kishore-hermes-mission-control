import subprocess

from app.services import hermes_adapter, legacy_adapter, probes
from fastapi import APIRouter

router = APIRouter(tags=["system"])


@router.get("/system")
def system_overview():
    metrics_store_record = {}
    try:
        from app.services import metrics_store

        metrics_store.record_system_metrics()
        metrics_store_record = metrics_store.cost_summary(1)
    except Exception:
        pass
    load = subprocess.run(["bash", "-lc", "cat /proc/loadavg"], capture_output=True, text=True, timeout=3)
    mem = subprocess.run(["bash", "-lc", "free -m | awk 'NR==2{print $3,$2}'"], capture_output=True, text=True, timeout=3)
    disk = subprocess.run(["bash", "-lc", "df -h / | awk 'NR==2{print $3,$2,$5}'"], capture_output=True, text=True, timeout=3)
    ts = subprocess.run(["tailscale", "status", "--json"], capture_output=True, text=True, timeout=5)
    return {
        "load": (load.stdout or "").strip(),
        "memory_mb": (mem.stdout or "").strip(),
        "disk": (disk.stdout or "").strip(),
        "tailscale": (ts.stdout or "")[:2000] if ts.returncode == 0 else None,
        "cron_count": len(hermes_adapter.load_cron_jobs()),
        "cost_today": metrics_store_record,
    }


@router.get("/search")
def search(q: str = "", limit: int = 20):
    q = q.lower().strip()
    if not q:
        return {"items": []}
    hits: list[dict] = []
    for job in hermes_adapter.list_cron_summaries():
        if q in str(job.get("name", "")).lower():
            hits.append({"source": "cron", "title": job.get("name"), "id": job.get("id")})
    for t in legacy_adapter.list_tasks():
        if q in str(t.get("title", "")).lower():
            hits.append({"source": "task", "title": t.get("title"), "id": t.get("id")})
    for svc in legacy_adapter.list_services():
        if q in str(svc.get("name", "")).lower():
            hits.append({"source": "service", "title": svc.get("name"), "id": svc.get("id")})
    return {"items": hits[:limit]}
