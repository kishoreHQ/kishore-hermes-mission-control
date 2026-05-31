# Fresh VM Setup Guide

This guide sets up Mission Control on a new Linux VM.

## 1. Install system packages

```bash
sudo apt-get update
sudo apt-get install -y git python3 python3-venv curl nodejs npm
```

Node is only used for `node --check static/app.js`; Mission Control itself is Python stdlib.

## 2. Install Python requirements

There is no project requirements file today. The server uses Python stdlib. Hermes CLI has its own installation/setup path.

```bash
python3 --version
```

## 3. Install or verify Hermes CLI

```bash
command -v hermes
hermes --version
hermes status || true
```

Real dispatch requires Hermes profiles to be configured under `HERMES_HOME`.

## 4. Clone Mission Control

```bash
git clone <repo-url> kishore-hermes-mission-control
cd kishore-hermes-mission-control
```

## 5. Configure environment

```bash
cp .env.example .env
```

Edit `.env` if needed. Do not commit `.env`.

Supported variables:

```text
MISSION_CONTROL_HOST
MISSION_CONTROL_PORT
HERMES_HOME
MC_MAX_CONCURRENT_DISPATCHES
MC_MAX_QUEUED_DISPATCHES
MC_MAX_CONCURRENT_WORKFLOWS
MC_MAX_WORKFLOW_RUNTIME_SECONDS
MC_MAX_RETRIES_PER_WORKFLOW
```

## 6. Create data/log directories

```bash
mkdir -p data logs
: > data/action_log.jsonl
: > data/dispatch_queue.jsonl
: > data/runs.jsonl
: > data/routing_history.jsonl
: > data/workflow_events.jsonl
```

Runtime JSONL files must remain untracked.

## 7. Run syntax checks

```bash
python3 -m py_compile server.py dispatch_engine.py
node --check static/app.js
```

## 8. Start manually

```bash
set -a
[ -f .env ] && . ./.env
set +a
python3 server.py
```

Open another terminal:

```bash
curl http://127.0.0.1:8090/healthz
```

Expected: `ok`.

## 9. Install systemd service

Review `mission-control.service.example`, then install:

```bash
sudo cp mission-control.service.example /etc/systemd/system/mission-control.service
sudo systemctl daemon-reload
sudo systemctl enable mission-control.service
sudo systemctl start mission-control.service
```

## 10. Verify health

```bash
systemctl status mission-control.service
curl http://127.0.0.1:8090/healthz
curl http://127.0.0.1:8090/api/status
curl http://127.0.0.1:8090/api/reliability/limits
```

## 11. Open UI

Local: `http://127.0.0.1:8090`

Remote access should use SSH tunnel, VPN/Tailscale, or an authenticated reverse proxy.

## 12. Run test dispatch

First verify Hermes manually:

```bash
hermes -p default chat -q "Say hello in one line" --quiet --max-turns=1
```

Then use the Mission Control Dispatch UI or API.

## 13. Troubleshooting

- Service fails: `journalctl -u mission-control.service -n 100 --no-pager`
- Port conflict: `ss -ltnp | grep 8090`
- Hermes missing: `command -v hermes`
- Profile issue: `hermes profile list` or inspect `$HERMES_HOME/profiles`
- Queue blocked: `curl http://127.0.0.1:8090/api/reliability/limits`
