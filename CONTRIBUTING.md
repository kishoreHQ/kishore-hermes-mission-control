# Development Discipline

Every change must follow this checklist:

1. Understand the goal.
2. Change only relevant code.
3. Update relevant documentation.
4. Update `CHANGELOG.md` for behavior/setup/API/UI/operations changes.
5. Run syntax checks.
6. Run API smoke checks when service is active.
7. Check git diff.
8. Confirm no secrets/runtime data are staged.
9. Commit with clear message.
10. Push to GitHub.
11. Report commit hash and verification proof.

## Pre-commit checklist

```bash
git status --short
git diff --stat
python3 -m py_compile server.py dispatch_engine.py
node --check static/app.js
git diff --cached --stat
```

## Pre-push checklist

```bash
./scripts/verify_mission_control.sh
git ls-files 'data/*.jsonl' 'logs/*' '*.log' '__pycache__/*' '*.pyc'
```

The tracked runtime/cache file list should be empty.

## Documentation checklist

- Setup change? Update `SETUP.md` and `.env.example` if needed.
- Operational change? Update `OPERATIONS.md`.
- API/data/design change? Update `ARCHITECTURE.md`.
- Security/secret/runtime-data change? Update `SECURITY.md`.
- Any meaningful change? Update `CHANGELOG.md`.
