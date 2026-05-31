# Architecture

## Components

### server.py

Python stdlib HTTP server. Responsibilities:

- serve static UI
- expose `/api/*` endpoints
- read/write JSON data files
- perform service health checks
- expose logs and status summaries
- enforce action safety gates
- bridge APIs to `dispatch_engine.py`

### dispatch_engine.py

Execution and reliability engine. Responsibilities:

- dispatch queue persistence
- workflow creation and orchestration
- dependency-aware subtask dispatch
- Hermes CLI command building
- `subprocess.Popen` execution
- stdout/stderr streaming
- PID tracking
- cancellation
- timeout enforcement
- retry and resume logic
- failure classification
- queue/concurrency limits

### static/app.js

Single-page UI controller. It renders dashboards, workflows, dispatch queue, drawer details, actions, logs, and safety controls.

### data directory

Contains safe configuration JSON and local runtime state. Runtime JSONL files are ignored.

### Hermes CLI

Mission Control dispatches real work through Hermes:

```bash
hermes -p <profile> chat -q "<prompt>" --quiet --max-turns=10
```

### systemd service

Keeps Mission Control running and provides logs through journald.

## Dispatch lifecycle

1. Dispatch is enqueued with profile, prompt, timeout, retry policy, and optional workflow/subtask IDs.
2. `dispatch_start()` checks VM-safe concurrency limits.
3. Dispatch becomes `running` with `process_status=starting`.
4. `_start_hermes_dispatch()` creates a monitor record and daemon thread.
5. The monitor starts `subprocess.Popen`.
6. Reader threads stream stdout/stderr to tail fields.
7. Heartbeat updates elapsed seconds and process state.
8. The process exits, is cancelled, or times out.
9. `_finalize_dispatch()` writes terminal state and failure reason.
10. Workflow subtasks sync from dispatch state.

## Workflow lifecycle

1. Workflow is created with subtasks and dependencies.
2. Ready subtasks dispatch up to concurrency limits.
3. A subtask completes, fails, times out, or is cancelled.
4. Dependent subtasks become eligible when dependencies complete or are intentionally skipped by resume-next.
5. Synthesis becomes ready when terminal subtasks are complete.

## Retry lifecycle

1. Dispatch fails.
2. `_classify_failure()` assigns a reason.
3. `_should_retry()` checks retry policy and global workflow retry budget.
4. If retryable, a new attempt starts and the old attempt is recorded.
5. If exhausted, status becomes `retry_exhausted`/failed with failure reason retained.

## Resume lifecycle

Supported resume modes:

- failed step: rerun the failed step with a new dispatch ID
- next step: mark selected failed step as skipped and continue downstream
- selected step: rerun a chosen step

Previous attempts are preserved for auditability.

## Failure classification

Failure reasons include `timeout`, `cancelled`, `command_not_found`, `provider_error`, `rate_limited`, `permission_error`, `empty_output`, `nonzero_exit`, `validation_error`, and `unknown_error`.

## Queue/concurrency control

Default limits:

- `MC_MAX_CONCURRENT_DISPATCHES=3`
- `MC_MAX_QUEUED_DISPATCHES=25`
- `MC_MAX_CONCURRENT_WORKFLOWS=2`
- `MC_MAX_WORKFLOW_RUNTIME_SECONDS=3600`
- `MC_MAX_RETRIES_PER_WORKFLOW=6`

The active dispatch counter counts live PIDs, monitor records, and recent `starting` claims to avoid startup races.

## UI/API relationship

The UI never executes system commands directly. It calls backend APIs. The backend enforces safety, redaction, allowlists, and concurrency rules.

## Data model overview

Dispatch records include `dispatch_id`, `workflow_id`, `subtask_id`, `profile`, `prompt`, `status`, `process_status`, `pid`, `exit_code`, `timeout_seconds`, `retry_count`, `failure_reason`, `stdout_tail`, and `stderr_tail`.

Workflow subtask fields mirror dispatch state for timeline rendering.

## Future extension points

- authenticated reverse proxy
- CI workflow
- richer profile registry
- server-sent event streaming
- Claw3D adapter protocol actions
- branch protection and release tagging
