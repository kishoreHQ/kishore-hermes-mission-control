# Security

## Never commit secrets

Do not commit `.env`, API keys, Telegram bot tokens, provider credentials, session files, cookies, private keys, runtime JSONL data, logs, generated uploads, or cache files.

## Environment variables

`.env.example` contains placeholders and non-secret defaults only. Real values belong in `.env` or systemd environment configuration and must remain untracked.

## Runtime data

Runtime JSONL files may contain prompts, outputs, session IDs, operational errors, and user-specific traces. They are ignored by `.gitignore` and must not be pushed.

## Telegram tokens

Mission Control currently sends through Hermes CLI/gateway paths. Telegram bot tokens must stay in Hermes gateway/profile secrets, not this repo.

## Provider API keys

OpenAI, Anthropic, Gemini, Google, FAL, Kling, and similar keys must stay in Hermes secrets/profile configuration, not Mission Control source control.

## Localhost-only mode

Default bind host is `127.0.0.1`. This is the safest mode. Use SSH tunnels or Tailscale/VPN for access.

## Public exposure warning

Exposing Mission Control publicly without authentication is unsafe. Before public exposure, add one of: authenticated reverse proxy, VPN/Tailscale-only access, firewall allowlist, identity-aware proxy, or application authentication.

## GitHub publishing checklist

```bash
git status --short
git diff --stat
git ls-files 'data/*.jsonl' 'logs/*' '*.log' '__pycache__/*' '*.pyc'
```

The last command should not list tracked runtime/cache files.

## Pre-push secret audit

```bash
grep -RInE "api[_-]?key|secret|token|password|authorization|bearer|PRIVATE_KEY|BOT_TOKEN|SESSION|COOKIE" . \
  --exclude-dir=.git \
  --exclude-dir=__pycache__ \
  --exclude="*.pyc" \
  --exclude="*.png" \
  --exclude="*.jpg" \
  --exclude=".env.example" \
  --exclude="SECURITY.md" \
  --exclude="README.md" \
  --exclude="SETUP.md" \
  --exclude="OPERATIONS.md" \
  --exclude="CHANGE_WORKFLOW.md" \
  --exclude="CONTRIBUTING.md" || true
```

Manually review every match. Documentation mentions of tokens/secrets are expected; real values are not.
