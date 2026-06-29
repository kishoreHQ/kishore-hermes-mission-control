# 15 — Implementation & Sprint Plan

---

## Sprint Structure

- **Sprint length:** 2 weeks
- **Total sprints:** 13 (26 weeks / 6 months)
- **Review:** End of each sprint — demo + retrospective

---

## Sprint 1 (Weeks 1–2): Foundation

### Goals
Monorepo live; FastAPI serves health; Postgres connected; dispatch_engine importable.

### Tasks
| Task | Owner | Points |
|------|-------|--------|
| Create Turborepo structure (apps/web, apps/api, packages/*) | Dev | 5 |
| Move server.py + dispatch_engine.py to legacy/ | Dev | 2 |
| FastAPI main.py with /healthz, /api/v1/openapi.json | Dev | 3 |
| SQLAlchemy models + Alembic init | Dev | 5 |
| docker-compose.yml (postgres, redis, api, web) | Dev | 3 |
| Legacy adapter: read dispatch_queue.jsonl | Dev | 5 |
| dispatch_service wrapper over dispatch_engine | Dev | 8 |
| JSONL importer script | Dev | 5 |
| GitHub Actions: lint + py_compile + build | Dev | 3 |
| Archive mission-control-dashboard (README redirect) | Dev | 1 |

### Acceptance
- [ ] `docker compose up` starts all services
- [ ] `curl localhost:8000/healthz` returns ok
- [ ] `GET /api/v1/dispatch` returns data from legacy or Postgres
- [ ] CI green on main

---

## Sprint 2 (Weeks 3–4): Shell

### Goals
Next.js app with 9-space nav, command palette, design system.

### Tasks
| Task | Points |
|------|--------|
| Next.js 15 app scaffold in apps/web | 3 |
| packages/ui: shadcn init + Calm Command theme | 5 |
| AppShell: Sidebar, TopBar, Drawer | 8 |
| 9-space routing (app/(spaces)/*) | 5 |
| Command palette (cmdk) | 5 |
| packages/sdk API client | 3 |
| packages/types from OpenAPI | 3 |
| Mobile bottom nav | 3 |

### Acceptance
- [ ] Navigate all 9 spaces
- [ ] ⌘K opens palette with navigate actions
- [ ] Dark theme matches design tokens

---

## Sprint 3 (Week 5): Today + Realtime

### Goals
Today briefing surface; SSE streaming.

### Tasks
| Task | Points |
|------|--------|
| today_service aggregator | 5 |
| GET /api/v1/today endpoint | 3 |
| Today page: greeting, metrics, attention | 8 |
| Agenda component (tasks due today) | 3 |
| Quick actions bar | 3 |
| Redis pub/sub + SSE /api/v1/stream/events | 8 |
| SSE client in web | 3 |
| Nightly report panel (stub data) | 3 |

### Acceptance
- [ ] Today loads in <2s
- [ ] Dispatch update appears via SSE without refresh
- [ ] Needs-attention shows failed crons/services

---

## Sprint 4 (Weeks 6–7): Agents Core

### Goals
Fleet, Workflows, Dispatch ported.

### Tasks
| Task | Points |
|------|--------|
| Agent fleet cards + hashtag tags | 5 |
| Workflow list + detail drawer | 8 |
| Span-tree timeline component | 8 |
| Dispatch queue + live log viewer | 8 |
| Approval modal (medium-risk) | 5 |
| Port action prepare/execute APIs | 5 |

### Acceptance
- [ ] Enqueue dispatch from V2 UI
- [ ] See live stdout via SSE
- [ ] Cancel dispatch works

---

## Sprint 5 (Week 8): Cron + Infra

### Goals
Cron grid; services; logs.

### Tasks
| Task | Points |
|------|--------|
| Cron grid with tags (#content, etc.) | 5 |
| Run/pause/resume cron actions | 5 |
| Services health cards | 5 |
| Log viewer with severity | 5 |
| Infrastructure space complete | 3 |

### Acceptance
- [ ] v1 UI not needed for daily ops

---

## Sprint 6 (Weeks 9–10): Nightly Pipeline

### Goals
Real 2 AM automation.

### Tasks
| Task | Points |
|------|--------|
| nightly-dag.yaml | 3 |
| scheduler_service + APScheduler | 8 |
| Job executor (dispatch + script) | 8 |
| Artifact storage | 5 |
| Morning report Jinja template | 5 |
| Nightly UI in Agents space | 5 |

### Acceptance
- [ ] Manual trigger runs full DAG
- [ ] Artifacts saved and viewable
- [ ] Today shows morning report

---

## Sprint 7 (Week 11): Insights

### Goals
Timeline, activity feed, trends.

### Tasks
| Task | Points |
|------|--------|
| Unified activity feed | 5 |
| Nightly success rate chart | 5 |
| Insights space | 3 |
| Export report action | 3 |

---

## Sprints 8–10 (Weeks 12–15): AI Layer

| Sprint | Focus |
|--------|-------|
| 8 | pgvector, embedding pipeline |
| 9 | Semantic search + AI chat |
| 10 | RCA, recommendations, cost analytics |

---

## Sprints 11–13 (Weeks 16–26): Plugins + Polish

| Sprint | Focus |
|--------|-------|
| 11–12 | Plugin registry + Create/Knowledge plugins |
| 12–13 | Wealth/Life plugins |
| 13 | a11y, PWA, security, v1 retirement, v2.0.0 tag |

---

## Definition of Done (Global)

- [ ] TypeScript strict mode passes
- [ ] Python ruff/mypy passes
- [ ] API endpoint has Pydantic model
- [ ] UI component uses packages/ui tokens
- [ ] Keyboard accessible
- [ ] Works in docker-compose dev
- [ ] No secrets in code

---

## Immediate Next Steps (Post-Approval)

1. Run Sprint 1 tasks (monorepo scaffold in this repo)
2. Archive `mission-control-dashboard` with pointer README
3. Demo Today shell to validate direction
4. Begin daily use of V2 for Today + Agents by end of Sprint 5

---

*End of V2 Strategy Dossier*
