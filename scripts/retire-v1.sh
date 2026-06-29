#!/usr/bin/env bash
# Stop and disable V1 mission-control.service (:8090). V2 must already be healthy.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "==> Checking V2 health before retiring V1..."
curl -sf http://127.0.0.1:8000/healthz >/dev/null || { echo "V2 API not healthy on :8000"; exit 1; }
curl -sf -o /dev/null http://127.0.0.1:3001/today || { echo "V2 Web not healthy on :3001"; exit 1; }
echo "V2 API + Web OK"

if systemctl is-active mission-control.service >/dev/null 2>&1; then
  echo "==> Stopping mission-control.service..."
  sudo systemctl stop mission-control.service
else
  echo "mission-control.service already stopped"
fi

if systemctl is-enabled mission-control.service >/dev/null 2>&1; then
  echo "==> Disabling mission-control.service..."
  sudo systemctl disable mission-control.service
else
  echo "mission-control.service already disabled"
fi

if command -v tailscale >/dev/null 2>&1 && tailscale serve status 2>/dev/null | grep -q ':8090'; then
  echo "==> Removing Tailscale serve on :8090..."
  tailscale serve --https=8090 off
fi

if ss -ltn 2>/dev/null | grep -qE '(:|\])8090\b'; then
  echo "WARNING: something still listening on port 8090"
  ss -ltnp | grep 8090 || true
else
  echo "Port 8090 is free"
fi

echo ""
echo "V1 retired. Production dashboard:"
echo "  https://$(tailscale status --json 2>/dev/null | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get("Self",{}).get("DNSName","").rstrip("."))' 2>/dev/null || echo '<vps-hostname>')/today"
echo "  http://127.0.0.1:3001/today"
