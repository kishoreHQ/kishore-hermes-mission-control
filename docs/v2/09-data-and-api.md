# 09 — Data Model & API Proposal

---

## Postgres Schema (Core Tables)

### dispatches
```sql
CREATE TABLE dispatches (
  id UUID PRIMARY KEY,
  workflow_id UUID REFERENCES workflows(id),
  subtask_id TEXT,
  profile TEXT NOT NULL,
  prompt TEXT NOT NULL,
  status TEXT NOT NULL,  -- queued, running, completed, failed, cancelled, retry_exhausted
  process_status TEXT,
  pid INTEGER,
  exit_code INTEGER,
  timeout_seconds INTEGER DEFAULT 3600,
  retry_count INTEGER DEFAULT 0,
  failure_reason TEXT,
  stdout_tail TEXT,
  stderr_tail TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_dispatches_status ON dispatches(status);
CREATE INDEX idx_dispatches_workflow ON dispatches(workflow_id);
```

### workflows
```sql
CREATE TABLE workflows (
  id UUID PRIMARY KEY,
  title TEXT NOT NULL,
  status TEXT NOT NULL,
  coordinator_profile TEXT,
  mode TEXT,
  subtasks JSONB NOT NULL DEFAULT '[]',
  dependencies JSONB DEFAULT '[]',
  synthesis TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### tasks
```sql
CREATE TABLE tasks (
  id UUID PRIMARY KEY,
  title TEXT NOT NULL,
  lane TEXT NOT NULL,  -- in_progress, needs_review, scheduled, archived
  assignee_profile TEXT,
  priority TEXT,
  due_date DATE,
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### nightly_runs
```sql
CREATE TABLE nightly_runs (
  id UUID PRIMARY KEY,
  started_at TIMESTAMPTZ NOT NULL,
  finished_at TIMESTAMPTZ,
  status TEXT NOT NULL,  -- running, completed, partial, failed
  jobs_total INTEGER,
  jobs_succeeded INTEGER,
  jobs_failed INTEGER,
  duration_seconds INTEGER,
  report_markdown TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE nightly_jobs (
  id UUID PRIMARY KEY,
  run_id UUID REFERENCES nightly_runs(id),
  job_key TEXT NOT NULL,
  status TEXT NOT NULL,
  started_at TIMESTAMPTZ,
  finished_at TIMESTAMPTZ,
  duration_seconds INTEGER,
  error TEXT,
  artifact_paths JSONB DEFAULT '[]'
);
```

### embeddings (pgvector)
```sql
CREATE EXTENSION IF NOT EXISTS vector;
CREATE TABLE embeddings (
  id UUID PRIMARY KEY,
  source_type TEXT NOT NULL,  -- dispatch, doc, cron_output, idea
  source_id TEXT NOT NULL,
  content TEXT NOT NULL,
  embedding vector(1536),
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX ON embeddings USING ivfflat (embedding vector_cosine_ops);
```

### action_log, routing_history, services, settings
- Migrated from JSONL/JSON with same shapes
- `settings` key-value store for profile_mode, thresholds, user prefs

---

## API Versioning

Base path: `/api/v1`

OpenAPI spec at `/api/v1/openapi.json`

---

## Endpoint Map (V2)

### Today
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/today` | Aggregated briefing payload |
| GET | `/api/v1/today/attention` | Needs-attention items |
| GET | `/api/v1/today/agenda` | Tasks due today |

### Agents & Dispatch (ported from v1)
| Method | Path | v1 Equivalent |
|--------|------|---------------|
| GET | `/api/v1/dispatch` | `/api/dispatch` |
| GET | `/api/v1/dispatch/active` | `/api/dispatch/active` |
| GET | `/api/v1/dispatch/{id}` | `/api/dispatch/{id}` |
| GET | `/api/v1/dispatch/{id}/live` | `/api/dispatch/{id}/live` |
| POST | `/api/v1/dispatch/enqueue` | `/api/dispatch/enqueue` |
| POST | `/api/v1/dispatch/{id}/cancel` | `/api/dispatch/{id}/cancel` |
| GET | `/api/v1/workflows` | `/api/workflows` |
| POST | `/api/v1/workflows/create` | `/api/workflows/create` |
| GET | `/api/v1/profiles` | `/api/profiles` |
| GET | `/api/v1/cron` | from `/api/status` scheduled_tasks |

### Infrastructure
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/services` | Service registry + health |
| GET | `/api/v1/logs` | journalctl wrapper |
| GET | `/api/v1/health` | System health summary |

### Nightly
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/nightly/runs` | Run history |
| GET | `/api/v1/nightly/runs/latest` | Latest run + jobs |
| POST | `/api/v1/nightly/trigger` | Manual trigger (medium-risk) |
| GET | `/api/v1/nightly/artifacts/{id}` | Download artifact |

### AI
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/ai/ask` | Ask dashboard anything |
| POST | `/api/v1/ai/search` | Semantic search |
| POST | `/api/v1/ai/rca` | Root cause analysis for failure |
| GET | `/api/v1/ai/recommendations` | Today recommendations |

### Stream
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/stream/events` | SSE: dispatch, nightly, alerts |

### Actions (safety-gated)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/actions/prepare` | Get approval code |
| POST | `/api/v1/actions/execute` | Execute with code |

---

## Today API Response Shape

```json
{
  "greeting": "Good morning, Kishore.",
  "date": "2026-06-29",
  "attention_count": 3,
  "metrics": {
    "nightly": { "status": "partial", "succeeded": 12, "total": 14 },
    "agents_active": 2,
    "content_queued": 3,
    "stocks": { "symbol": "NIFTY", "change": "+0.4%" }
  },
  "attention": [
    { "id": "a1", "severity": "error", "title": "StockPulse failed", "actions": ["logs", "retry"] }
  ],
  "agenda": [
    { "id": "t1", "title": "Review stock picks", "done": false }
  ],
  "nightly_report": {
    "summary": "4 AI tools researched. Learning roadmap updated.",
    "artifacts": ["morning-report.md"]
  },
  "recommendations": [
    { "id": "r1", "text": "Content queue empty — run ContentForge idea generator" }
  ],
  "quick_actions": ["dispatch", "run_cron", "capture", "summary"]
}
```

---

## JSONL Importer

Script: `apps/api/scripts/import_jsonl.py`

| Source | Target Table |
|--------|--------------|
| `dispatch_queue.jsonl` | `dispatches` |
| `runs.jsonl` | `runs` (new table) |
| `workflow_events.jsonl` | `workflow_events` |
| `action_log.jsonl` | `action_log` |
| `tasks.json` | `tasks` |
| `nightly_builds.json` | `nightly_runs` (manual builds) |

Idempotent: upsert by original ID field.

---

## Caching Strategy

| Data | Cache | TTL |
|------|-------|-----|
| Today briefing | Redis | 60s |
| Service health | Redis | 30s |
| Cron list | Redis | 30s |
| Dispatch active | Redis pub/sub | realtime |
| Static config | In-memory | 5m |

---

*Next: [10-state-and-realtime.md](./10-state-and-realtime.md)*
