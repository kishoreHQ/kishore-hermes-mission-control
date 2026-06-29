# 14 — Technical Debt, Risks & Opportunities

---

## Technical Debt Report

### Critical (Address in Phase 0)

| ID | Debt | Location | Remediation |
|----|------|----------|-------------|
| TD-01 | No authentication | server.py | FastAPI auth middleware |
| TD-02 | Monolithic server.py (3,371 lines) | server.py | Split into FastAPI routers |
| TD-03 | Dead dispatch code (~400 lines) | server.py:2556–3087 | Delete after engine wrapper |
| TD-04 | JSONL single-process locking | data/*.jsonl | Postgres migration |
| TD-05 | Runs as root | systemd example | Non-root user in v2 deploy |

### High (Address in Phase 1–2)

| ID | Debt | Remediation |
|----|------|-------------|
| TD-06 | No SSE (docs claim it) | Implement Redis pub/sub + SSE |
| TD-07 | Hardcoded `/root` paths | Env-based `HERMES_HOME`, `DATA_DIR` |
| TD-08 | Browser prompt() approval | ApprovalModal component |
| TD-09 | Stubbed search | Semantic search Phase 4 |
| TD-10 | workflow_dispatch_all_ready shadowing | Remove duplicate; use engine only |
| TD-11 | SQL injection risk in session query | Parameterized queries |
| TD-12 | Two-repo naming collision | Archive mission-control-dashboard |

### Medium (Address in Phase 3–6)

| ID | Debt | Remediation |
|----|------|-------------|
| TD-13 | No API integration tests | pytest + httpx |
| TD-14 | No CI/CD | GitHub Actions |
| TD-15 | Global state object S in app.js | Retire with Next.js |
| TD-16 | No OpenAPI spec | FastAPI auto-gen |
| TD-17 | SETUP.md / requirements.txt contradiction | Update docs |
| TD-18 | Synthetic test data toggle in prod UI | Dev-only env flag |
| TD-19 | audit_scheduled_jobs.sh hardcodes /root/mission-control | Env-based paths |
| TD-20 | Profile routing index has /root paths in committed JSON | Sanitize paths |

---

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| **Scope creep** — 45 modules before Today works | High | Critical | Strict phase gates; plugin architecture |
| **Rewrite dispatch_engine** instead of reuse | Medium | High | Wrap as service; no rewrite |
| **Migration data loss** | Medium | High | JSONL importer with validation; parallel run |
| **No daily habit formed** | Medium | High | Ship Today first; measure daily opens |
| **SSE complexity on VPS** | Low | Medium | Polling fallback; Redis optional in dev |
| **Hermes CLI breaking changes** | Medium | Medium | Pin Hermes version; adapter layer |
| **Postgres ops burden on VPS** | Low | Medium | docker-compose; backup script in nightly DAG |
| **AI cost runaway** | Medium | Medium | Budget alerts; per-dispatch limits |
| **Abandon mid-build** | Medium | Critical | 6-month phased value; each phase usable |

---

## Opportunities

| Opportunity | Value | Phase |
|-------------|-------|-------|
| **Today as daily habit** | Transforms MC from ops tool to life OS | 1 |
| **Nightly automation** | 2 AM work → morning clarity | 3 |
| **Plugin marketplace** | Community/share widgets | 5+ |
| **Open-source Hermes OS** | Others with agent fleets need this | 6+ |
| **Headless agent-trace UI** | Reusable component package | 2 |
| **Tag system from spec repo** | Better cron fleet filtering | 2 |
| **Langfuse-style cost tracking** | Control LLM spend | 4 |
| **Knowledge graph over wiki** | Visual second brain | 5 |
| **Tailscale-native auth** | Zero-config secure access | 0 |
| **Cursor SDK integration** | Trigger agents from IDE | 6+ |

---

## Recommended Stack (Final)

| Layer | Choice | Justification |
|-------|--------|---------------|
| Monorepo | Turborepo | JS + Python coexist; shared types |
| Frontend | Next.js 15 + TS | App Router, RSC, ecosystem |
| UI | shadcn/ui + Tailwind | Matches Linear/Vercel quality |
| State | TanStack Query + Zustand | Server vs UI separation |
| API | FastAPI | Python ecosystem; wraps dispatch_engine |
| ORM | SQLAlchemy 2 + Alembic | Migrations, typed models |
| DB | Postgres 16 + pgvector | One DB for state + vectors |
| Cache/Queue | Redis 7 | Pub/sub, job queue, sessions |
| Realtime | SSE + Redis pub/sub | Simple, sufficient |
| Scheduler | APScheduler | Python-native nightly cron |
| CI | GitHub Actions | Lint, test, build on push |
| Deploy | systemd + docker-compose | VPS-native; Tailscale access |
| Auth | Tailscale + session cookie | Single-user; no OAuth complexity |

---

*Next: [15-implementation-and-sprint-plan.md](./15-implementation-and-sprint-plan.md)*
