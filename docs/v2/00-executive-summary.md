# 00 — Executive Summary

**Project:** Mission Control V2 → Hermes OS  
**Date:** June 2026  
**Status:** Strategy approved; implementation in progress

---

## The Verdict

You have **two repositories pretending to be one product**:

| Repository | Reality |
|------------|---------|
| `mission-control-dashboard` | Single-commit **docs-only spec** for a React/Tailscale rewrite. No app code. Never built. |
| `kishore-hermes-mission-control` | **Working production system**: ~3,400-line stdlib `server.py`, ~1,800-line `dispatch_engine.py`, vanilla-JS SPA on port 8090. |

**Decision:** Archive `mission-control-dashboard`. Preserve its hashtag tag-system idea. Build V2 as a Turborepo monorepo inside `kishore-hermes-mission-control` (or a renamed `hermes-os` repo).

---

## What Works Today (Keep)

- **Dispatch engine** — Real Popen supervision, heartbeat, timeout/cancel, failure taxonomy, retry/resume, workflow DAG orchestration. This is production-grade orchestration logic.
- **Safety model** — Safe/medium/high action tiers with approval codes.
- **Profile routing v2** — Token scoring against `profile_routing_index.json`.
- **UI redesign (Phases 1–5)** — "Calm Command" design system, command palette, operations cockpit, drawer details.
- **Hermes integration** — Real `hermes -p <profile> chat` execution, cron visibility, service health probes.

---

## What Must Change (Brutal Honesty)

| Area | Problem |
|------|---------|
| **Product scope** | Fleet observability admin panel, not a personal AI OS |
| **Architecture** | Monolithic 3,400-line server.py, dead duplicated dispatch code |
| **Data** | JSONL file locking, single-process, no queries, no integrity |
| **Realtime** | 30s polling; docs claim SSE but none exists |
| **Security** | No auth; runs as root; hardcoded `/root` paths |
| **AI-native** | No ask-anything, semantic search, recommendations, RCA |
| **Nightly builds** | Manual tracking UI, not an automated 2 AM pipeline |
| **Daily value** | No morning briefing, no life/work integration |
| **Extensibility** | 11 hardcoded sections; every module is bespoke |
| **Tests** | Portability checks only; no API/integration tests |

---

## V2 Direction: Hermes OS

Transform Mission Control from an **admin dashboard** into a **personal AI operating system** — the single interface opened every morning.

### Four Laws

1. **Surface, don't store** — Show what matters now; raw data lives behind search.
2. **Coordinate the AI workforce** — Agents and workflows are first-class, observable, steerable.
3. **Automate the repetitive** — Nightly pipelines do boring work; you review results.
4. **Help me think and create** — Ask-anything, recommendations, semantic memory across domains.

### Stack (Hybrid — Approved)

| Layer | Technology |
|-------|------------|
| Frontend | Next.js 15 (App Router) + TypeScript + Tailwind + shadcn/ui |
| API Gateway | FastAPI + Pydantic v2 + OpenAPI |
| Orchestration | Reused `dispatch_engine.py` as a service |
| Data | Postgres + Redis + pgvector |
| Realtime | SSE (primary), WebSocket (bidirectional only) |
| Repo | Turborepo monorepo |

---

## Scope Control

Your module wishlist has ~45 surfaces. Built naively, this becomes an abandoned mega-dashboard.

**Solution:** 9 domain **Spaces** + plugin/widget registry. Ship **Today** first (daily-driver value), then **Agents & Automation** (existing capability), then domain plugins.

---

## 6-Month Outcome

| Month | Deliverable |
|-------|-------------|
| 1 | Foundation + Today surface + realtime |
| 2 | Agents & Automation ported |
| 3 | Nightly pipeline + Insights |
| 4 | AI-native layer |
| 5–6 | Domain plugins + polish |

---

## Biggest Risks

1. **Scope creep** — 45 modules before Today works
2. **Rewrite vs. reuse** — Throwing away dispatch_engine
3. **Two-repo confusion** — Maintaining parallel efforts
4. **No daily habit** — Building ops tools nobody opens daily

---

## Recommended First Sprint

1. Monorepo scaffold
2. FastAPI gateway wrapping existing APIs
3. Postgres + JSONL importer
4. Next.js shell with 9-space nav + command palette
5. **Today briefing surface** — first thing you see every morning

---

*Next: [01-current-architecture-review.md](./01-current-architecture-review.md)*
