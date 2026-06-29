# 12 — AI Feature Roadmap

---

## Vision

Hermes OS should feel **AI-native** — not a dashboard with an AI chatbot bolted on. AI is woven into search, recommendations, failure analysis, and the morning briefing.

---

## Feature Matrix

| Feature | Phase | Priority | Description |
|---------|-------|----------|-------------|
| Global AI Chat (⌘J) | 4 | P1 | Ask anything about dashboard state |
| Semantic Search | 4 | P1 | Vector search across dispatches, docs, cron output, ideas |
| Today Recommendations | 3–4 | P1 | AI-generated action suggestions on Today |
| Auto-RCA | 4 | P1 | Root cause analysis on failures |
| Morning Report NL Summary | 3 | P1 | Natural language nightly summary |
| Ask Dashboard API | 4 | P1 | `POST /api/v1/ai/ask` with tool use |
| Prompt Library | 5 | P2 | Versioned prompts linked to profiles |
| Predictive Insights | 6+ | P3 | "StockPulse usually fails Mondays" |
| Workflow Suggestions | 6+ | P3 | "Create workflow for this task pattern" |
| Content Recommendations | 5 | P2 | Topic suggestions from research + trends |

---

## AI Service Architecture

```
┌─────────────────────────────────────────┐
│              ai_service                  │
├─────────────────────────────────────────┤
│  ask(query, context)                     │
│  search(query, filters)                  │
│  rca(failure_id)                         │
│  recommend(today_context)                │
│  embed(text) → vector                    │
└──────────────┬──────────────────────────┘
               │
    ┌──────────┼──────────┐
    ▼          ▼          ▼
 Tool       pgvector    Hermes CLI
 Registry   search      (LLM calls)
```

### Tool Registry
AI chat can call tools:

| Tool | Data Source |
|------|-------------|
| `get_today` | today_service |
| `list_dispatches` | dispatch_service |
| `get_cron_status` | legacy_adapter |
| `search_knowledge` | pgvector |
| `get_nightly_report` | nightly_runs |
| `run_dispatch` | dispatch_service (medium-risk gate) |

Uses Hermes CLI or direct provider API for LLM inference.

---

## Semantic Search Pipeline

### Index Sources
| Source | Trigger |
|--------|---------|
| Dispatch prompts + output | On finalize |
| Cron job output logs | Nightly `index_knowledge` job |
| Wiki markdown files | Nightly job |
| ContentForge ideas/posts | On change |
| Nightly artifacts | On job complete |

### Embedding
- Model: `text-embedding-3-small` or local equivalent
- Store: `embeddings` table with pgvector
- Chunk: 512 tokens, 50 overlap

### Search API
```json
POST /api/v1/ai/search
{
  "query": "kubernetes content ideas",
  "filters": { "source_type": ["idea", "doc"] },
  "limit": 10
}
```

---

## Ask Dashboard

```json
POST /api/v1/ai/ask
{
  "message": "What failed last night and why?",
  "conversation_id": "optional-uuid"
}
```

Response includes:
- Natural language answer
- Citations (dispatch IDs, cron job IDs, doc paths)
- Suggested actions (retry, view logs)

### Context Assembly
1. Fetch Today attention items
2. Fetch latest nightly run failures
3. Retrieve top-k semantic search results for query
4. Build system prompt with tool definitions
5. Run agent loop (max 5 tool calls)

---

## Auto-RCA

Triggered on:
- Nightly job failure
- Dispatch `retry_exhausted`
- Cron job `last_status: error`

```json
POST /api/v1/ai/rca
{ "source_type": "dispatch", "source_id": "d-8f2a" }
```

Output:
```json
{
  "summary": "Provider rate limit after 3 retries",
  "failure_reason": "rate_limited",
  "evidence": ["stderr: 429 Too Many Requests"],
  "recommendation": "Retry after 15 minutes or switch profile to fallback",
  "confidence": 0.85
}
```

---

## Recommendations Engine

Runs after nightly pipeline completes.

Inputs:
- Failed/partial jobs
- Empty content queue
- Unfinished tasks
- Agent performance eval
- Calendar (future)

Outputs: 2–5 actionable recommendations on Today.

---

## LLM Cost Analytics (Phase 4)

### Data Collection
- On dispatch finalize: extract tokens from Hermes session if available
- OTel GenAI semantic conventions
- Store in `llm_usage` table: model, input_tokens, output_tokens, cost_usd, profile, workflow_id

### Dashboard (Agents → LLM Analytics)
- Daily spend chart
- Cost per profile
- Cost per workflow
- P95 latency per model
- Budget alert threshold

Inspired by Langfuse `usage_details` / `cost_details`.

---

## Privacy & Safety

- AI features run on same VPS; no data sent to third parties unless configured
- Prompts may contain sensitive data — redact in logs
- `run_dispatch` tool requires medium-risk approval
- Embeddings stored locally in Postgres

---

## Phase Timeline

| Phase | AI Features Shipped |
|-------|---------------------|
| 3 | Morning report NL summary |
| 4 | Ask, search, RCA, recommendations, cost analytics |
| 5 | Prompt library, content recommendations |
| 6+ | Predictive insights, workflow suggestions |

---

*Next: [13-roadmap-and-backlog.md](./13-roadmap-and-backlog.md)*
