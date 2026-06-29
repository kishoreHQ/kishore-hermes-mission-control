# VPS Deployment + Tailscale Access

**Hermes OS V2** — deploy on your VPS and access from Mac via Tailscale.

**Recommended: native (no Docker).** Hermes cron and agents stay on systemd; only the V2 dashboard runs as two lightweight services.

---

## Documentation map

| Topic | Location | Covers |
|-------|----------|--------|
| **V2 native VPS (recommended)** | This doc §1 | `vps-native.sh`, systemd, Tailscale |
| **V2 local Mac** | [README-V2.md](../README-V2.md) | `dev-mac.sh` |
| **V2 Docker (optional)** | This doc §8 | `docker-local.sh` |
| **V1 VPS setup (legacy UI, :8090)** | [SETUP.md](../SETUP.md) | `server.py`, systemd |
| **Hermes agent clone/run** | [AGENTS.md](../AGENTS.md) | Hermes self-setup |
| **V2 strategy** | [docs/v2/README.md](./v2/README.md) | Full dossier |

---

## Which dashboard?

| Version | Port | Stack | Status |
|---------|------|-------|--------|
| **V1 legacy** | 8090 | `server.py` + `static/` | Still on VPS today |
| **V2 Hermes OS** | 3001 (web) + 8000 (api) | Native systemd or Docker | New — run alongside V1 |

Run **both in parallel** during migration. Retire V1 when V2 covers your daily workflows.

---

## 1. Native VPS deploy (recommended)

No Docker. ~200 MB disk vs 1–2 GB for Docker. Hermes cron fleet unchanged.

### Prerequisites

```bash
sudo apt-get update
sudo apt-get install -y git python3 python3-venv curl
# Node 20+ (nodesource or nvm — apt nodejs is often too old)
node -v   # must be >= 20
tailscale status
```

### One-time setup

```bash
cd /root
git clone https://github.com/kishoreHQ/kishore-hermes-mission-control.git
cd kishore-hermes-mission-control

# Reuse V1 data if already running at /root/mission-control
HERMES_DATA_DIR=/root/mission-control/data ./scripts/vps-native.sh setup
./scripts/vps-native.sh install-services
```

### Start + Tailscale

```bash
./scripts/vps-native.sh start
./scripts/vps-native.sh tailscale
```

From your Mac (Tailscale on):

```
https://<vps-hostname>/today
```

The web app proxies `/api/v1/*` to the API on localhost — **only port 3001** needs Tailscale Serve.

### Day-2 commands

```bash
./scripts/vps-native.sh status
./scripts/vps-native.sh health
./scripts/vps-native.sh restart
journalctl -u hermes-os-api -n 50 --no-pager
journalctl -u hermes-os-web -n 50 --no-pager
```

### What runs where

| Component | How | Docker? |
|-----------|-----|---------|
| Hermes cron (19 jobs) | Existing systemd/cron | No |
| Hermes CLI / agents | Native `$HERMES_HOME` | No |
| V1 dashboard (:8090) | `mission-control.service` | No |
| V2 API (:8000) | `hermes-os-api.service` | No |
| V2 Web (:3001) | `hermes-os-web.service` | No |

### Environment (`.vps-native.env`)

Written by `setup`. Key values:

```bash
WEB_PORT=3001
API_PORT=8000
HERMES_DATA_DIR=/root/mission-control/data   # or ./data
HERMES_HOME=/root/.hermes
AUTO_CREATE_TABLES=false                     # no Postgres required
NEXT_PUBLIC_API_URL=                         # empty = same-origin proxy
INTERNAL_API_URL=http://127.0.0.1:8000
```

---

## 2. Expose via Tailscale

**Do not** open 3001/8000 on the public internet.

### Tailscale Serve (recommended)

```bash
./scripts/vps-native.sh tailscale
# equivalent: tailscale serve --bg 3001
tailscale serve status
```

### Direct tailnet IP (HTTP)

```
http://100.x.x.x:3001/today
```

API docs (localhost only unless you expose separately):

```
http://127.0.0.1:8000/api/v1/docs   # on VPS
```

### SSH tunnel

```bash
ssh -L 3001:127.0.0.1:3001 root@100.x.x.x
# open http://localhost:3001/today
```

### Firewall

```bash
sudo ufw deny 3001
sudo ufw deny 8000
sudo ufw allow 22
sudo ufw enable
```

Tailscale traffic does not need public firewall holes.

### After reboot

```bash
sudo systemctl start hermes-os-api hermes-os-web
tailscale serve --bg 3001
```

Add to crontab `@reboot` if needed.

---

## 3. Migrate from V1 (port 8090)

### What carries over

| V1 asset | V2 usage |
|----------|----------|
| `data/dispatch_queue.jsonl` | Legacy adapter reads JSONL |
| `data/workflows_multi.json` | Workflows API |
| `data/tasks.json` | Today agenda |
| `data/services.json` | Infrastructure space |
| `workflows.json` | Agent fleet catalog |
| Hermes cron at `$HERMES_HOME/cron/` | Cron API |

### Steps

```bash
# 1. Keep V1 running
systemctl status mission-control.service

# 2. Start V2 native alongside
HERMES_DATA_DIR=/root/mission-control/data ./scripts/vps-native.sh setup
./scripts/vps-native.sh install-services
./scripts/vps-native.sh start

# 3. Compare
curl http://127.0.0.1:8090/api/status | head
curl http://127.0.0.1:8000/api/v1/today

# 4. When ready, retire V1
sudo systemctl stop mission-control.service
sudo systemctl disable mission-control.service
```

### Old `mission-control-dashboard` spec repo

Never built (docs only). Ignore except [TAG_SYSTEM.md](../../mission-control-dashboard/docs/TAG_SYSTEM.md). See [ARCHIVED.md](../../mission-control-dashboard/ARCHIVED.md).

---

## 4. Hermes self-setup (agents)

Hermes agents should run the **native V2 path**:

```bash
git clone https://github.com/kishoreHQ/kishore-hermes-mission-control.git
cd kishore-hermes-mission-control
HERMES_DATA_DIR=/root/mission-control/data ./scripts/vps-native.sh setup
./scripts/vps-native.sh install-services && ./scripts/vps-native.sh start
./scripts/vps-native.sh tailscale
curl -sf http://127.0.0.1:8000/healthz
```

Do **not** containerize Hermes cron or agents. See [AGENTS.md](../AGENTS.md).

---

## 5. Quick reference

| From Mac (Tailscale on) | URL |
|-------------------------|-----|
| V2 Today (Serve) | `https://<vps-hostname>/today` |
| V2 Today (direct IP) | `http://100.x.x.x:3001/today` |
| V1 legacy (until retired) | `http://100.x.x.x:8090` |

---

## 6. Troubleshooting

| Problem | Fix |
|---------|-----|
| Can't reach UI from Mac | `tailscale status` on both; run `./scripts/vps-native.sh tailscale` |
| UI loads, API errors | `journalctl -u hermes-os-api`; check `HERMES_DATA_DIR` |
| Empty dispatch/cron | Point `HERMES_DATA_DIR` at V1 `data/`; set `HERMES_HOME` |
| Node too old | Install Node 20+ via nvm or nodesource |
| Port in use | `WEB_PORT=3002 API_PORT=8001 ./scripts/vps-native.sh setup` |
| Rebuild after git pull | `./scripts/vps-native.sh setup && ./scripts/vps-native.sh restart` |

---

## 7. Optional: Docker deploy

Use Docker only if you need **Postgres + Redis** on the VPS (nightly DAG persistence, pgvector later).

```bash
chmod +x scripts/docker-local.sh
./scripts/docker-local.sh up-d
tailscale serve --bg 3001
```

See [README-V2.md](../README-V2.md) for local Docker details. Disk cost: ~1–2 GB.

---

*For local Mac testing, see [README-V2.md](../README-V2.md).*

---

## 8. Nightly pipeline timer (optional)

Install systemd timer to trigger the DAG at 2 AM:

```bash
sudo cp deploy/hermes-os-nightly.service.example /etc/systemd/system/hermes-os-nightly.service
sudo cp deploy/hermes-os-nightly.timer.example /etc/systemd/system/hermes-os-nightly.timer
sudo systemctl daemon-reload
sudo systemctl enable --now hermes-os-nightly.timer
systemctl list-timers hermes-os-nightly.timer
```

Manual trigger: `curl -X POST http://127.0.0.1:8000/api/v1/nightly/trigger`

---

## 9. Per-phase verification checklist

After `git pull && ./scripts/vps-native.sh setup && ./scripts/vps-native.sh restart`:

| Phase | Verify |
|-------|--------|
| 0 Data | `curl -sf localhost:8000/api/v1/cron \| jq '.items \| length'` ≈ 19 |
| 1 Reads | `curl -sf localhost:8000/api/v1/status?heavy=false \| jq .summary` |
| 2 Today | Open `/today` — status hero + 7 bento tiles + running strip |
| 3 Dispatch | `POST /api/v1/dispatch/enqueue` then watch `/agents/dispatch` |
| 4 Nightly | `POST /api/v1/nightly/trigger`; `/insights` shows cost rows |
| 5 Spaces | `/create`, `/wealth`, `/knowledge`, `/infrastructure` load data |
| 6 Cutover | Compare V1 `:8090` vs V2; stop `mission-control.service` when ready |

