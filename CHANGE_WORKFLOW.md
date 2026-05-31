# Change Workflow

Every code change must include documentation review.

## Required flow

1. Create or identify goal.
2. Inspect current git status.
3. Modify code.
4. Update relevant docs:
   - `README.md` for user-facing behavior/setup overview
   - `SETUP.md` for installation/config changes
   - `OPERATIONS.md` for operational changes
   - `ARCHITECTURE.md` for design/data/API changes
   - `SECURITY.md` for security/auth/secret/runtime-data changes
   - `CHANGELOG.md` for all meaningful behavior changes
   - `examples/` for sample workflow/config changes
5. Run verification.
6. Run secret audit when pushing.
7. Commit.
8. Push.
9. Final report.

## Completion rule

A change is not complete until code, docs, verification, commit, and push are all done.

## Final report must include

- commit hash
- files changed
- verification result
- secret audit result
- push status
- rollback command

## No-runtime-data rule

Never stage or push runtime JSONL files, logs, generated uploads, sessions, cookies, keys, tokens, or `.env` files.
