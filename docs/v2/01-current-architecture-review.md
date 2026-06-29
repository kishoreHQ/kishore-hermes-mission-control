# 01 — Current Architecture Review

**Scope:** `kishore-hermes-mission-control` (working app) + `mission-control-dashboard` (spec repo)

---

## 1. Repository Landscape

### kishore-hermes-mission-control (Production)

```
kishore-hermes-mission-control/
├── server.py              146 KB / 3,371 lines — HTTP server + all API routes
├── dispatch_engine.py      84 KB / 1,830 lines — orchestration engine
├── static/
│   ├── index.html           8.6 KB — SPA shell
│   ├── app.js              58 KB / 790 lines — UI controller
│   └── styles.css          19 KB — "Calm Command" design system
├── data/                   Config JSON + runtime JSONL (gitignored)
├── docs/                   Architecture, UI research, redesign plan
├── scripts/                Audit + verify scripts
├── tests/                  Portability tests only
└── Makefile                setup, verify, run, audit-jobs
```

**Git:** 5 commits, standalone decomp from Hermes monolith (phase 4).

### mission-control-dashboard (Spec Only)

```
mission-control-dashboard/
├── README.md               16 KB — architecture + setup guide
├── docs/                   ARCHITECTURE, DATA_SOURCES, API_REFERENCE, UI_SPEC, TAG_SYSTEM
├── config/.env.example     Vite env template
└── scripts/setup.sh        Bootstrap (expects missing dashboard/ app)
```

**Git:** 1 commit. No application source code.

---

## 2. Backend Architecture

### Framework

Python **stdlib only** — no Flask, FastAPI, or framework:

```python
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
```

- `Handler` subclasses `SimpleHTTPRequestHandler`
- Manual `do_GET` / `do_POST` path matching (~100 routes)
- Serves `static/` as document root
- Binds `MISSION_CONTROL_HOST` (default `127.0.0.1`) / `MISSION_CONTROL_PORT` (default `8090`)

### server.py Responsibilities

| Concern | Implementation |
|---------|----------------|
| HTTP routing | Manual path matching, no router |
| Aggregated status | `api_status()` mega JSON for UI |
| Service registry | `data/services.json` + systemd/HTTP probes |
| Cron integration | Reads `$HERMES_HOME/cron/jobs.json` |
| Profile routing v2 | Token scoring vs `profile_routing_index.json` |
| Multi-profile workflows | CRUD in `workflows_multi.json` |
| Runs tracking | JSONL + Telegram notifications |
| Tasks / Kanban | `tasks.json` |
| Nightly builds | `nightly_builds.json` + base64 uploads |
| Safe actions | safe/medium/high tiers, 600s approval TTL |
| Logs | `journalctl -u <service>` wrapper |
| Session analytics | Read-only SQLite on `$HERMES_HOME/state.db` |
| **Dead code** | ~400 lines inline dispatch block shadowed by `dispatch_engine` import |

### dispatch_engine.py (Crown Jewel)

| Capability | Detail |
|------------|--------|
| Queue persistence | `data/dispatch_queue.jsonl` append-only |
| Concurrency | `MC_MAX_CONCURRENT_DISPATCHES=3`, queued=25, workflows=2 |
| Execution | `subprocess.Popen` + reader threads + timeout kill |
| Command | `hermes -p <cli_alias> chat -q ... --max-turns=10` |
| Failure taxonomy | timeout, cancelled, provider_error, rate_limited, etc. |
| Workflow orchestration | DAG deps, parallel dispatch, synthesis |
| Resume modes | failed step, next step (skip), selected step rerun |

**Verdict:** Preserve and wrap as a service. Do not rewrite.

---

## 3. API Surface (~100 Endpoints)

### Categories

| Category | Key Endpoints |
|----------|---------------|
| Health | `GET /healthz`, `GET /api/status` |
| Services | `GET /api/services`, `/api/services/health` |
| Actions | `POST /api/actions/prepare`, `/execute`, `/run` |
| Runs | `GET/POST /api/runs/*` |
| Profiles | `GET /api/profiles`, `POST /api/profiles/edit`, routing APIs |
| Tasks | `GET/POST /api/tasks`, move/archive/assign/decompose |
| Workflows | Full CRUD + subtask lifecycle + dispatch |
| Dispatch | Enqueue, start, complete, fail, retry, cancel, live logs |
| Nightly | `GET/POST /api/nightly-builds`, upload |
| Gateways | Profile gateway test/start/stop/restart |

No OpenAPI schema. No versioning. No middleware stack.

---

## 4. Data Model

### Committed Config (data/)

| File | Purpose |
|------|---------|
| `workflows.json` | 7 operational lanes (hermes-core, ai-creator, career-ops, stockforge, claw3d, memory-wiki, contentforge) |
| `services.json` | 5 registered services with ports, systemd units, Tailscale URLs |
| `profile_settings.json` | profile_mode, default_profile, keyword routing |
| `profile_routing_index.json` | SOUL.md keywords, best_for/avoid_for per profile |
| `routing_threshold.json` | auto-accept/ask/fallback score thresholds |
| `docs.json` | Governance copy for UI |

### Runtime (gitignored)

| File | Format |
|------|--------|
| `dispatch_queue.jsonl` | Append-only dispatch records |
| `runs.jsonl` | Run history |
| `routing_history.jsonl` | Routing decisions |
| `workflow_events.jsonl` | Workflow events |
| `action_log.jsonl` | Action audit trail |
| `tasks.json` | Kanban state |
| `nightly_builds.json` | Build registry |
| `workflows_multi.json` | Active workflow instances |

### External (Hermes)

| Source | Access |
|--------|--------|
| `$HERMES_HOME/cron/jobs.json` | Cron job definitions |
| `$HERMES_HOME/state.db` | SQLite session/token stats (read-only) |
| `$HERMES_HOME/cron/output/` | Job output logs |

**Limitations:** Thread lock only (not multi-process safe), no migrations, no referential integrity, no full-text search.

---

## 5. Frontend Architecture

### Stack

Plain HTML + vanilla JS + custom CSS. No framework, no bundler, no TypeScript.

### Structure

- Single-page app with **section-based navigation** (show/hide, not routes)
- Global state object `S` in `app.js`
- 11 sections: Home, Runs, Workflows, Dispatch, Agents, Tasks, Services, Logs, Nightly, Cron, Docs
- Command palette (`⌘K`), right drawer for details
- 30-second `setInterval(load, 30000)` polling
- Search input stubbed: `/* future: filter within current section */`

### Design System ("Calm Command")

- Dark-first CSS variables (`--bg-base`, `--accent`, `--ok/warn/err`)
- BEM-style `.mc-*` classes
- Responsive: sidebar desktop, bottom bar mobile (<900px)

---

## 6. Automation & Scheduling

Mission Control **does not run cron**. It observes and controls:

1. **Hermes cron scheduler** — reads jobs, exposes in `/api/status`
2. **Medium-risk actions** — `run_cron`, `pause_cron`, `resume_cron` via Hermes CLI
3. **System crontab** — audited by `scripts/audit_scheduled_jobs.sh`, not managed

**Nightly builds:** Manual tracking UI with lifecycle Built → Testing → Feedback → Fix → Promote. **Not** an automated pipeline.

### Documented Cron Ecosystem (14+ Hermes jobs)

ContentForge (5), StockPulse (4), Career Ops, Daily Priority, Config Sync, gbrain, Micro-System Builder (2), DevSecOps, StockForge, Morning Intelligence.

---

## 7. Deployment

- **Production:** systemd via `mission-control.service.example`
- **Runs as:** root
- **Path:** `/root/mission-control`
- **Access:** localhost:8090 or Tailscale
- **No:** CI/CD, containerization, health checks beyond `/healthz`

---

## 8. Technical Debt Summary

| Severity | Issue |
|----------|-------|
| Critical | No authentication |
| Critical | Monolithic server.py (3,371 lines) |
| Critical | Dead/duplicated dispatch code in server.py |
| High | JSONL single-process file locking |
| High | No SSE despite docs claiming it |
| High | Hardcoded `/root` paths throughout |
| Medium | No API tests |
| Medium | Stubbed search |
| Medium | `workflow_dispatch_all_ready` shadowed/aliased incorrectly |
| Low | SETUP.md contradicts requirements.txt existence |

---

## 9. What the Spec Repo Got Right

From `mission-control-dashboard`:

- **Tag system** (`#content`, `#finance`, `#nightly`) — adopt for agent fleet filtering
- **Data adapter pattern** (Local/SSH/API) — useful for remote Mac → VPS access
- **Three connection modes** — local, Tailscale, API
- **UI wireframes** — 5-panel layout concept (fleet, operations, content, health, control)

What it got wrong: proposing a separate React-only client without backend, duplicating repo naming, never shipping code.

---

*Next: [02-ux-and-design-audit.md](./02-ux-and-design-audit.md)*
