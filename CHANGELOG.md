# Changelog

Every future commit that changes behavior, setup, API, UI, workflow, config, or operations must update this changelog.

## Unreleased

- Phase 5 UI revamp: widened the static UI into fluid grids, tightened card density, improved empty/log states, and preserved the mobile bottom-bar breakpoint.
- Phase 4 UI revamp: added colored workflow/dispatch timeline markers, prioritized pending/running workflow steps, collapsed dispatch stdout/stderr by default, and moved live dispatch detail into the drawer.
- Phase 3 UI revamp: added a home cockpit hero verdict, bento metrics, service issue signal, and de-duplicated Needs Attention cards with a Show test data toggle.
- Phase 2 UI revamp: retuned the static design system with clearer elevation, quieter chrome, tabular numerals, and warning/error badge glyphs.
- Phase 1 UI revamp: fixed the command palette so it is hidden by default and opens/closes with its backdrop.
- Phase 1 UI revamp: made sidebar active state rely on `navTo()` instead of static initial markup.
- Added scheduled-jobs audit runbook and `scripts/audit_scheduled_jobs.sh`.
- Documented 2026-05-31 cron/systemd/Hermes scheduler audit in `docs/scheduled_jobs_audit_2026-05-31.md`.
- Fixed Morning Content Intelligence Hermes cron by converting it to no-agent script mode.
- Cleared stale StockPulse Hermes cron error states after manual script verification.
- Documented GitHub publishing, setup, operations, architecture, security, examples, verification, and permanent change discipline.
- Added `.env.example` with only variables used by current code.
- Added `.gitignore` protection for runtime data, caches, secrets, logs, and generated uploads.
- Removed tracked runtime JSONL files and generated uploads from source control.

## da163fd - Workflow reliability hardening

- Added retry success/exhausted behavior.
- Added per-step timeout.
- Added cancel handling.
- Added resume from failed step.
- Added resume from next step.
- Added queue/concurrency limit.
- Added timeline API.
- Fixed queue limit startup race.
- Verified real Hermes CLI dispatch.
- Verified orphan checks.

## 18b4886 - Popen streaming dispatch runner

- Replaced blocking dispatch with `subprocess.Popen`.
- Added PID tracking.
- Added stdout/stderr streaming.
- Added timeout kill.
- Added real cancel.
- Added UI process fields.
