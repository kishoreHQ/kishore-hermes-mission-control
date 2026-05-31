# Hermes Scheduled Jobs Audit — 2026-05-31

## Summary

- System cron: active. Root/user crontab contains 9 custom jobs: 8 AI Creator jobs and 1 Memory Wiki regeneration job.
- System cron directories: only standard system jobs in `/etc/cron.d`, `/etc/cron.daily`, `/etc/cron.weekly`.
- Systemd timers: 19 timers listed; no failed timer/service units found.
- Mission Control service: active and `/healthz` returns ok.
- Hermes cron scheduler: 14 jobs found.
- Confirmed failing scheduled jobs fixed: 5 Hermes cron jobs.
- Credential-blocked but scheduler-healthy jobs: AI Creator image/approval/posting/crosspost jobs. They exit 0 but report missing/invalid external credentials; not disabled because they are not obsolete and require secrets from owner.

## Fixed failing jobs

### Morning Content Intelligence — `a5a01d4fe703`

- Source: Hermes cron scheduler.
- Previous mode: LLM-agent prompt that ran `/root/.hermes/scripts/morning-intelligence.py`.
- Failure: `RuntimeError: No Codex credentials stored. Run hermes auth/model`.
- Root cause: job depended on the active LLM provider even though the underlying pipeline is deterministic and already writes JSON.
- Fix: created `/root/.hermes/scripts/morning_intelligence_report.py`; updated Hermes cron job to `no_agent=true` script mode.
- Verification: `cronjob run a5a01d4fe703`; output `/root/.hermes/cron/output/a5a01d4fe703/2026-05-31_17-15-13.md`; `last_status=ok`.

### StockPulse Pre-Market — `c52dd586f976`

- Source: Hermes cron scheduler.
- Command: no_agent script `pulse_pre_market.sh`.
- Failure: stale scheduler state showed `error` with `Failed to compute next run for recurring schedule (is the 'croniter' package installed in the gateway's Python env?)`.
- Root cause: stale Hermes scheduler state from earlier croniter environment issue; current gateway venv has croniter and next run computes correctly.
- Fix: manually verified script exit 0, then `cronjob resume c52dd586f976`.
- Verification: `/root/.hermes/scripts/pulse_pre_market.sh` exit 0; `cronjob list` shows `state=scheduled`, `last_status=ok`.

### StockPulse Mid-Day — `daa340ca8867`

- Source: Hermes cron scheduler.
- Command: no_agent script `pulse_mid_day.sh`.
- Failure/root cause: same stale croniter scheduler state.
- Fix: manually verified script exit 0, then `cronjob resume daa340ca8867`.
- Verification: `state=scheduled`, `last_status=ok`.

### StockPulse Pre-Close — `8094bf62527c`

- Source: Hermes cron scheduler.
- Command: no_agent script `pulse_pre_close.sh`.
- Failure/root cause: same stale croniter scheduler state.
- Fix: manually verified script exit 0, then `cronjob resume 8094bf62527c`.
- Verification: `state=scheduled`, `last_status=ok`.

### StockPulse Post-Market — `facefd3b644d`

- Source: Hermes cron scheduler.
- Command: no_agent script `pulse_post_market.sh`.
- Failure/root cause: same stale croniter scheduler state.
- Fix: manually verified script exit 0, then `cronjob resume facefd3b644d`.
- Verification: `state=scheduled`, `last_status=ok`.

## Healthy scheduled jobs verified

### Root/user crontab — AI Creator Pipeline

- `01_prepare_jobs.py`: exit 0; prepares daily jobs.
- `02_generate_images.py`: exit 0 but business output is `image_failed` due to FAL `401 Unauthorized` — credential issue, not scheduler failure.
- `03_generate_video.py`: exit 0; currently no `image_ready` reel jobs.
- `04_assemble_post.py`: exit 0; blocked by upstream `image_failed` statuses.
- `05_approval_card.py`: exit 0; no assembled jobs requiring approval.
- `06_post_to_ig.py`: exit 0; no approved jobs to post.
- `youtube_crosspost.py`: exit 0 but reports YouTube API not configured — credential/setup issue, not scheduler failure.
- `07_analytics.py`: exit 0; writes report and JSON summary.
- `approval_poller.py`: exit 0; cron logs show it runs every 5 minutes.

### Root/user crontab — Memory Wiki

- `/root/memory-wiki/regenerate.sh`: daily regeneration present; `.last-gen.log` and generated index updated on 2026-05-31.

### System cron/systemd timers

- `/etc/cron.d/e2scrub_all`: standard e2fsprogs fallback cron; no failure found.
- `/etc/cron.d/sysstat`: standard sysstat collection; no failure found.
- `/etc/cron.daily/*`: standard system maintenance; no failure found.
- Systemd timers: 19 timers listed; `systemctl --failed` reported 0 failed units.

### Other Hermes cron jobs

- `f7d76bb4005e` Daily Hermes Config Sync — scheduled, last_status ok.
- `3e99f79c09bf` Remind about Model Routing — scheduled, future reminder, not yet run.
- `b49392a4cfc8` StockForge Daily Top 10 Growth Picks — scheduled, last_status ok.
- `42476ae5294c` Career Ops - Daily Full Pipeline — scheduled, last_status ok.
- `9af44079bca9` daily-priority-check — scheduled, last_status ok.
- `415896932120` gbrain-daily-update-check — scheduled, last_status ok.
- `d23ce2a90b5c` nightly-2am-personal-goals-microapp-builder — scheduled, last_status ok.
- `82465a5b6fff` Nightly Micro-System Builder — scheduled, last_status ok.
- `2e675f92b46a` DevSecOps Zero to Hero Daily Practice — scheduled, last_status ok.

## External dependency notes

AI Creator is scheduler-healthy but not business-complete because external credentials are missing/invalid. Required owner-supplied credentials remain:

- FAL API key/account access.
- Kling API key/secret.
- Telegram bot token/chat ID for approval cards.
- Meta/Instagram publishing credentials.
- YouTube API/OAuth credentials for cross-posting.
- Optional Google Sheets analytics ID.

Do not print or commit any of these secrets. Use env vars or protected `config/secrets.yaml`.

## Repeat audit

Run:

```bash
cd /root/mission-control
./scripts/audit_scheduled_jobs.sh
```

Expected success marker:

```text
SCHEDULED_JOBS_AUDIT_OK
```
