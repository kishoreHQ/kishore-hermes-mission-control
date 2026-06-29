#!/usr/bin/env bash
# Full local stack via Docker — Postgres + Redis + API + Web
# No Neon, no VPS. Uses sample data/ on your Mac.

set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

pick_port() {
  local start="${1:-3000}"
  local p="$start"
  while lsof -i ":$p" -sTCP:LISTEN >/dev/null 2>&1; do
    p=$((p + 1))
  done
  echo "$p"
}

export WEB_PORT="${WEB_PORT:-$(pick_port 3001)}"
export API_PORT="${API_PORT:-$(pick_port 8000)}"
export POSTGRES_PORT="${POSTGRES_PORT:-$(pick_port 5433)}"
export REDIS_PORT="${REDIS_PORT:-$(pick_port 6380)}"

cmd="${1:-up}"

echo "Hermes OS — Docker local stack"
echo "  web:      http://localhost:${WEB_PORT}/today"
echo "  api:      http://localhost:${API_PORT}/api/v1/docs"
echo "  postgres: localhost:${POSTGRES_PORT} (host) → 5432 (container)"
echo "  redis:    localhost:${REDIS_PORT} (host) → 6379 (container)"
echo ""
if lsof -i :5432 -sTCP:LISTEN >/dev/null 2>&1; then
  echo "Note: port 5432 is in use (e.g. contentforge-db). Hermes uses ${POSTGRES_PORT} instead."
  echo ""
fi

case "$cmd" in
  up)
    docker compose up --build
    ;;
  up-d)
    docker compose up --build -d
    echo ""
    echo "Running in background. Logs: ./scripts/docker-local.sh logs"
    ;;
  down)
    docker compose down
    ;;
  logs)
    docker compose logs -f
    ;;
  db-only)
    docker compose up postgres redis -d
    echo "Postgres + Redis only. Run ./scripts/dev-mac.sh api && ./scripts/dev-mac.sh web"
    ;;
  reset)
    docker compose down -v
    echo "Removed containers and postgres volume."
    ;;
  *)
    echo "Usage: $0 {up|up-d|down|logs|db-only|reset}"
    exit 1
    ;;
esac
