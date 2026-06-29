# 13 — 6-Month Roadmap & Prioritized Backlog

---

## 6-Month Roadmap

### Month 1: Foundation + Today (Weeks 1–5)
**Goal:** Daily-driver shell; first morning briefing

| Week | Deliverables |
|------|--------------|
| 1–2 | Monorepo, FastAPI gateway, Postgres, JSONL importer, auth stub, CI |
| 3–4 | Next.js shell, 9-space nav, command palette, design system package |
| 5 | Today surface, SSE streaming, needs-attention, metric cards |

**Exit criteria:** Open `http://localhost:3000/today` every morning; see briefing in <30s.

---

### Month 2: Agents & Automation (Weeks 6–8)
**Goal:** Port all v1 orchestration to V2 UI

| Week | Deliverables |
|------|--------------|
| 6 | Agent Fleet, Cron with tags |
| 7 | Workflows + span-tree timeline, Dispatch live view |
| 8 | Actions (safe/medium), approval modal, service health |

**Exit criteria:** Retire v1 UI for daily ops; v1 API proxied through FastAPI.

---

### Month 3: Nightly Pipeline + Insights (Weeks 9–11)
**Goal:** Real 2 AM automation

| Week | Deliverables |
|------|--------------|
| 9 | Scheduler service, nightly-dag.yaml, job execution |
| 10 | Artifacts, morning report, Today integration |
| 11 | Insights timeline, activity feed, nightly trends |

**Exit criteria:** Wake up to morning report; nightly success rate visible.

---

### Month 4: AI-Native Layer (Weeks 12–15)
**Goal:** Ask-anything + semantic search

| Week | Deliverables |
|------|--------------|
| 12 | pgvector, embedding pipeline, index job |
| 13 | Semantic search UI, global AI chat (⌘J) |
| 14 | Auto-RCA, Today recommendations |
| 15 | LLM cost analytics dashboard |

**Exit criteria:** "What failed last night?" answered in chat with citations.

---

### Month 5: Domain Plugins (Weeks 16–22)
**Goal:** Create, Knowledge, Wealth, Life, Infrastructure plugins

| Week | Deliverables |
|------|--------------|
| 16–17 | Plugin registry, widget loader |
| 18 | Create space (ContentForge) |
| 19 | Knowledge space (wiki, research) |
| 20 | Wealth space (StockForge) |
| 21 | Life space (career, calendar stub) |
| 22 | Infrastructure space (full port) |

---

### Month 6: Polish & Hardening (Weeks 23–26)
**Goal:** Production-ready personal OS

| Week | Deliverables |
|------|--------------|
| 23 | a11y audit, keyboard shortcuts complete |
| 24 | Performance (LCP <2s), PWA offline Today |
| 25 | Observability, security review, non-root deploy |
| 26 | Docs, v1 retirement, release tag `v2.0.0` |

---

## Prioritized Backlog

### Epic 1: Foundation (P0)
- [ ] Turborepo monorepo scaffold
- [ ] FastAPI app with health + OpenAPI
- [ ] Postgres + Alembic migrations
- [ ] Redis connection
- [ ] JSONL→Postgres importer
- [ ] Legacy adapter (proxy v1 file reads)
- [ ] dispatch_engine import wrapper
- [ ] GitHub Actions CI (lint, test, build)
- [ ] docker-compose dev environment
- [ ] Session auth middleware

### Epic 2: Shell + Today (P0)
- [ ] App shell (sidebar, topbar, drawer)
- [ ] 9-space navigation routing
- [ ] Command palette (cmdk)
- [ ] Calm Command theme in packages/ui
- [ ] Today page with metric cards
- [ ] Needs-attention component
- [ ] Agenda list (tasks due today)
- [ ] Quick actions bar
- [ ] SSE client + Redis pub/sub
- [ ] Mobile bottom nav

### Epic 3: Agents (P0)
- [ ] Agent fleet cards with tags
- [ ] Workflow list + detail drawer
- [ ] Dispatch queue + live logs
- [ ] Cron grid with run/pause/resume
- [ ] Span-tree timeline component
- [ ] Approval modal (replace prompt())

### Epic 4: Nightly (P1)
- [ ] nightly-dag.yaml config
- [ ] Scheduler service (APScheduler)
- [ ] Job executor (dispatch + script types)
- [ ] Artifact storage
- [ ] Morning report generator
- [ ] Nightly UI in Agents space
- [ ] Today nightly report panel

### Epic 5: AI (P1)
- [ ] embeddings table + pgvector
- [ ] index_knowledge script
- [ ] POST /api/v1/ai/ask
- [ ] POST /api/v1/ai/search
- [ ] POST /api/v1/ai/rca
- [ ] AI chat bar component
- [ ] Recommendations on Today
- [ ] LLM usage tracking

### Epic 6: Plugins (P2)
- [ ] Plugin manifest schema
- [ ] Widget registry
- [ ] @hermes/plugin-content
- [ ] @hermes/plugin-knowledge
- [ ] @hermes/plugin-wealth
- [ ] Plugin marketplace UI (System)

### Epic 7: Polish (P2)
- [ ] WCAG AA audit
- [ ] prefers-reduced-motion
- [ ] PWA service worker
- [ ] OpenTelemetry traces
- [ ] Prometheus metrics
- [ ] Security hardening
- [ ] v1 server.py retirement

---

## What NOT to Build (Backlog Exclusions)

- Multi-user RBAC
- Visual workflow builder (n8n-style)
- Mobile native apps
- Public SaaS deployment
- Gamification / streaks
- 45 modules before Today works

---

*Next: [14-tech-debt-risks-opportunities.md](./14-tech-debt-risks-opportunities.md)*
