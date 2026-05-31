#!/usr/bin/env bash
set -euo pipefail

ROOT="/root/mission-control"
HERMES_HOME="${HERMES_HOME:-/root/.hermes}"

echo "== User crontab =="
crontab -l || true

echo "== Root crontab =="
sudo -n crontab -l || true

echo "== /etc cron directories =="
ls -la /etc/cron.d /etc/cron.hourly /etc/cron.daily /etc/cron.weekly /etc/cron.monthly || true

echo "== Systemd timers =="
systemctl list-timers --all --no-pager || true

echo "== Failed units =="
systemctl --failed --no-pager || true

echo "== Mission Control health =="
curl -fsS http://127.0.0.1:8090/healthz >/dev/null
curl -fsS http://127.0.0.1:8090/api/status >/dev/null
curl -fsS http://127.0.0.1:8090/api/services/health >/dev/null

echo "== Mission Control scheduled/runtime data =="
cd "$ROOT"
find data -maxdepth 2 -type f | sort || true

echo "== Hermes cron jobs =="
python3 - <<'PY'
import json
from pathlib import Path
p = Path('/root/.hermes/cron/jobs.json')
if not p.exists():
    print('No Hermes cron jobs file found')
    raise SystemExit(0)
data = json.loads(p.read_text())
jobs = data.get('jobs', []) if isinstance(data, dict) else data
if isinstance(jobs, dict):
    jobs = list(jobs.values())
for j in jobs:
    print(f"{j.get('id') or j.get('job_id')} | {j.get('name')} | state={j.get('state')} | last={j.get('last_status')} | next={j.get('next_run_at')} | script={j.get('script') or '-'} | no_agent={j.get('no_agent')}")
PY

echo "== Recent cron service log tail =="
journalctl -u cron -n 80 --no-pager || true

echo "SCHEDULED_JOBS_AUDIT_OK"
