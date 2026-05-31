# Mission Control for Kishore-Hermes

Mission Control is a local-first operations dashboard for Kishore-Hermes. It unifies service health, run history, workflow orchestration, dispatch execution, logs, cron visibility, and safe actions behind one Python stdlib HTTP service.

## What this is

Mission Control is the control plane for Hermes automation on a VM. It is intentionally simple: `server.py` runs a `ThreadingHTTPServer`, serves the static UI from `static/`, reads/writes JSON state from `data/`, and delegates execution to `dispatch_engine.py`.

It is designed for live Hermes service status, workflow and dispatch visibility, real Hermes CLI execution through profiles, stdout/stderr tail inspection, retry/resume/timeout/cancel operations, VM-safe queue limits, and safe operational actions.

## Current stable milestones

- `18b4886 replace blocking dispatch with popen streaming runner`
- `da163fd add workflow retry resume timeout and failure classification`

These are the important local milestone commits for understanding dispatch evolution.

## Features

- Mission Control UI on port `8090`
- service registry and health cards
- workflow list and workflow detail drawer
- dispatch queue and live dispatch details
- Hermes CLI profile dispatch: `hermes -p <profile> chat -q ...`
- `subprocess.Popen`-based execution with PID tracking
- stdout/stderr streaming into dispatch records
- timeout kill and cancel support
- retry success/exhausted behavior
- resume from failed step and resume from next step
- failure classification
- VM-safe queue and concurrency limits
- safe/medium/high action model
- journalctl-backed logs viewer

## Architecture overview

Main files:

- `server.py` — HTTP server, API routes, static serving, service checks, safe actions, docs/status payloads.
- `dispatch_engine.py` — dispatch queue, Hermes CLI execution, Popen runner, workflow orchestration, retry/resume/timeout/cancel logic.
- `static/index.html` — single-page shell.
- `static/app.js` — UI rendering and API calls.
- `static/styles.css` — UI styling.
- `data/` — JSON configuration and runtime state directory.

Runtime JSONL files are intentionally ignored and must not be committed.

## Requirements

- Linux VM
- Python 3.11+
- Node.js for `node --check static/app.js`
- Git
- Hermes CLI installed and authenticated for real dispatch execution
- systemd for production service mode
- `curl` for smoke checks

No Flask/FastAPI framework is required.

## Installation

```bash
git clone <repo-url>
cd kishore-hermes-mission-control
cp .env.example .env
python3 -m py_compile server.py dispatch_engine.py
node --check static/app.js
```

Create runtime directory placeholders if missing:

```bash
mkdir -p data logs
: > data/action_log.jsonl
: > data/dispatch_queue.jsonl
: > data/runs.jsonl
: > data/routing_history.jsonl
: > data/workflow_events.jsonl
```

## Configuration

Mission Control currently reads these environment variables:

- `MISSION_CONTROL_HOST` — bind host, default `127.0.0.1`
- `MISSION_CONTROL_PORT` — bind port, default `8090`
- `HERMES_HOME` — Hermes home directory, default `/root/.hermes`
- `MC_MAX_CONCURRENT_DISPATCHES` — default `3`
- `MC_MAX_QUEUED_DISPATCHES` — default `25`
- `MC_MAX_CONCURRENT_WORKFLOWS` — default `2`
- `MC_MAX_WORKFLOW_RUNTIME_SECONDS` — default `3600`
- `MC_MAX_RETRIES_PER_WORKFLOW` — default `6`

Provider API keys and Telegram bot tokens are not read directly by Mission Control. Hermes profiles and the Hermes gateway own those credentials. Keep them out of this repo.

## Running locally

```bash
python3 server.py
```

Open `http://127.0.0.1:8090`.

## Running as a systemd service

```bash
sudo cp mission-control.service.example /etc/systemd/system/mission-control.service
sudo systemctl daemon-reload
sudo systemctl enable mission-control.service
sudo systemctl start mission-control.service
sudo systemctl status mission-control.service
```

## API overview

Common endpoints:

- `GET /healthz`
- `GET /api/status`
- `GET /api/services/health`
- `GET /api/reliability/limits`
- `GET /api/workflows`
- `GET /api/workflows/<workflow_id>/timeline`
- `POST /api/workflows/<workflow_id>/resume`
- `POST /api/workflows/<workflow_id>/cancel`
- `GET /api/dispatch`
- `POST /api/dispatch/enqueue`
- `POST /api/dispatch/<dispatch_id>/start`
- `POST /api/dispatch/<dispatch_id>/cancel`

## Mission Control UI

The UI is a static single-page app. It shows Home, Runs, Workflows, Dispatch, Agents, Tasks, Services, Logs, Nightly, Cron, and Docs. Workflow drawers expose retry count, timeout, failure reason, dispatch ID, PID, stdout/stderr tails, resume actions, and rerun actions.

## Dispatch engine

The dispatch engine builds real Hermes commands by default:

```bash
hermes -p <profile> chat -q "<prompt>" --quiet --max-turns=10
```

Display profile names are normalized to CLI profile aliases before execution.

## Workflow reliability layer

Reliability includes per-step `timeout_seconds`, retry policy, retry history, attempt history, failure classification, resume from failed step, resume from next step, selected step rerun, and synthesis readiness once subtasks finish.

## Why subprocess.Popen is used

`subprocess.Popen` is required because Mission Control needs process supervision, not blocking execution. The runner stores PID, streams stdout/stderr, updates live state, enforces timeouts, supports cancel, captures exit code, and marks terminal status accurately.

`subprocess.run` remains only in helper paths, not in the active dispatch execution path.

## Queue and concurrency limits

The default limits protect a small e2-medium VM:

- max concurrent dispatches: `3`
- max queued dispatches: `25`
- max concurrent workflows: `2`
- max workflow runtime: `3600s`
- max retries per workflow: `6`

Override with `MC_*` environment variables.

## Logs and runtime data

Runtime records are created under `data/`:

- `data/action_log.jsonl`
- `data/dispatch_queue.jsonl`
- `data/runs.jsonl`
- `data/routing_history.jsonl`
- `data/workflow_events.jsonl`

These files are ignored and must not be pushed.

Service logs:

```bash
journalctl -u mission-control.service -n 100 --no-pager
```

## Security notes

- Do not expose Mission Control publicly without auth, reverse proxy protection, firewall rules, or VPN/Tailscale access.
- Do not commit `.env`, tokens, provider keys, cookies, session files, logs, runtime JSONL, or generated uploads.
- Keep provider credentials in Hermes profiles/secrets, not in this repo.
- Run the secret audit before every push.

## Common commands

```bash
systemctl status mission-control.service
systemctl restart mission-control.service
journalctl -u mission-control.service -n 100 --no-pager
curl http://127.0.0.1:8090/healthz
curl http://127.0.0.1:8090/api/status
curl http://127.0.0.1:8090/api/reliability/limits
```

## Verification commands

```bash
python3 -m py_compile server.py dispatch_engine.py
node --check static/app.js
./scripts/verify_mission_control.sh
```

Dispatch runner proof:

```bash
grep -R "subprocess.run" -n dispatch_engine.py server.py || true
grep -R "subprocess.Popen" -n dispatch_engine.py server.py || true
```

## Troubleshooting

- UI not loading: check `systemctl status mission-control.service` and `/healthz`.
- Dispatch stuck queued: check `/api/reliability/limits`.
- Dispatch failed: inspect stdout/stderr tails in the Dispatch UI.
- Hermes profile failure: run `hermes -p <profile> chat -q "hello" --quiet --max-turns=1` manually.
- Port conflict: change `MISSION_CONTROL_PORT` or stop the conflicting service.

## Rollback

```bash
cd /root/mission-control
git reset --hard da163fd
systemctl restart mission-control.service
```

Older Popen milestone:

```bash
git reset --hard 18b4886
systemctl restart mission-control.service
```

## New Hermes agent setup

```bash
git clone <repo-url>
cd kishore-hermes-mission-control
cp .env.example .env
python3 -m py_compile server.py dispatch_engine.py
./scripts/verify_mission_control.sh
```

Then read `SETUP.md`, `OPERATIONS.md`, `ARCHITECTURE.md`, `SECURITY.md`, and `CHANGE_WORKFLOW.md`.

## Ongoing change discipline

Every future Mission Control or Hermes code change must update relevant docs/changelog/examples, run verification, check diff, confirm no secrets/runtime data are staged, commit code and docs together, push to GitHub, and report commit hash, files changed, verification, and push status.

No code change is complete until docs, verification, commit, and push are done.

## Roadmap

- authentication or VPN-only access policy for public exposure
- deeper profile gateway controls
- richer workflow templates
- live output streaming via server-sent events or WebSocket
- CI workflow for syntax/smoke checks
- branch protection once the repo workflow stabilizes
