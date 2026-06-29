# 08 — Target Architecture

---

## Overview

Hermes OS V2 uses a **hybrid stack**: Next.js frontend, FastAPI gateway, reused Python dispatch engine, Postgres + Redis data plane.

```
┌─────────────────────────────────────────────────────────────┐
│                    Turborepo Monorepo                        │
├─────────────────────────────────────────────────────────────┤
│  apps/web          Next.js 15 App Router + TypeScript        │
│  apps/api          FastAPI gateway + services                │
│  packages/ui       shadcn components + Calm Command theme    │
│  packages/types    Shared TypeScript types (OpenAPI gen)     │
│  packages/sdk      API client for web                        │
│  legacy/           server.py, dispatch_engine.py (wrapped)   │
└─────────────────────────────────────────────────────────────┘
```

---

## Service Layers

### 1. Presentation (apps/web)
- Next.js App Router, RSC where appropriate
- TanStack Query for server state
- Zustand for UI state (drawer, palette, sidebar)
- SSE client via `EventSource` for realtime
- Tailwind + shadcn from `packages/ui`

### 2. API Gateway (apps/api)
- FastAPI with Pydantic v2 models
- OpenAPI 3.1 spec auto-generated
- Middleware: CORS, auth, request ID, logging
- Route modules: `today`, `agents`, `dispatch`, `workflows`, `infra`, `ai`, `stream`
- Wraps `legacy/dispatch_engine.py` via import path

### 3. Core Services (apps/api/services/)

| Service | Responsibility |
|---------|----------------|
| `dispatch_service` | Thin wrapper over dispatch_engine |
| `workflow_service` | Workflow CRUD + orchestration |
| `scheduler_service` | Nightly DAG execution |
| `ai_service` | Ask-anything, embeddings, RCA |
| `today_service` | Aggregates briefing data |
| `legacy_adapter` | Proxies to v1 JSON/file reads during migration |

### 4. Data Plane

| Store | Use |
|-------|-----|
| **Postgres** | Primary state: dispatches, workflows, tasks, nightly runs, settings |
| **pgvector** | Embeddings for semantic search |
| **Redis** | Job queue, pub/sub for SSE, session cache |
| **Object storage** | Nightly artifacts, uploads (local `/data/artifacts` or S3) |
| **JSONL (legacy)** | Fallback during migration; read-only after cutover |

---

## Monorepo Structure

```
hermes-os/
├── apps/
│   ├── web/
│   │   ├── app/
│   │   │   ├── (spaces)/
│   │   │   │   ├── today/
│   │   │   │   ├── agents/
│   │   │   │   ├── create/
│   │   │   │   ├── knowledge/
│   │   │   │   ├── wealth/
│   │   │   │   ├── life/
│   │   │   │   ├── infrastructure/
│   │   │   │   ├── insights/
│   │   │   │   └── system/
│   │   │   ├── layout.tsx
│   │   │   └── api/          # Next.js API routes (BFF optional)
│   │   ├── components/
│   │   └── package.json
│   └── api/
│       ├── app/
│       │   ├── main.py
│       │   ├── routers/
│       │   ├── services/
│       │   ├── models/
│       │   └── db/
│       ├── alembic/
│       ├── scripts/import_jsonl.py
│       └── requirements.txt
├── packages/
│   ├── ui/
│   ├── types/
│   └── sdk/
├── legacy/
│   ├── server.py              # v1 reference; gradual retirement
│   └── dispatch_engine.py     # imported by apps/api
├── data/                      # runtime + config
├── docker-compose.yml
├── turbo.json
└── package.json
```

---

## Deployment Topology

### Development
```yaml
# docker-compose.yml
services:
  postgres:
    image: pgvector/pgvector:pg16
  redis:
    image: redis:7-alpine
  api:
    build: ./apps/api
    ports: ["8000:8000"]
  web:
    build: ./apps/web
    ports: ["3000:3000"]
```

### Production (VPS)
- systemd: `hermes-os-api.service`, `hermes-os-web.service`
- Tailscale-only access (no public ports)
- Legacy v1 on :8090 during migration; cutover to :3000/:8000
- Hermes CLI on same host

---

## Security Architecture

| Layer | Mechanism |
|-------|-----------|
| Network | Tailscale VPN; bind localhost |
| Auth | Session cookie or Tailscale identity headers |
| API | Bearer token for service-to-service |
| Actions | Preserve safe/medium/high tiers; modal approval |
| Secrets | Env vars + `.env`; never in repo |
| Process | Non-root user in production systemd |

---

## Migration Strategy

### Phase A: Parallel Run
- v1 on :8090, v2 on :3000
- FastAPI proxies read same JSONL files
- JSONL→Postgres importer runs nightly

### Phase B: Write Cutover
- New writes go to Postgres
- dispatch_engine reads/writes via adapter

### Phase C: v1 Retirement
- Remove server.py HTTP server
- Keep dispatch_engine as library only

---

## Extension Points

| Extension | Mechanism |
|-----------|-----------|
| Domain plugins | `packages/plugin-*` + manifest JSON |
| Today widgets | Widget registry in System space |
| Data sources | Adapter interface (local, SSH, API) |
| AI tools | Tool registry in ai_service |
| Nightly jobs | Declarative DAG YAML |

---

## Observability

- Structured JSON logging (request_id, user, route, duration)
- OpenTelemetry traces (optional Phase 6)
- Health: `GET /healthz`, `GET /readyz` (DB + Redis check)
- Metrics endpoint for Prometheus (Phase 6)

---

*Next: [09-data-and-api.md](./09-data-and-api.md)*
