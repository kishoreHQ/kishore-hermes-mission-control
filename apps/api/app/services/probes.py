"""Service health probes (ported from V1 server.py)."""

from __future__ import annotations

import json
import subprocess
import time
from datetime import datetime, timezone
from urllib.request import Request, urlopen

SERVICE_ALLOWLIST = {
    "mission-control.service",
    "hermes-os-api.service",
    "hermes-os-web.service",
    "hermes-dashboard.service",
    "hermes-gateway.service",
    "hermes-webui.service",
    "claw3d-studio.service",
    "claw3d-adapter.service",
    "tailscaled.service",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _run(cmd: list[str], timeout: int = 5) -> tuple[int, str]:
    try:
        p = subprocess.run(cmd, text=True, capture_output=True, timeout=timeout)
        return p.returncode, (p.stdout + p.stderr).strip()
    except Exception as exc:
        return 1, str(exc)


def http_probe(url: str, timeout: int = 3) -> dict:
    started = time.time()
    try:
        req = Request(url, headers={"User-Agent": "HermesOS/2.0"})
        with urlopen(req, timeout=timeout) as resp:
            body = resp.read(5000).decode("utf-8", errors="replace")
            ok = 200 <= int(resp.status) < 400
            parsed = None
            try:
                parsed = json.loads(body)
            except Exception:
                pass
            return {
                "ok": ok,
                "status_code": resp.status,
                "latency_ms": int((time.time() - started) * 1000),
                "json": parsed,
            }
    except Exception as exc:
        return {
            "ok": False,
            "status_code": None,
            "latency_ms": int((time.time() - started) * 1000),
            "summary": str(exc)[:500],
            "json": None,
        }


def service_status(service: str) -> dict:
    if service not in SERVICE_ALLOWLIST:
        return {"service": service, "active": "blocked", "ok": False}
    code, active = _run(["systemctl", "is-active", service], timeout=3)
    return {
        "service": service,
        "active": active.splitlines()[0] if active else "unknown",
        "ok": code == 0 and active.startswith("active"),
    }


def port_status(port: int) -> dict:
    code, _ = _run(
        ["bash", "-lc", f"ss -ltn | awk '{{print $4}}' | grep -E '(:|\\]){int(port)}$' >/dev/null"],
        timeout=3,
    )
    return {"port": int(port), "listening": code == 0}


def probe_service(svc: dict) -> dict:
    item = dict(svc)
    systemd = str(svc.get("systemd_service") or "")
    item["systemd"] = service_status(systemd) if systemd else None
    port = int(svc.get("port") or 0)
    item["port_status"] = port_status(port) if port else None
    health_url = str(svc.get("url", "")).rstrip("/") + str(svc.get("health_endpoint") or "/")
    item["health_probe"] = http_probe(health_url)
    item["last_checked"] = now_iso()
    if item["systemd"] and item["systemd"].get("ok") and item["health_probe"].get("ok"):
        item["status"] = "online"
    elif item["systemd"] and item["systemd"].get("ok"):
        item["status"] = "degraded"
    elif item["port_status"] and item["port_status"].get("listening"):
        item["status"] = "degraded"
    else:
        item["status"] = "offline"
    return item
