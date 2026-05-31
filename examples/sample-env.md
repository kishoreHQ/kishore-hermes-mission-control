# Sample environment

Copy `.env.example` to `.env` and edit locally. Do not commit `.env`.

```dotenv
MISSION_CONTROL_HOST=127.0.0.1
MISSION_CONTROL_PORT=8090
HERMES_HOME=/root/.hermes
MC_MAX_CONCURRENT_DISPATCHES=3
MC_MAX_QUEUED_DISPATCHES=25
MC_MAX_CONCURRENT_WORKFLOWS=2
MC_MAX_WORKFLOW_RUNTIME_SECONDS=3600
MC_MAX_RETRIES_PER_WORKFLOW=6
```

Provider keys and Telegram tokens are intentionally not shown because Mission Control does not read them directly. Configure those through Hermes profiles/secrets/gateway.
