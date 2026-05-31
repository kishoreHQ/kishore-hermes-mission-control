# Operations Runbook

## Health checks

```bash
systemctl status mission-control.service
curl http://127.0.0.1:8090/healthz
curl http://127.0.0.1:8090/api/status
curl http://127.0.0.1:8090/api/reliability/limits
```

## Restart service

```bash
sudo systemctl restart mission-control.service
systemctl status mission-control.service
curl http://127.0.0.1:8090/healthz
```

## View logs

```bash
journalctl -u mission-control.service -n 100 --no-pager
journalctl -u mission-control.service -f
```

## Check dispatch state

```bash
curl http://127.0.0.1:8090/api/dispatch
```

In the UI, open Dispatch and inspect status, PID, stdout tail, stderr tail, failure reason, and process status.

## Check workflow state

```bash
curl http://127.0.0.1:8090/api/workflows
curl http://127.0.0.1:8090/api/workflows/<workflow_id>/timeline
```

## Check queue limits

```bash
curl http://127.0.0.1:8090/api/reliability/limits
```

Watch `active_dispatches`, `queued_dispatches`, and `active_workflows`.

## Cancel dispatch

```bash
curl -X POST http://127.0.0.1:8090/api/dispatch/<dispatch_id>/cancel
```

## Inspect stdout/stderr

Use the Dispatch UI or workflow timeline drawer. The API records `last_output_chunk`, `last_error_chunk`, `stdout_tail`, `stderr_tail`, `exit_code`, and `failure_reason`.

## Run verification

```bash
./scripts/verify_mission_control.sh
```

Manual verification:

```bash
python3 -m py_compile server.py dispatch_engine.py
node --check static/app.js
curl -fsS http://127.0.0.1:8090/healthz
curl -fsS http://127.0.0.1:8090/api/status
curl -fsS http://127.0.0.1:8090/api/reliability/limits
```

## Rollback to previous commit

```bash
cd /root/mission-control
git log --oneline -5
git reset --hard <commit>
sudo systemctl restart mission-control.service
curl http://127.0.0.1:8090/healthz
```

Known stable rollback points:

```bash
git reset --hard da163fd
# or
git reset --hard 18b4886
```

## Backup and restore

Back up code through GitHub. Runtime JSONL data is local operational state and is not committed.

Manual runtime backup if needed:

```bash
tar -czf mission-control-runtime-$(date +%F).tgz data/*.jsonl data/*.json 2>/dev/null || true
```

Restore by copying the archive back to `data/` and restarting the service.

## Change discipline

Before any change is complete: update code, update docs/changelog, run verification, run secret audit before push, commit, push, and report commit hash plus verification proof.
