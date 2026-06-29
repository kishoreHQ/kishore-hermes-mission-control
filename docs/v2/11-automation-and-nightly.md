# 11 — Automation & Nightly Build Architecture

---

## Overview

The **Nightly Build System** runs at ~2:00 AM daily. It executes a declarative DAG of jobs via the dispatch engine, persists results to Postgres, generates a morning report, and surfaces everything on the **Today** space.

This replaces the current manual "nightly builds" tracking UI with **real automation**.

---

## Scheduler

### Trigger
- **Primary:** APScheduler cron `0 2 * * *` in `scheduler_service`
- **Fallback:** System cron invokes `hermes-os nightly run`
- **Manual:** `POST /api/v1/nightly/trigger` (medium-risk action)

### Execution Flow
```
02:00 AM
    │
    ▼
Create nightly_run record (status: running)
    │
    ▼
Load DAG from config/nightly-dag.yaml
    │
    ▼
Topological sort → execute jobs in parallel where deps allow
    │
    ├──► Job: research_ai_tools → dispatch ContentCreator/DeepResearch
    ├──► Job: update_learning → dispatch Tutor
    ├──► Job: stock_research → dispatch MarketAnalyst
    ├──► Job: content_ideas → dispatch ContentCreator
    ├──► Job: index_knowledge → local script + embed
    ├──► Job: backup_data → shell script
    ├──► Job: eval_agents → analyze dispatch stats
    └──► Job: clean_temp → shell script
    │
    ▼
Wait for all jobs (timeout: 2h total)
    │
    ▼
Generate morning_report.md (aggregate job outputs)
    │
    ▼
Update nightly_run (status: completed/partial/failed)
    │
    ▼
Publish SSE event: nightly.completed
    │
    ▼
Today surface shows briefing on next open
```

---

## DAG Configuration

`config/nightly-dag.yaml`:

```yaml
version: 1
schedule: "0 2 * * *"
timeout_minutes: 120

jobs:
  research_ai_tools:
    profile: DeepResearch
    prompt: "Research latest AI tools and models released this week. Summarize top 5."
    timeout: 600
    artifact: ai-tools-summary.md

  update_learning:
    profile: Tutor
    prompt: "Review my learning progress and update the learning roadmap."
    timeout: 600
    depends_on: []
    artifact: learning-roadmap.json

  stock_research:
    profile: MarketAnalyst
    prompt: "Refresh NSE/Nifty research. Update stock picks."
    timeout: 900
    artifact: stock-research.md

  content_ideas:
    profile: ContentCreator
    prompt: "Generate 5 content ideas for this week based on recent AI news."
    timeout: 600
    depends_on: [research_ai_tools]
    artifact: content-ideas.json

  index_knowledge:
    type: script
    command: "python scripts/index_knowledge.py"
    timeout: 300

  backup_data:
    type: script
    command: "bash scripts/backup.sh"
    timeout: 600

  eval_agents:
    type: script
    command: "python scripts/eval_agent_performance.py"
    timeout: 300

  clean_temp:
    type: script
    command: "bash scripts/clean_temp.sh"
    timeout: 120

  morning_report:
    type: report
    depends_on: [research_ai_tools, update_learning, stock_research, content_ideas, index_knowledge, backup_data, eval_agents]
    template: templates/morning-report.md.j2
```

---

## Job Types

| Type | Execution |
|------|-----------|
| `dispatch` | Enqueue via dispatch_engine with profile + prompt |
| `script` | Run shell/python script with timeout |
| `report` | Jinja2 template aggregating job artifacts |

---

## Artifacts

Stored at `data/artifacts/nightly/{run_id}/{job_key}/`

Indexed in `nightly_jobs.artifact_paths` JSONB.

Morning report copied to `data/artifacts/nightly/{run_id}/morning-report.md`.

---

## Failure Handling

| Scenario | Behavior |
|----------|----------|
| Single job timeout | Mark failed; continue independent jobs |
| Dispatch failure | Classify via dispatch_engine; retry once if policy allows |
| >50% jobs fail | Run status = `failed`; alert on Today |
| Script non-zero exit | Mark failed; capture stderr in `error` field |
| Total pipeline timeout | Cancel running dispatches; status = `partial` |

### Auto-RCA (Phase 4)
On failure, `ai_service.rca()` analyzes stderr + logs → recommendation on Today.

---

## UI Surfaces

### Agents → Nightly
- Pipeline DAG visualization (last run)
- Job list with status, duration, artifacts
- Historical trend chart (7/30 day success rate)
- Manual trigger button

### Today
- Nightly metric card (12/14 ✓)
- Nightly report summary panel
- Failed job in needs-attention

### Insights
- Nightly runs timeline
- Productivity evaluation from `eval_agents` job

---

## Integration with Hermes Cron

Existing Hermes cron jobs (ContentForge, StockPulse, etc.) continue running on their schedules.

Nightly DAG **orchestrates** research/index/report jobs that complement cron — does not replace cron.

Optional: nightly job triggers `hermes cron run <job_id>` for specific crons.

---

## Migration from v1 nightly_builds.json

Manual build registry → `nightly_runs` with `source: manual` flag.

Promotion workflow (Built → Testing → Promote) moves to System → Experiments (Phase 5).

---

*Next: [12-ai-feature-roadmap.md](./12-ai-feature-roadmap.md)*
