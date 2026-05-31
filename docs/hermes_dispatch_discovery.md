# Hermes Dispatch Discovery

Date: 2026-05-31

## Summary

Mission Control can dispatch tasks to real Hermes profiles via the CLI using profile aliases or the `-p` flag. Each profile runs as an independent session with its own SOUL.md, skills, and gateway context.

## Available Dispatch Methods

### Option 1: CLI Profile Dispatch (✅ CONFIRMED — Recommended)

```bash
hermes -p <profile_name> chat -q "<prompt>" --quiet [--max-turns N] [-t TOOLSETS]
```

**Verified with all profiles:**
- `hermes -p coder chat -q "..." --quiet` ✅
- `hermes -p contentcreator chat -q "..." --quiet` ✅
- `hermes -p deepresearch chat -q "..." --quiet` ✅
- `hermes -p marketanalyst chat -q "..." --quiet` ✅
- `hermes -p default chat -q "..." --quiet` ✅

**Output format:**
```
session_id: 20260531_073617_e34d2b
<response>
```

**Key features:**
- Uses profile without switching global default
- Non-interactive (`-q` + `--quiet`)
- Returns `session_id` for tracking
- Can limit turns with `--max-turns`
- Can enable toolsets with `-t terminal,web,file`
- Capturable stdout response
- Runs subprocess with timeout support

**Profile aliases (also work):**
```bash
/root/.local/bin/coder chat -q "..." --quiet
/root/.local/bin/contentcreator chat -q "..." --quiet
```
These are shell scripts wrapping `hermes -p <profile> "$@"`

### Option 2: Profile Gateway (Partially Viable)

Each profile has its own gateway but only `default` is running. Starting profile gateways would allow independent Telegram-based dispatch per profile.

```bash
hermes -p coder gateway start  # Start coder's gateway
hermes send --to telegram --profile coder  # Not yet tested
```

**Limitation:** Multiple gateways would compete for the same Telegram bot token unless separate tokens are configured per profile.

### Option 3: Hermes WebUI API (❌ Not Viable)

The WebUI on `:8787` is read-only. No session creation, no profile dispatch, no prompt execution endpoints.

### Option 4: Hermes Dashboard API (❌ Not Viable)

The dashboard on `:9119` is primarily read-only status. No execution endpoints.

### Option 5: Manual/Telegram Fallback (⚠️ Fallback Only)

The current implementation sends prompts to Telegram. This is preserved as fallback when CLI dispatch fails.

## Profiles Available

| Profile          | Alias               | SOUL.md | Skills | Gateway |
|------------------|---------------------|---------|--------|---------|
| default          | (none)              | N/A     | 131+   | running |
| coder            | /root/.local/bin/coder | ✅     | 224    | stopped |
| contentcreator   | /root/.local/bin/contentcreator | ✅ | 224  | stopped |
| deepresearch     | /root/.local/bin/deepresearch | ✅   | 224    | stopped |
| marketanalyst    | /root/.local/bin/marketanalyst | ✅ | 224    | stopped |

## CLI Options for Dispatch

| Flag | Purpose | Recommended |
|------|---------|-------------|
| `-q "prompt"` | Single non-interactive query | ✅ Always |
| `--quiet` | Suppress banner, spinner | ✅ Always |
| `--max-turns N` | Limit agent turns | ✅ Set to 5-10 |
| `-t toolsets` | Enable specific tools | ✅ Task-dependent |
| `-s skills` | Preload skills | Optional |
| `-m model` | Override model | Optional |

## Can We...

| Capability | Status | Method |
|-----------|--------|--------|
| Select profile at launch | ✅ Yes | `-p <profile>` |
| Run non-interactively | ✅ Yes | `-q --quiet` |
| Capture output | ✅ Yes | stdout pipe |
| Get session ID | ✅ Yes | First line of output |
| Stream logs | ⚠️ Partial | Poll journalctl or state.db |
| Cancel running task | ✅ Yes | SIGTERM on subprocess |
| Select toolsets | ✅ Yes | `-t terminal,web,file` |
| Limit turns | ✅ Yes | `--max-turns` |
| Set timeout | ✅ Yes | `subprocess timeout=` |
| Run parallel profiles | ✅ Yes | Separate subprocesses |
| Get run status | ⚠️ Partial | Session in state.db |
| Pass context/files | ✅ Yes | Include in prompt |

## Limitations

1. **No live output streaming**: `hermes chat -q` returns output only on completion
2. **No programmatic status query**: Can't poll a running session's progress
3. **Profile switching race condition**: `hermes profile use` is global; must use `-p` flag
4. **State.db contention**: Multiple sessions write to same DB
5. **No built-in timeout**: Must wrap in subprocess timeout
6. **Exit codes unreliable**: Hermes may return 0 even on tool failure

## Recommended Implementation Path

**Primary (CLI Dispatch):**
1. Build dispatch with `hermes -p <profile> chat -q "<prompt>" --quiet --max-turns 10`
2. Wrap in `subprocess.Popen` with timeout
3. Capture `session_id` and response
4. Log output to run record
5. Mark dispatch complete/failed based on exit code

**Fallback (Telegram):**
1. Use existing `hermes send --to telegram` when CLI fails
2. Mark as "Manual execution needed"
3. Provide copy-prompt button
4. Accept manual output entry

**Monitoring:**
1. Poll `state.db` for session status every few seconds
2. Use `hermes sessions stats` to get recent session data
3. Show "Running" while subprocess is alive
4. Show "Completed" when subprocess exits

**Safety:**
1. Timeout after 120 seconds
2. Max turns limit = 10
3. Toolsets restricted per profile (ContentCreator doesn't need terminal)
4. Never pass secrets in prompt
5. Redact API keys from logged output
