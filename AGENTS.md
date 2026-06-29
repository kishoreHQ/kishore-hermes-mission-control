# Mission Control -- AGENTS.md

> **Read this first if you are an AI coding agent (Cursor, Copilot, Claude Code, Codex, OpenCode, Gemini, Qwen, etc.).**

## What this repo is

**Mission Control** is a Python stdlib web app that gives a single UI for:

- **Hermes dispatch** -- send prompts to a chosen Hermes profile and see live output
- **Reliability limits** -- throttle concurrent dispatches, queue depth, retry budget
- **Recent files** -- unified browse across `HERMES_HOME`, `career-ops/interview-prep`, `wiki`, cron output
- **Workflow runs** -- the JSONL log of all past dispatches
- **Routing history** -- which profile handled which prompt

It is a **server + JSON UI**, not a CLI. The Python side is stdlib-only (no pip deps). The frontend is a single `static/app.js` file.

## Hermes OS V2 (production path)

**V2** is the live dashboard at `https://gcp-hermes.tail57c68b.ts.net/today` (native systemd, no Docker).

```bash
git clone https://github.com/kishoreHQ/kishore-hermes-mission-control.git
cd kishore-hermes-mission-control

# VPS production
HERMES_DATA_DIR=/root/mission-control/data HERMES_HOME=/root/.hermes ./scripts/vps-native.sh setup
./scripts/vps-native.sh install-services
./scripts/vps-native.sh start
./scripts/vps-native.sh tailscale

# Local Mac demo
./scripts/dev-mac.sh api   # terminal 1
./scripts/dev-mac.sh web   # terminal 2
```

- **Product spec:** `docs/PRD_V2.md`
- **Deploy:** `docs/DEPLOYMENT.md`
- **API:** `http://127.0.0.1:8000/api/v1/docs`
- **Retire V1:** `./scripts/retire-v1.sh` (stops `mission-control.service` on :8090)

## Quickstart V1 (deprecated)

V1 (`make run` on port 8090) is **retired** in production. The code remains in `server.py` for reference. Use V2 above.

```bash
# 1. Clone
git clone https://github.com/kishoreHQ/kishore-hermes-mission-control.git
cd kishore-hermes-mission-control

# 2. Verify (compile + smoke checks, no network)
make verify

# 3. Configure
cp .env.example .env
# edit .env if needed (defaults are fine for a local dev box)

# 4. Start
make run     # starts the server on http://127.0.0.1:8090

# 5. Open
curl http://127.0.0.1:8090/healthz
# Expected: "ok"
```

That's it. Mission Control has **no pip dependencies**. The only thing the server needs is `python3` (3.10+).

For a full systemd install (production / remote), see `SETUP.md` step 9.

## Repo structure

```
.
|-- AGENTS.md                       <-- you are here
|-- SETUP.md                        <-- 13-step fresh VM setup
|-- README.md                       <-- feature overview
|-- ARCHITECTURE.md                 <-- module map
|-- OPERATIONS.md                   <-- runbook
|-- SECURITY.md
|-- CHANGE_WORKFLOW.md
|-- CHANGELOG.md
|-- CONTRIBUTING.md
|
|-- Makefile                        <-- canonical command surface
|-- server.py                       <-- stdlib HTTP server + handlers
|-- dispatch_engine.py              <-- Hermes profile dispatch
|-- mission-control.service.example <-- systemd unit template
|
|-- .env.example
|-- .gitignore
|
|-- scripts/
|   |-- verify_mission_control.sh   <-- live smoke check (needs server up)
|   `-- audit_scheduled_jobs.sh     <-- cron job inventory
|
|-- static/
|   `-- app.js                      <-- frontend
|
|-- data/                           <-- runtime JSONL state (gitignored except .gitkeep)
|-- logs/                           <-- runtime logs (gitignored except .gitkeep)
|-- examples/
|-- docs/                           <-- design notes, audits, plans
|
`-- tests/
    `-- test_portability.py         <-- 20 pytest checks
```

## Configuration

All config is via env vars (`.env` file or system env). Defaults are in `.env.example`.

| Var | Default | Required? | Purpose |
|-----|---------|-----------|---------|
| `MISSION_CONTROL_HOST` | `127.0.0.1` | no | Bind address. Use `0.0.0.0` for network access (with auth!) |
| `MISSION_CONTROL_PORT` | `8090` | no | HTTP port |
| `HERMES_HOME` | `~/.hermes` | no | Where Mission Control looks for profiles and CLI binary |
| `MC_MAX_CONCURRENT_DISPATCHES` | (default) | no | Throttle: how many Hermes processes at once |
| `MC_MAX_QUEUED_DISPATCHES` | (default) | no | Throttle: max queue depth before rejection |
| `MC_MAX_CONCURRENT_WORKFLOWS` | (default) | no | Throttle: parallel workflow limit |
| `MC_MAX_WORKFLOW_RUNTIME_SECONDS` | (default) | no | Hard timeout per workflow |
| `MC_MAX_RETRIES_PER_WORKFLOW` | (default) | no | Max retry attempts |

`.env` is in `.gitignore` and never committed.

## Commands (Makefile targets)

| Target | What it does |
|--------|--------------|
| `make help` | Show all targets |
| `make setup` | Create data/log dirs, install gitkeep, verify deps |
| `make verify` | Compile-check Python + JS + run pytest portability tests (no network) |
| `make verify-live` | Same as `verify` + smoke test against running server (requires `make run` first) |
| `make run` | Start the server in foreground (Ctrl-C to stop) |
| `make serve-bg` | Start the server in background, write PID to `data/server.pid` |
| `make stop` | Stop the background server |
| `make logs` | Tail the runtime logs |
| `make health` | Curl `/healthz` (server must be running) |
| `make audit-jobs` | Run `scripts/audit_scheduled_jobs.sh` |
| `make clean` | Stop server, remove data/* and logs/* |
| `make lint` | Compile-check Python sources |

## How the dispatch engine works

1. Browser POSTs `{profile, prompt, ...}` to `/api/dispatch`
2. `server.py` validates against reliability limits
3. `dispatch_engine.py` shells out to the Hermes CLI (`hermes -p <profile> chat -q "<prompt>" --quiet --max-turns=1`)
4. Output streams back to the browser via Server-Sent Events
5. The whole run is logged to `data/runs.jsonl` with timestamps, profile, prompt hash, exit code, duration

The dispatch engine respects `HERMES_HOME` for profile discovery and the throttle limits for fairness.

## What "agent-cloneable" means here

After `git clone`, an agent should be able to:

1. `make verify` -> all 20 pytest checks pass (Python compiles, JS parses, no hardcoded paths, runtime dirs present, .env.example documented)
2. `make setup` -> data/ and logs/ dirs ready
3. `cp .env.example .env && make run` -> server listens on 127.0.0.1:8090
4. `curl /healthz` -> returns `ok`

If any of those fail, the repo is broken. `tests/test_portability.py` enforces 1-3.

## Systemd install (production)

See `SETUP.md` step 9. The short version:

```bash
# Edit the service template to match your install path
sed "s|/root/mission-control|$(pwd)|g" mission-control.service.example > /tmp/mc.service
sudo cp /tmp/mc.service /etc/systemd/system/mission-control.service
sudo systemctl daemon-reload
sudo systemctl enable --now mission-control.service
sudo systemctl status mission-control.service
```

## Troubleshooting

- **`curl /healthz` returns connection refused** -> server is not running. `make run` (foreground) or `make serve-bg` (background).
- **`hermes: command not found`** -> install Hermes CLI. The server uses it for actual dispatches. `command -v hermes` should print a path.
- **`PermissionError: data/action_log.jsonl`** -> `chmod 664 data/*.jsonl` (or run as the user that should own them).
- **Throttle rejection (`429 Too Many Requests`)** -> you hit `MC_MAX_CONCURRENT_DISPATCHES`. Wait or raise the limit in `.env`.
- **Port 8090 already in use** -> change `MISSION_CONTROL_PORT` in `.env`.

## Related repos (same family)

- `career-ops` -- AI job-search pipeline (Mission Control browses its `interview-prep/`)
- `aicreator` -- AI influencer content factory
- `StockForge` -- Indian stock-market intelligence

## License

Personal project. See `LICENSE` if present.
