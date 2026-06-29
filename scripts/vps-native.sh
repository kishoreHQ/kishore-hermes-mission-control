#!/usr/bin/env bash
# Native VPS deploy — no Docker. Hermes cron stays on systemd; V2 runs as two services.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

WEB_PORT="${WEB_PORT:-3001}"
API_PORT="${API_PORT:-8000}"
if [[ -d /root/mission-control/data ]]; then
  HERMES_DATA_DIR="${HERMES_DATA_DIR:-/root/mission-control/data}"
else
  HERMES_DATA_DIR="${HERMES_DATA_DIR:-$ROOT/data}"
fi
HERMES_HOME="${HERMES_HOME:-${HOME}/.hermes}"
ENV_FILE="$ROOT/.vps-native.env"

write_env() {
  cat > "$ENV_FILE" <<EOF
WEB_PORT=$WEB_PORT
API_PORT=$API_PORT
HERMES_DATA_DIR=$HERMES_DATA_DIR
HERMES_HOME=$HERMES_HOME
AUTO_CREATE_TABLES=false
INTERNAL_API_URL=http://127.0.0.1:${API_PORT}
NEXT_PUBLIC_API_URL=
EOF
  echo "Wrote $ENV_FILE"
}

require_linux() {
  if [[ "$(uname -s)" != "Linux" ]]; then
    echo "vps-native.sh is for Linux VPS. On Mac use: ./scripts/dev-mac.sh"
    exit 1
  fi
}

require_node() {
  if ! command -v node >/dev/null 2>&1; then
    echo "Node.js required (>= 20). Install via nvm or nodesource."
    exit 1
  fi
  local major
  major="$(node -p "process.versions.node.split('.')[0]")"
  if [[ "$major" -lt 20 ]]; then
    echo "Node >= 20 required (found $(node -v))"
    exit 1
  fi
}

setup_api_venv() {
  cd "$ROOT/apps/api"
  if ! python3 -m venv --help >/dev/null 2>&1; then
    echo "Installing python3-venv..."
    sudo apt-get update -qq
    sudo DEBIAN_FRONTEND=noninteractive apt-get install -y python3-venv
  fi
  if [[ ! -d .venv ]]; then
    echo "Creating API venv..."
    python3 -m venv .venv
  fi
  # shellcheck source=/dev/null
  source .venv/bin/activate
  python -m pip install -q -U pip
  python -m pip install -q -r requirements.txt
}

setup() {
  require_linux
  require_node
  write_env

  mkdir -p "$HERMES_DATA_DIR" logs
  touch "$HERMES_DATA_DIR/action_log.jsonl" \
        "$HERMES_DATA_DIR/dispatch_queue.jsonl" \
        "$HERMES_DATA_DIR/runs.jsonl" 2>/dev/null || true

  setup_api_venv

  echo "Installing npm dependencies..."
  npm ci 2>/dev/null || npm install

  echo "Building web (same-origin API proxy for Tailscale)..."
  # shellcheck source=/dev/null
  source "$ENV_FILE"
  export INTERNAL_API_URL NEXT_PUBLIC_API_URL
  npm run build --workspace=@hermes/web

  echo ""
  echo "Setup complete. Next:"
  echo "  ./scripts/vps-native.sh install-services"
  echo "  ./scripts/vps-native.sh start"
  echo "  ./scripts/vps-native.sh tailscale"
}

install_services() {
  require_linux
  write_env

  for unit in hermes-os-api hermes-os-web; do
  sudo sed \
    -e "s|REPO_ROOT|$ROOT|g" \
    -e "s|WEB_PORT|$WEB_PORT|g" \
    -e "s|API_PORT|$API_PORT|g" \
    "$ROOT/deploy/${unit}.service.example" \
    | sudo tee "/etc/systemd/system/${unit}.service" >/dev/null
  done

  sudo systemctl daemon-reload
  sudo systemctl enable hermes-os-api.service hermes-os-web.service
  echo "Installed systemd units: hermes-os-api, hermes-os-web"
}

start() {
  sudo systemctl start hermes-os-api.service hermes-os-web.service
  health
}

stop() {
  sudo systemctl stop hermes-os-web.service hermes-os-api.service
}

restart() {
  sudo systemctl restart hermes-os-api.service hermes-os-web.service
  health
}

status() {
  systemctl status hermes-os-api.service hermes-os-web.service --no-pager || true
}

health() {
  if [[ -f "$ENV_FILE" ]]; then
    # shellcheck source=/dev/null
    source "$ENV_FILE"
  fi
  echo "API:  $(curl -sf "http://127.0.0.1:${API_PORT}/healthz" || echo FAIL)"
  echo "Web:  HTTP $(curl -sf -o /dev/null -w '%{http_code}' "http://127.0.0.1:${WEB_PORT}/today" || echo FAIL)"
  echo ""
  echo "Local:  http://127.0.0.1:${WEB_PORT}/today"
  echo "Tailscale: run ./scripts/vps-native.sh tailscale"
}

tailscale_serve() {
  if ! command -v tailscale >/dev/null 2>&1; then
    echo "tailscale not found"
    exit 1
  fi
  tailscale serve --bg "$WEB_PORT"
  echo ""
  tailscale serve status
  echo ""
  echo "Open from Mac: https://$(tailscale status --json 2>/dev/null | head -1 || hostname)/"
  echo "API is proxied through Next.js — only port ${WEB_PORT} needs Serve."
}

cmd="${1:-}"

case "$cmd" in
  setup) setup ;;
  install-services) install_services ;;
  start) start ;;
  stop) stop ;;
  restart) restart ;;
  status) status ;;
  health) health ;;
  tailscale) tailscale_serve ;;
  *)
    echo "Hermes OS V2 — native VPS (no Docker)"
    echo ""
    echo "Usage: $0 {setup|install-services|start|stop|restart|status|health|tailscale}"
    echo ""
    echo "  setup             Install deps, build web, write .vps-native.env"
    echo "  install-services  Install systemd units (run after setup)"
    echo "  start|stop|restart"
    echo "  health            Curl API + web"
    echo "  tailscale         tailscale serve --bg $WEB_PORT"
    echo ""
    echo "Env overrides: WEB_PORT API_PORT HERMES_DATA_DIR HERMES_HOME"
    echo "Reuse V1 data: HERMES_DATA_DIR=/root/mission-control/data $0 setup"
    exit 1
    ;;
esac
