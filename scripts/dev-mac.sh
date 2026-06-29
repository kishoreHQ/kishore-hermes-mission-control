#!/usr/bin/env bash
# Local Mac demo — no VPS, no Hermes CLI, no Postgres required.
# Uses committed sample data in data/ (services.json, workflows.json, etc.)

set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

export HERMES_DATA_DIR="$ROOT/data"
export AUTO_CREATE_TABLES=false

pick_port() {
  local start="${1:-3000}"
  local p="$start"
  while lsof -i ":$p" -sTCP:LISTEN >/dev/null 2>&1; do
    p=$((p + 1))
  done
  echo "$p"
}

WEB_PORT="${WEB_PORT:-$(pick_port 3000)}"
API_PORT="${API_PORT:-$(pick_port 8000)}"
PORTS_FILE="$ROOT/.dev-local.env"

if [[ "${1:-}" == "api" ]]; then
  cat > "$PORTS_FILE" <<EOF
API_PORT=$API_PORT
WEB_PORT=$WEB_PORT
NEXT_PUBLIC_API_URL=http://localhost:${API_PORT}
EOF
fi

if [[ -f "$PORTS_FILE" ]]; then
  # shellcheck source=/dev/null
  source "$PORTS_FILE"
fi

export NEXT_PUBLIC_API_URL="${NEXT_PUBLIC_API_URL:-http://localhost:${API_PORT}}"

echo "Hermes OS — local UI demo"
echo "  data:  $HERMES_DATA_DIR"
echo "  web:   http://localhost:${WEB_PORT}/today"
echo "  api:   http://localhost:${API_PORT}/api/v1/docs"
echo ""
echo "No Hermes VPS data required. Empty dispatch/cron is normal."
echo ""

if [[ "${1:-}" == "api" ]]; then
  cd apps/api
  VENV="$PWD/.venv"
  if [[ ! -d "$VENV" ]]; then
    echo "Creating API venv at $VENV ..."
    python3 -m venv "$VENV"
  fi
  # shellcheck source=/dev/null
  source "$VENV/bin/activate"
  python -m pip install -q -U pip
  python -m pip install -q -r requirements.txt
  exec env PYTHONPATH=. AUTO_CREATE_TABLES=false python -m uvicorn app.main:app --reload --port "$API_PORT"
fi

if [[ "${1:-}" == "web" ]]; then
  npm install
  exec npm run dev --workspace=@hermes/web -- --port "$WEB_PORT"
fi

echo "Usage:"
echo "  Terminal 1:  ./scripts/dev-mac.sh api"
echo "  Terminal 2:  ./scripts/dev-mac.sh web"
echo ""
echo "Override ports: WEB_PORT=3001 API_PORT=8001 ./scripts/dev-mac.sh web"
echo "Then open the web URL printed above"
