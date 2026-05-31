#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

python3 -m py_compile server.py dispatch_engine.py
node --check static/app.js

if ! curl -fsS http://127.0.0.1:8090/healthz >/dev/null; then
  echo "Mission Control API smoke checks require the service to be running on 127.0.0.1:8090" >&2
  exit 2
fi

curl -fsS http://127.0.0.1:8090/api/status >/dev/null
curl -fsS http://127.0.0.1:8090/api/reliability/limits >/dev/null

echo "VERIFY_OK"
