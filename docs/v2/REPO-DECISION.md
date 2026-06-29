# Repository Decision — Hermes OS V2

**Date:** June 2026  
**Decision:** Single monorepo in `kishore-hermes-mission-control`

---

## Decision

| Repo | Action |
|------|--------|
| `kishore-hermes-mission-control` | **Primary** — V2 monorepo (`apps/`, `packages/`, `legacy/`) |
| `mission-control-dashboard` | **Archived** — see `ARCHIVED.md`; docs-only spec never built |

## Monorepo Layout

```
kishore-hermes-mission-control/   (rename to hermes-os optional later)
├── apps/
│   ├── web/          Next.js 15 frontend
│   └── api/          FastAPI gateway
├── packages/
│   ├── ui/           shadcn + Calm Command theme
│   ├── types/        Shared TypeScript types
│   └── sdk/          API client
├── legacy/
│   ├── server.py     v1 HTTP server (retire after cutover)
│   └── dispatch_engine.py
├── static/           v1 UI (retire after cutover)
├── docs/v2/          Strategy dossier
├── data/             Runtime state
├── docker-compose.yml
├── turbo.json
└── package.json
```

## Rationale

1. **One source of truth** — orchestration + UI + docs together
2. **dispatch_engine stays Python** — wrap, don't rewrite
3. **Gradual migration** — v1 on :8090, v2 on :3000/:8000 in parallel
4. **No naming collision** — archive the spec repo

## GitHub Actions

- Rename repo to `hermes-os` when ready (optional)
- Archive `mission-control-dashboard` on GitHub
