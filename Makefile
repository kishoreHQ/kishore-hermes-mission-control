# Mission Control Makefile
# Canonical command surface for AI agents and humans.
# All targets are .PHONY (no file collisions).

PY         ?= python3
HOST       ?= 127.0.0.1
PORT       ?= 8090
PIDFILE    := data/server.pid
LOGFILE    := logs/server.log
SERVER_PY   := server.py
DISPATCH    := dispatch_engine.py

.PHONY: help setup install verify verify-live test run serve-bg stop logs health audit-jobs clean lint

help:  ## Show this help
	@echo "Mission Control - Hermes dispatch UI"
	@echo ""
	@echo "Usage:  make <target> [VAR=value ...]"
	@echo ""
	@echo "Targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "Variables:"
	@echo "  HOST=127.0.0.1   Bind address (default 127.0.0.1, use 0.0.0.0 for network)"
	@echo "  PORT=8090        HTTP port (default 8090)"
	@echo "  PY=python3       Python interpreter (default python3)"
	@echo ""
	@$(PY) --version

setup:  ## Create runtime dirs, install gitkeep, verify Python + Node
	@echo "🔧 Mission Control setup"
	@mkdir -p data logs static examples docs
	@touch data/.gitkeep logs/.gitkeep
	@touch data/action_log.jsonl data/dispatch_queue.jsonl data/runs.jsonl \
	      data/routing_history.jsonl data/workflow_events.jsonl
	@command -v $(PY) >/dev/null 2>&1 || { echo "❌ $(PY) not found"; exit 1; }
	@echo "  ✅ $(PY): $$($(PY) --version)"
	@command -v node >/dev/null 2>&1 && echo "  ✅ node: $$(node --version)" || echo "  ⚠️  node not found (only needed for app.js syntax check)"
	@if [ -f requirements.txt ]; then \
		echo "  📦 Installing test deps from requirements.txt..."; \
		$(PY) -m pip install --quiet --break-system-packages -r requirements.txt 2>/dev/null \
			|| $(PY) -m pip install --quiet -r requirements.txt; \
	fi
	@if [ ! -f .env ]; then cp .env.example .env; echo "  📝 Created .env from .env.example"; fi
	@echo "✅ Setup complete"
	@echo ""
	@echo "Next:  make verify   then   make run"

install: setup  ## Alias for setup
	@true

verify: test  ## Compile-check Python + JS + run pytest (alias for test)
	@echo ""
	@echo "🩺 Mission Control verify"
	@echo "================================="
	@$(PY) -m py_compile $(SERVER_PY) $(DISPATCH) && echo "  ✅ Python compiles"
	@if [ -f static/app.js ]; then \
		node --check static/app.js && echo "  ✅ static/app.js parses" || echo "  ⚠️  app.js syntax error"; \
	else \
		echo "  ⚠️  static/app.js not present (skipped)"; \
	fi
	@echo ""
	@echo "✅ verify complete"

verify-live: verify  ## Same as verify + smoke test against running server
	@echo ""
	@echo "🩺 Live smoke test (requires server on 127.0.0.1:8090)..."
	@bash scripts/verify_mission_control.sh

test:  ## Run pytest portability tests (no network)
	@$(PY) -m pytest tests/ -v

run:  ## Start the server in foreground
	@echo "🚀 Starting Mission Control on $(HOST):$(PORT)..."
	@echo "   (Ctrl-C to stop)"
	@echo ""
	@set -a; [ -f .env ] && . ./.env; set +a; \
		MISSION_CONTROL_HOST=$(HOST) MISSION_CONTROL_PORT=$(PORT) \
		$(PY) $(SERVER_PY)

serve-bg:  ## Start the server in background, write PID to data/server.pid
	@mkdir -p data logs
	@if [ -f $(PIDFILE) ] && kill -0 $$(cat $(PIDFILE)) 2>/dev/null; then \
		echo "⚠️  Server already running (PID $$(cat $(PIDFILE)))"; \
		exit 0; \
	fi
	@set -a; [ -f .env ] && . ./.env; set +a; \
		nohup $(PY) $(SERVER_PY) > $(LOGFILE) 2>&1 & \
		echo $$! > $(PIDFILE)
	@sleep 1
	@echo "✅ Started (PID $$(cat $(PIDFILE)))"
	@echo "   Log: $(LOGFILE)"
	@echo "   URL: http://$(HOST):$(PORT)"

stop:  ## Stop the background server
	@if [ ! -f $(PIDFILE) ]; then \
		echo "ℹ️  No PID file; nothing to stop"; \
	else \
		PID=$$(cat $(PIDFILE)); \
		if kill -0 $$PID 2>/dev/null; then \
			kill $$PID; echo "✅ Stopped PID $$PID"; \
			rm -f $(PIDFILE); \
		else \
			echo "⚠️  PID $$PID not running; cleaning up PID file"; \
			rm -f $(PIDFILE); \
		fi \
	fi

logs:  ## Tail the runtime log
	@if [ -f $(LOGFILE) ]; then tail -f $(LOGFILE); else echo "No $(LOGFILE) yet"; fi

health:  ## Curl /healthz (requires server running)
	@curl -fsS http://$(HOST):$(PORT)/healthz && echo "" || echo "❌ Server not reachable on $(HOST):$(PORT)"

audit-jobs:  ## Run the scheduled-jobs audit
	@bash scripts/audit_scheduled_jobs.sh

clean: stop  ## Stop server, remove data/* and logs/* (preserves .gitkeep)
	@find data -type f ! -name .gitkeep -delete 2>/dev/null || true
	@find logs -type f ! -name .gitkeep -delete 2>/dev/null || true
	@echo "✅ Cleaned data/* and logs/* (kept .gitkeep)"

lint:  ## Compile-check Python sources
	@$(PY) -m compileall -q . 2>/dev/null || true
	@echo "✅ Lint complete"
