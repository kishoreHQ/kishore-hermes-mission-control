#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

python3 -m py_compile server.py dispatch_engine.py
node --check static/app.js

if curl -fsS http://127.0.0.1:8000/healthz >/dev/null 2>&1; then
  curl -fsS "http://127.0.0.1:8000/api/v1/status?heavy=false" >/dev/null
  curl -fsS http://127.0.0.1:8000/api/v1/today >/dev/null
elif curl -fsS http://127.0.0.1:8090/healthz >/dev/null 2>&1; then
  echo "WARNING: V1 still running on :8090 — run ./scripts/retire-v1.sh" >&2
  curl -fsS http://127.0.0.1:8090/api/status >/dev/null
else
  echo "Compile checks OK (no live API on :8000 or :8090)"
fi

echo "VERIFY_OK"
