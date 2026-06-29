# 03 — Feature Gap Analysis

**Method:** Current capability vs. industry best practice → gap → priority → complexity → value → implementation

---

## Gap Matrix

| # | Capability | Current | Best Practice | Gap | Priority | Complexity | Business Value | User Value | Implementation | Expected Impact |
|---|------------|---------|---------------|-----|----------|------------|----------------|------------|----------------|-----------------|
| 1 | **Realtime updates** | 30s polling | SSE/token streaming (LangGraph Studio, Langfuse) | No live feel | P0 | M | High | High | Redis pub/sub + SSE hub in FastAPI; client EventSource | Operators see dispatch complete in <1s |
| 2 | **Data persistence** | JSONL files, thread lock | Postgres + migrations | No query, scale, integrity | P0 | L | High | Medium | SQLAlchemy + Alembic; JSONL→PG importer | Reliable state, complex queries |
| 3 | **Authentication** | None (localhost only) | Session/SSO + secrets manager | Exposed if off-localhost | P0 | M | Critical | Medium | Tailscale + simple session cookie or Authelia | Safe remote access |
| 4 | **Daily briefing surface** | Ops-only Home | Intent-driven Today (Life OS) | No daily-driver value | P0 | M | High | Critical | Today space with nightly report + agenda widgets | **Opens every morning** |
| 5 | **AI ask-anything** | None | Natural language over all data (Perplexity, Cursor) | Not AI-native | P1 | L | High | Critical | AI service + tool registry + pgvector RAG | Single interface for questions |
| 6 | **Nightly automation** | Manual build tracker | Scheduled DAG + artifacts (Temporal, Airflow) | Core promise unbuilt | P1 | L | High | High | APScheduler → Redis queue → dispatch; morning report gen | 2 AM work happens automatically |
| 7 | **Plugin architecture** | 11 hardcoded sections | Widget registry (Homepage, Homarr) | Every module bespoke | P1 | L | High | Medium | Plugin manifest + widget loader in Next.js | Add modules without core changes |
| 8 | **Semantic search** | Stubbed text filter | Vector search across all domains | Can't find anything | P1 | M | Medium | High | pgvector + embed pipeline on index cron | Cross-project understanding |
| 9 | **LLM cost analytics** | SQLite peek | Langfuse usage_details/cost_details | No spend control | P2 | M | High | Medium | OTel GenAI + Postgres aggregates + dashboard | Budget alerts, per-feature cost |
| 10 | **Workflow visualization** | Basic timeline | Temporal 3-view (Compact/Timeline/History) | Limited debugging | P2 | M | Medium | High | Span-tree component (agent-prism style) | Faster failure diagnosis |
| 11 | **Content pipeline UI** | Catalog entry only | Full studio (queue, draft, publish, metrics) | Content invisible | P2 | M | Medium | High | Create space plugin reading ContentForge JSON | End-to-end content workflow |
| 12 | **Stock/finance dashboard** | Cron visibility only | Live charts, alerts, research (TradingView patterns) | Finance domain missing | P2 | M | Medium | High | Wealth space plugin + StockForge integration | Investment decisions in one place |
| 13 | **Knowledge graph** | Recent files list | Force-directed graph (Obsidian, Eidetic OS) | No visual memory | P2 | L | Medium | High | D3/graph viewer over wiki + Hermes memory | See connections |
| 14 | **API tests + CI** | Portability only | Integration tests + GitHub Actions | Fragile deploys | P2 | M | High | Low | pytest + httpx against FastAPI; CI on push | Confident releases |
| 15 | **Mobile/PWA** | Responsive web | Installable PWA with offline cache | No offline | P3 | M | Low | Medium | next-pwa + service worker for Today cache | Check briefing on phone |
| 16 | **Multi-user** | Single operator | RBAC (Homarr model) | N/A for personal OS | P3 | L | Low | Low | Defer unless sharing with team | — |

---

## Brutal Deletions

| Item | Verdict | Reason |
|------|---------|--------|
| `mission-control-dashboard` repo | **Delete/archive** | Never built; naming collision |
| server.py inline dispatch (~400 lines) | **Delete** | Dead code |
| Browser `prompt()` approval | **Delete** | Replace with modal |
| Separate React-only client (spec repo vision) | **Delete** | Wrong architecture; need full stack |
| Docs as primary nav | **Demote** | Not daily-use |
| 45 modules in v1 | **Defer** | Ship Today + Agents first |

---

## Priority Tiers

### P0 — Must have for V2 launch
1. Postgres + Redis data layer
2. FastAPI gateway (wrap existing APIs)
3. SSE realtime
4. Auth (Tailscale or session)
5. Today briefing surface
6. 9-space navigation + command palette

### P1 — Core differentiators (months 2–3)
7. Nightly automation DAG
8. AI ask-anything
9. Plugin/widget registry
10. Semantic search

### P2 — Domain depth (months 4–6)
11. LLM cost analytics
12. Create / Wealth / Knowledge spaces
13. Advanced workflow viz
14. CI/CD + tests

### P3 — Polish
15. PWA/offline
16. Multi-user RBAC

---

## Workflow Gaps (Daily Lifecycle)

| Time | Current | Target |
|------|---------|--------|
| **Wake** | Manual open MC, scan failures | Today briefing auto-loaded: nightly summary, agenda, alerts |
| **Morning** | Trigger cron manually | Pre-run jobs completed at 2 AM; review recommendations |
| **Work** | Monitor dispatch in ops view | Dispatch + tasks integrated; AI suggests next action |
| **Create** | No UI | Content Studio: ideas → draft → queue → publish |
| **Research** | DeepResearch profile only | Research Lab: saved queries, summaries, knowledge links |
| **Evening** | Check cron output | Insights: productivity score, unfinished tasks, tomorrow prep |
| **Night** | Nothing | Nightly DAG runs: research, index, backup, report |

---

*Next: [04-competitor-benchmark.md](./04-competitor-benchmark.md)*
