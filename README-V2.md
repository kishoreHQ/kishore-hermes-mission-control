# Hermes OS V2

See [docs/v2/README.md](docs/v2/README.md) for the full strategy dossier.

**VPS + Tailscale deployment:** [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) — **native (no Docker) recommended**

**Product spec (PRD):** [docs/PRD_V2.md](docs/PRD_V2.md)

## Quick start — pick one

| Mode | Best for | Postgres |
|------|----------|----------|
| **[Native VPS](#native-vps-recommended)** | Production on your VM | No |
| **[Docker full stack](#docker-local)** | Local prod-like testing | Yes (in Docker) |
| **[dev-mac.sh](#lightweight-mac-demo)** | Fast UI iteration on Mac | No |
| **Hybrid** | DB in Docker, app on host | `docker-local.sh db-only` |

---

## Native VPS (recommended)

No Docker. Hermes cron stays native; V2 runs as two systemd services.

```bash
# On your VPS
HERMES_DATA_DIR=/root/mission-control/data ./scripts/vps-native.sh setup
./scripts/vps-native.sh install-services
./scripts/vps-native.sh start
./scripts/vps-native.sh tailscale
```

- **Web:** `https://<vps-hostname>/today` (via Tailscale Serve)
- **API:** proxied through Next.js on same origin (no second port to expose)

Full guide: [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)

---

## Docker local

Uses **local Postgres + Redis in Docker**. No Neon, no VPS.

```bash
chmod +x scripts/docker-local.sh

# Build and run (foreground — see logs)
./scripts/docker-local.sh up

# Or background
./scripts/docker-local.sh up-d
```

- **Web:** http://localhost:3001/today (port 3001 avoids conflict with other Docker apps on 3000)
- **API:** http://localhost:8000/api/v1/docs

Other commands:

```bash
./scripts/docker-local.sh logs    # follow logs
./scripts/docker-local.sh down    # stop
./scripts/docker-local.sh reset   # stop + wipe DB volume
```

Override ports if needed:

```bash
WEB_PORT=3002 API_PORT=8001 ./scripts/docker-local.sh up
```

---

## Lightweight Mac demo

No Docker, no Postgres — reads sample JSON from `data/`.

```bash
chmod +x scripts/dev-mac.sh

# Terminal 1
./scripts/dev-mac.sh api

# Terminal 2
./scripts/dev-mac.sh web
```

Uses `apps/api/.venv` and auto-picks free ports if 3000/8000 are busy.

---

## Hybrid: Docker DB + native app

```bash
./scripts/docker-local.sh db-only
./scripts/dev-mac.sh api
./scripts/dev-mac.sh web
```

Set in `apps/api/.env`:

```bash
DATABASE_URL=postgresql://hermes:hermes@localhost:5432/hermes_os
AUTO_CREATE_TABLES=true
```

---

## Neon vs local (cost note)

**Decision for now: local Docker only.**

If you later use **Neon Launch** ($0.106/CU-hour):

| Scenario | ~Compute/month | Notes |
|----------|----------------|-------|
| **24/7 always-on** (1 CU) | **~$77** | 730 hrs × $0.106 |
| **Personal use** (scale-to-zero, ~2 hrs active/day) | **~$6–15** | API + nightly hits wake DB |
| **Free plan** | $0 | **100 compute hrs/mo** — not 24/7 (~4 days continuous max) |

Storage is cheap (~$0.35/GB-month). For a personal OS, **local Docker Postgres costs $0** and has no compute-hour limits.

---

## Monorepo

| Path | Purpose |
|------|---------|
| `apps/web` | Next.js 15 frontend |
| `apps/api` | FastAPI gateway |
| `packages/ui` | Calm Command design system |
| `packages/sdk` | API client |
| `legacy/` | v1 server.py + dispatch_engine.py |
| `docs/v2/` | Strategy dossier |
| `docs/DEPLOYMENT.md` | Native VPS + Tailscale (Docker optional) |
| `scripts/vps-native.sh` | VPS setup without Docker |
