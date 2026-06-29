> **Implementation note (Hermes OS):** This PRD is the **product spec** (modules, layouts, APIs, KPIs). Code ships in `kishore-hermes-mission-control` using **Next.js 15** (`apps/web`), **FastAPI** (`apps/api`), **SQLite** `data/metrics.db` + JSONL, and **native VPS** deploy via `scripts/vps-native.sh`. Do **not** build a separate Vite `dashboard/` app. API routes ship under `/api/v1` first; `/api/v2` aliases later. Orchestration wraps `legacy/dispatch_engine.py`.

---

# Mission Control V2 — Product Requirements Document

**Version:** 2.0.0  
**Date:** 2026-06-29  
**Status:** Draft — Ready for Implementation  
**Repository:** https://github.com/kishoreHQ/kishore-hermes-mission-control  
**Classification:** AI Operating System — Single Source of Truth

---

## 1. Vision

### 1.1 Why Mission Control Exists

Mission Control is not a dashboard. It is the **AI Operating System** for Kishore's Hermes agent army. Every agent, workflow, job, repository, experiment, cost, failure, and success flows through here. It is the single pane of glass where operational truth lives.

### 1.2 Long-Term Goals

| Horizon | Goal |
|---------|------|
| **Now (V2)** | Unify all Hermes operations into one intelligent interface |
| **3 months** | Self-healing: detect failures, retry, report, learn |
| **6 months** | Predictive: anticipate failures, optimize costs, recommend actions |
| **12 months** | Autonomous: most operational decisions made by Mission Control itself |

### 1.3 Design Philosophy

Inspired by the best operational tools:
- **Linear** — Speed, keyboard-first, minimal UI
- **Vercel** — Deployment clarity, real-time status
- **Datadog** — Information density, metrics at a glance
- **Grafana** — Customizable, data-rich panels
- **Cursor** — AI-native, context-aware
- **GitHub** — Activity feeds, clear state transitions
- **Raycast** — Command palette, instant actions
- **OpenAI Playground** — Experimentation, iteration
- **Claude Console** — Reasoning transparency

**Core principles:**
1. **Simple** — No clutter. Every pixel earns its place.
2. **Fast** — Sub-100ms interactions. No loading spinners.
3. **Dense** — Maximum information per square inch.
4. **Beautiful** — Dark mode by default. Calm, professional.
5. **Zero Clutter** — If it's not actionable, it's not visible.

### 1.4 Operating Principles

| Principle | Implementation |
|-----------|---------------|
| **Local-first** | All data starts on the VPS. Sync to cloud only when needed. |
| **Event-driven** | Everything is an event. Events flow through a bus. |
| **Immutable logs** | Once written, never modified. Append-only. |
| **Self-documenting** | Every action leaves a trail. Every state has a reason. |
| **Fail loudly** | Errors are visible, actionable, and routed to the right place. |
| **Cost-conscious** | Every LLM call, every token, every API hit is tracked. |

---

## 2. Current Architecture Analysis

### 2.1 Existing System Inventory

| Component | Technology | Lines | Purpose | Status |
|-----------|-----------|-------|---------|--------|
| `server.py` | Python stdlib HTTP | 3,371 | API server, static serving, health checks | ✅ Active |
| `dispatch_engine.py` | Python stdlib | 1,830 | Workflow orchestration, dispatch, retry | ✅ Active |
| `static/app.js` | Vanilla JS | 790 | UI rendering, navigation, drawers | ✅ Active |
| `static/styles.css` | CSS | 256 | Styling, dark theme | ✅ Active |
| `static/index.html` | HTML | ~200 | Single-page shell | ✅ Active |
| **Total** | | **~6,247** | | |

### 2.2 Data Model

**Runtime JSONL files (append-only, gitignored):**
```
data/
├── action_log.jsonl          # Every action taken
├── dispatch_queue.jsonl      # Dispatch queue state
├── runs.jsonl                # All workflow/dispatch runs
├── routing_history.jsonl     # Profile routing decisions
├── workflow_events.jsonl     # Workflow lifecycle events
├── workflows.json            # Workflow definitions
├── services.json             # Service registry
├── nightly_builds.json       # Nightly build registry
├── tasks.json                # Task/Kanban data
├── docs.json                 # Documentation index
├── profile_settings.json     # Profile configurations
├── profile_routing_index.json # Routing keywords
└── routing_threshold.json    # Routing confidence thresholds
```

**External data sources:**
```
~/.hermes/
├── config.yaml               # Hermes configuration
├── cron/jobs.json            # Cron job definitions
├── cron/output/              # Cron job logs
├── profiles/                 # Hermes profiles
├── skills/                   # Custom skills
├── plugins/                  # Plugins
├── state.db                  # SQLite state
└── scripts/                  # Custom scripts

/tmp/contentforge/            # ContentForge state
/var/log/journal/            # Systemd logs
```

### 2.3 API Surface

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/healthz` | GET | Health check |
| `/api/status` | GET | Full system status |
| `/api/services/health` | GET | Service health cards |
| `/api/reliability/limits` | GET | Queue/concurrency limits |
| `/api/workflows` | GET | Workflow list |
| `/api/workflows/<id>/timeline` | GET | Workflow timeline |
| `/api/workflows/<id>/resume` | POST | Resume workflow |
| `/api/workflows/<id>/cancel` | POST | Cancel workflow |
| `/api/dispatch` | GET | Dispatch queue |
| `/api/dispatch/enqueue` | POST | Enqueue dispatch |
| `/api/dispatch/<id>/start` | POST | Start dispatch |
| `/api/dispatch/<id>/cancel` | POST | Cancel dispatch |

### 2.4 Service Registry

| Service | Port | Type | Status |
|---------|------|------|--------|
| Hermes Dashboard | 9119 | dashboard | 🟡 Legacy |
| Mission Control | 8090 | mission-control | 🟢 Active |
| Hermes WebUI | 8787 | dashboard | 🟢 Active |
| Claw3D | 3000 | app | 🔴 Removed |
| Claw3D Adapter | 18789 | adapter | 🔴 Removed |

### 2.5 Cron Job Inventory (19 Jobs)

| Category | Jobs | Schedule | Status |
|----------|------|----------|--------|
| **Content** | 5 | Daily | 🟢 All healthy |
| **Finance** | 4 | Weekdays | 🟢 All healthy |
| **System** | 3 | Daily | 🟢 All healthy |
| **Learning** | 1 | Daily | 🟢 Healthy |
| **Nightly** | 2 | Daily | 🟢 All healthy |
| **Career** | 1 | Daily | 🟢 Healthy |
| **Morning** | 1 | Daily | 🟢 Healthy |
| **Other** | 2 | Various | 🟡 One error |

### 2.6 Strengths of Current System

1. **Python stdlib only** — No pip dependencies, ultra-portable
2. **Subprocess.Popen streaming** — Real-time stdout/stderr
3. **Workflow orchestration** — Multi-step, dependency-aware
4. **Retry/resume/cancel** — Full lifecycle management
5. **VM-safe limits** — Concurrency throttling protects resources
6. **Safety gates** — Action risk classification (safe/medium/high)
7. **JSONL append-only** — Immutable audit trail

### 2.7 Weaknesses to Address

1. **UI is functional, not beautiful** — Needs visual overhaul
2. **No real-time updates** — Must refresh to see changes
3. **Limited data visualization** — No charts, graphs, trends
4. **No cost tracking** — LLM costs invisible
5. **No anomaly detection** — Failures only visible after they happen
6. **No predictive capabilities** — Cannot anticipate problems
7. **Mobile experience poor** — Not responsive enough
8. **No search** — Cannot find past runs, errors, patterns
9. **No integration with external tools** — GitHub, Linear, Notion disconnected

---

## 3. Current Workflows

### 3.1 Repository → Nightly Build → Dashboard Update

```
Repository (GitHub)
    ↓
Nightly Build Trigger (2 AM IST)
    ↓
Code Analysis (git diff, complexity, coverage)
    ↓
Agent Execution (Hermes profiles)
    ↓
Testing (make verify, smoke tests)
    ↓
Deployment (systemd restart)
    ↓
Metrics Collection (timing, success/failure)
    ↓
Dashboard Update (write to JSONL)
    ↓
Recommendations (pattern analysis)
    ↓
Next Tasks (queue for tomorrow)
```

### 3.2 ContentForge Pipeline

```
Content Discovery (web, RSS, YouTube)
    ↓
Idea Generation (quality scoring)
    ↓
Draft Creation (Hermes agent)
    ↓
Review Queue (human or AI approval)
    ↓
Publishing (xurl CLI → X/Twitter)
    ↓
Metrics Collection (impressions, likes, reposts)
    ↓
14-Day Aggregation (trend analysis)
    ↓
Experiment Orchestration (A/B testing)
```

### 3.3 StockPulse Pipeline

```
Pre-Market (2:30 AM UTC)
    ↓
Mid-Day (6:00 AM UTC)
    ↓
Pre-Close (9:00 AM UTC)
    ↓
Post-Market (10:30 AM UTC)
    ↓
StockForge Daily Picks (1:30 AM UTC)
    ↓
Metrics Aggregation (performance tracking)
```

### 3.4 Career Ops Pipeline

```
Upstream Sync (job board scraping)
    ↓
Skill Matching (resume vs job descriptions)
    ↓
Application Drafting (cover letters)
    ↓
Interview Prep (question generation)
    ↓
Progress Tracking (status updates)
```

### 3.5 DevSecOps Learning

```
Daily Check-in (4:30 AM UTC)
    ↓
Progress Load (references/progress.json)
    ↓
Topic Selection (spaced repetition)
    ↓
Content Generation (notes, diagrams, quizzes)
    ↓
Knowledge Check (interview questions)
    ↓
Progress Update (write back to JSON)
```

---

## 4. Future Workflow (Ideal State)

### 4.1 Autonomous Nightly Build

```
02:00 AM — Trigger
    ↓
System Health Check (auto-detect issues)
    ↓
Repository Sync (pull latest, check conflicts)
    ↓
Code Analysis (complexity, debt, security scan)
    ↓
Dependency Update Check (outdated packages)
    ↓
Test Suite (unit, integration, e2e)
    ↓
Performance Benchmark (compare to baseline)
    ↓
Build Decision (pass/fail/rollback)
    ↓
If PASS:
    ├── Deploy to staging
    ├── Smoke test staging
    ├── Deploy to production (gradual)
    ├── Monitor metrics (5 min)
    └── Confirm success
If FAIL:
    ├── Classify failure (root cause)
    ├── Attempt auto-fix (if safe)
    ├── Create incident report
    ├── Notify (Telegram)
    └── Rollback to last stable
    ↓
Metrics Collection (full telemetry)
    ↓
Dashboard Update (real-time push)
    ↓
Pattern Learning (update failure models)
    ↓
Recommendations (next day's priorities)
    ↓
06:00 AM — Morning Report (Telegram)
```

### 4.2 Self-Healing Failure Recovery

```
Failure Detected (any pipeline)
    ↓
Classification (automatic)
    ├── Timeout → Extend timeout, retry
    ├── Rate limit → Backoff, queue
    ├── Provider error → Fallback provider
    ├── Auth failure → Alert human
    ├── Disk full → Cleanup, retry
    └── Unknown → Log, alert, investigate
    ↓
Retry with Exponential Backoff
    ↓
If Retry Exhausted:
    ├── Escalate to human (Telegram)
    ├── Create incident record
    ├── Update failure pattern model
    └── Queue for manual review
    ↓
Success → Update success model, optimize
```

### 4.3 Continuous Optimization

```
Every Hour:
    ├── Cost Analysis (token usage, API costs)
    ├── Performance Analysis (duration, success rate)
    ├── Resource Analysis (CPU, RAM, disk)
    ├── Pattern Detection (anomalies, trends)
    └── Recommendation Generation

Every Day:
    ├── 24-Hour Cost Report
    ├── Success/Failure Trend
    ├── Resource Utilization
    ├── Top Failure Patterns
    └── Optimization Suggestions

Every Week:
    ├── Weekly Cost Summary
    ├── Pipeline Efficiency Score
    ├── Agent Performance Ranking
    ├── Resource Forecast
    └── Architecture Recommendations
```

---

## 5. Mission Control Modules (V2 Design)

### 5.1 Home — Executive Overview

**Purpose:** "What needs my attention right now?"

**Layout:**
```
┌─────────────────────────────────────────────────────────────┐
│  STATUS HERO                                                │
│  🟢 OPERATIONAL / 🟡 ATTENTION / 🔴 ACTION REQUIRED        │
│  "All systems operational" or "3 services degraded · 2      │
│   failures · 1 blocked workflow"                            │
│  5 active runs · 19 monitored services · updated 10:30 AM  │
├─────────────────────────────────────────────────────────────┤
│  BENTO METRICS (7 tiles)                                    │
│  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐             │
│  │ 5      │ │ 2      │ │ 3      │ │ 0      │             │
│  │Running │ │Failed  │ │Review  │ │Blocked │             │
│  └────────┘ └────────┘ └────────┘ └────────┘             │
│  ┌────────┐ ┌────────┐ ┌────────┐                        │
│  │ 7      │ │ $12.45 │ │ 2.3M   │                        │
│  │Workflows│ │Cost    │ │Tokens  │                        │
│  └────────┘ └────────┘ └────────┘                        │
├─────────────────────────────────────────────────────────────┤
│  RUNNING NOW (horizontal scroll)                          │
│  ┌────────┐ ┌────────┐ ┌────────┐                          │
│  │Content │ │Stock   │ │Career  │                          │
│  │Forge   │ │Pulse   │ │Ops     │                          │
│  │🟢 45%  │ │🟢 12%  │ │🟡 78%  │                          │
│  └────────┘ └────────┘ └────────┘                          │
├─────────────────────────────────────────────────────────────┤
│  NEEDS ATTENTION (de-duplicated, prioritized)               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 🔴 Service: Hermes WebUI — degraded                 │   │
│  │ 🟡 Run: ContentForge — failed (timeout)            │   │
│  │ 🟡 Review: StockPulse Pre-Market — needs review    │   │
│  │ 🔴 Workflow: Nightly Build — blocked (disk full)   │   │
│  └─────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│  QUICK ACTIONS                                              │
│  [Create Workflow] [Test Adapter] [Refresh All] [Send     │
│   Summary]                                                  │
├─────────────────────────────────────────────────────────────┤
│  RECENT ACTIVITY (chronological feed)                       │
│  10:30 — ContentForge completed ✅                          │
│  10:15 — StockPulse started 🟢                              │
│  09:45 — Career Ops failed 🔴 (timeout)                     │
│  09:30 — Nightly build completed ✅                          │
│  ...                                                        │
└─────────────────────────────────────────────────────────────┘
```

**Features:**
- Real-time status hero with operational verdict
- Bento-style metric tiles (click to drill down)
- Horizontal scroll of active runs with progress
- De-duplicated needs attention feed (prioritized)
- Quick action buttons (safe actions only)
- Activity feed with filtering

---

### 5.2 Agents — Profile Management

**Purpose:** "Which agents are handling what? How are they performing?"

**Layout:**
```
┌─────────────────────────────────────────────────────────────┐
│  AGENT FLEET (3-column grid)                                │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐             │
│  │ 🤖 Default │ │ 🎨 Content │ │ 📈 Finance │             │
│  │            │ │ Specialist │ │ Specialist│             │
│  │ Status: 🟢  │ │ Status: 🟢  │ │ Status: 🟢  │             │
│  │ Runs: 142  │ │ Runs: 89   │ │ Runs: 56   │             │
│  │ Success: 98%│ │ Success: 95%│ │ Success: 92%│             │
│  │ Avg: 2.3s  │ │ Avg: 4.5s  │ │ Avg: 3.1s  │             │
│  │ Tokens: 1.2M│ │ Tokens: 890K│ │ Tokens: 456K│             │
│  │ Cost: $8.50 │ │ Cost: $6.20 │ │ Cost: $3.10 │             │
│  │            │ │            │ │            │             │
│  │ [Test] [Edit] [Reload] │ [Test] [Edit] [Reload] │ ... │
│  └────────────┘ └────────────┘ └────────────┘             │
├─────────────────────────────────────────────────────────────┤
│  ROUTING ACCURACY                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Profile        │ Accuracy │ Trend │ Keywords       │   │
│  │ Default        │ 94%      │ ↑ 2%  │ 142 keywords   │   │
│  │ Content        │ 91%      │ ↑ 5%  │ 89 keywords    │   │
│  │ Finance        │ 88%      │ ↓ 1%  │ 56 keywords    │   │
│  └─────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│  MEMORY USAGE                                                 │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Profile        │ Memory   │ Last Update │ Size       │   │
│  │ Default        │ 🟢 OK    │ 10 min ago  │ 12KB       │   │
│  │ Content        │ 🟢 OK    │ 1 hour ago  │ 45KB       │   │
│  │ Finance        │ 🟡 Warn  │ 1 day ago   │ 128KB      │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

**Features:**
- Agent cards with performance metrics
- Routing accuracy tracking
- Memory usage monitoring
- Capability listing
- Cost per agent
- Success/failure rates
- Test routing button

---

### 5.3 Missions — Workflow Orchestration

**Purpose:** "What missions are in flight? What's blocked? What's next?"

**Layout:**
```
┌─────────────────────────────────────────────────────────────┐
│  MISSION BOARD (Kanban-style)                                 │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌────────┐ │
│  │ IN PROGRESS │ │ NEEDS REVIEW│ │ QUEUED      │ │DONE    │ │
│  │ (3)         │ │ (2)         │ │ (5)         │ │(12)    │ │
│  │             │ │             │ │             │ │        │ │
│  │ ┌────────┐ │ │ ┌────────┐ │ │ ┌────────┐ │ │        │ │
│  │ │Nightly │ │ │ │Content │ │ │ │Stock   │ │ │ ...    │ │
│  │ │Build   │ │ │ │Review  │ │ │ │Pulse   │ │ │        │ │
│  │ │🟢 67%   │ │ │ │🟡 Wait │ │ │ │⏳ 2:30 │ │ │        │ │
│  │ └────────┘ │ │ └────────┘ │ │ └────────┘ │ │        │ │
│  │ ┌────────┐ │ │             │ │ ┌────────┐ │ │        │ │
│  │ │Career  │ │ │             │ │ │ │DevSec  │ │ │        │ │
│  │ │Ops     │ │ │             │ │ │ │Ops     │ │ │        │ │
│  │ │🟡 45%   │ │ │             │ │ │ │⏳ 4:30 │ │ │        │ │
│  │ └────────┘ │ │             │ │ └────────┘ │ │        │ │
│  └─────────────┘ └─────────────┘ └─────────────┘ └────────┘ │
├─────────────────────────────────────────────────────────────┤
│  MISSION TIMELINE (Gantt-style)                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Nightly Build    ████████░░░░░░░░░░░░  2-3 AM      │   │
│  │ ContentForge     ░░░░████████░░░░░░░░  6-7 AM      │   │
│  │ StockPulse       ████░░░░████░░░░████  2:30-10:30  │   │
│  │ Career Ops       ░░░░░░░░░░░░████░░░░  2:30 AM      │   │
│  │ DevSecOps        ░░░░░░░░░░░░░░░░██░░  4:30 AM      │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

**Features:**
- Kanban board with drag-and-drop
- Gantt timeline view
- Dependency visualization
- Estimated completion times
- Blocker identification
- Resource allocation view

---

### 5.4 Nightly Builds — Experiment Tracking

**Purpose:** "What experiments are running? What worked? What failed?"

**Layout:**
```
┌─────────────────────────────────────────────────────────────┐
│  BUILD HISTORY                                                │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Date       │ Status │ Changes │ Perf    │ Action     │   │
│  │ 2026-06-29 │ 🟢 PASS│ 12 files│ +5%     │ [Promote]  │   │
│  │ 2026-06-28 │ 🟢 PASS│ 8 files │ +2%     │ [Promote]  │   │
│  │ 2026-06-27 │ 🔴 FAIL│ 15 files│ N/A     │ [Rollback] │   │
│  │ 2026-06-26 │ 🟡 WARN│ 3 files │ -1%     │ [Review]   │   │
│  └─────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│  PERFORMANCE COMPARISON                                       │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Metric     │ Baseline │ Current │ Delta   │ Trend    │   │
│  │ Build Time │ 45s      │ 38s     │ -15%   │ ↓        │   │
│  │ Test Pass  │ 98%      │ 99%     │ +1%    │ ↑        │   │
│  │ Bundle Size│ 245KB    │ 198KB   │ -19%   │ ↓        │   │
│  │ Load Time  │ 1.2s     │ 0.9s    │ -25%   │ ↓        │   │
│  └─────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│  REGRESSION DETECTION                                         │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Test              │ Baseline │ Current │ Status     │   │
│  │ API latency       │ 120ms    │ 145ms   │ 🟡 +21%   │   │
│  │ Memory usage      │ 45MB     │ 52MB    │ 🟡 +16%   │   │
│  │ Error rate        │ 0.1%     │ 0.15%   │ 🟡 +50%   │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

**Features:**
- Build history with status
- Performance comparison charts
- Regression detection
- Automatic rollback suggestions
- Screenshot comparison
- Change list visualization

---

### 5.5 Repositories — Code Health

**Purpose:** "What's the state of our code?"

**Layout:**
```
┌─────────────────────────────────────────────────────────────┐
│  REPOSITORY HEALTH                                            │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Repo              │ Health │ Issues │ PRs  │ Coverage│   │
│  │ mission-control   │ 🟢 95% │ 3      │ 1    │ 87%     │   │
│  │ hermes-agent-config│ 🟢 92%│ 5      │ 0    │ 82%     │   │
│  │ contentforge      │ 🟡 78% │ 12     │ 2    │ 65%     │   │
│  │ career-ops        │ 🟢 88% │ 8      │ 1    │ 71%     │   │
│  │ stockforge        │ 🟢 90% │ 4      │ 0    │ 75%     │   │
│  └─────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│  TECHNICAL DEBT                                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Category          │ Count │ Severity │ Trend      │   │
│  │ Outdated deps     │ 15    │ Medium   │ ↑          │   │
│  │ Security issues   │ 2     │ High     │ ↓          │   │
│  │ Code smells       │ 45    │ Low      │ →          │   │
│  │ Test gaps         │ 8     │ Medium   │ ↑          │   │
│  └─────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│  DEPENDENCY UPDATES                                           │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Package           │ Current │ Latest │ Priority     │   │
│  │ react             │ 18.2    │ 19.0   │ High         │   │
│  │ typescript        │ 5.2     │ 5.5    │ Medium       │   │
│  │ tailwindcss       │ 3.4     │ 4.0    │ Low          │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

**Features:**
- Repository health scores
- Open issues/PRs tracking
- Code coverage trends
- Technical debt inventory
- Dependency update queue
- Security vulnerability alerts

---

### 5.6 Intelligence — Learning System

**Purpose:** "What has the system learned? What patterns has it discovered?"

**Layout:**
```
┌─────────────────────────────────────────────────────────────┐
│  KNOWLEDGE GRAPH                                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ [Interactive graph visualization]                   │   │
│  │                                                     │   │
│  │  ContentForge ──→ Twitter API ──→ Rate Limits      │   │
│  │       │              │                              │   │
│  │       ↓              ↓                              │   │
│  │  StockPulse ──→ Market Data ──→ Timing Issues      │   │
│  │       │                                             │   │
│  │       ↓                                             │   │
│  │  Career Ops ──→ Job Boards ──→ Auth Changes         │   │
│  │                                                     │   │
│  └─────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│  PATTERNS DISCOVERED                                        │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Pattern                    │ Confidence │ Occurrences │   │
│  │ ContentForge fails at 10 AM│ 87%        │ 12/30 days │   │
│  │ StockPulse rate limit 9 AM │ 92%        │ 15/20 days │   │
│  │ Career Ops timeout on Mon  │ 78%        │ 8/12 weeks │   │
│  │ Nightly build disk full    │ 95%        │ 5/7 days   │   │
│  └─────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│  ANOMALY DETECTION                                          │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Anomaly                    │ Severity │ Detected    │   │
│  │ Token usage spike +300%   │ 🔴 High   │ 10 min ago  │   │
│  │ Unusual provider pattern  │ 🟡 Medium │ 1 hour ago  │   │
│  │ New error type: timeout_v2│ 🟡 Medium │ 2 hours ago │   │
│  └─────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│  RECOMMENDATIONS                                            │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 1. Increase ContentForge timeout to 120s (87%      │   │
│  │    confidence this will fix 10 AM failures)          │   │
│  │ 2. Add rate limit buffer to StockPulse (estimated    │   │
│  │    $5/month savings)                                 │   │
│  │ 3. Schedule disk cleanup before nightly build       │   │
│  │    (prevented 5/7 recent failures)                 │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

**Features:**
- Interactive knowledge graph
- Pattern discovery with confidence scores
- Anomaly detection with severity
- Automated recommendations
- Root cause analysis
- Prediction models

---

### 5.7 Cost Analytics — Financial Intelligence

**Purpose:** "What are we spending? Where can we optimize?"

**Layout:**
```
┌─────────────────────────────────────────────────────────────┐
│  COST OVERVIEW                                                │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Today: $12.45 │ This Week: $87.30 │ This Month: $340│   │
│  │ Budget: $500  │ Remaining: $160   │ Trend: ↑ 12%   │   │
│  └─────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│  COST BY PROVIDER                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Provider      │ Cost    │ %      │ Trend │ Tokens   │   │
│  │ OpenAI        │ $5.20   │ 42%    │ ↑     │ 1.2M     │   │
│  │ Anthropic     │ $4.10   │ 33%    │ ↓     │ 890K     │   │
│  │ DeepSeek      │ $2.50   │ 20%    │ ↑     │ 456K     │   │
│  │ OpenRouter    │ $0.65   │ 5%     │ →     │ 120K     │   │
│  └─────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│  COST BY AGENT                                                │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Agent         │ Cost    │ Runs   │ Avg/Run │ Efficiency│   │
│  │ ContentForge  │ $4.50   │ 45     │ $0.10   │ 95%      │   │
│  │ StockPulse    │ $3.20   │ 20     │ $0.16   │ 88%      │   │
│  │ Career Ops    │ $2.10   │ 12     │ $0.18   │ 82%      │   │
│  │ DevSecOps     │ $1.20   │ 30     │ $0.04   │ 98%      │   │
│  │ Nightly Build │ $1.45   │ 7      │ $0.21   │ 75%      │   │
│  └─────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│  DAILY TREND (7-day chart)                                   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ $15 │                                              │   │
│  │ $12 │    ██                                        │   │
│  │ $10 │    ██  ██                                    │   │
│  │  $8 │    ██  ██  ██                                │   │
│  │  $6 │    ██  ██  ██  ██                            │   │
│  │  $4 │ ██ ██  ██  ██  ██  ██                        │   │
│  │  $2 │ ██ ██  ██  ██  ██  ██  ██                    │   │
│  │     └────────────────────────────────────────────    │   │
│  │       Mon  Tue  Wed  Thu  Fri  Sat  Sun            │   │
│  └─────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│  OPTIMIZATION OPPORTUNITIES                                 │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 1. Switch StockPulse to DeepSeek (save $1.20/day)   │   │
│  │ 2. Batch Career Ops (reduce API calls by 40%)       │   │
│  │ 3. Cache DevSecOps responses (save $0.80/day)       │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

**Features:**
- Real-time cost tracking
- Provider comparison
- Agent-level cost breakdown
- Daily/weekly/monthly trends
- Budget warnings
- Optimization suggestions
- Token usage analytics

---

### 5.8 Infrastructure — System Health

**Purpose:** "What's happening under the hood?"

**Layout:**
```
┌─────────────────────────────────────────────────────────────┐
│  SYSTEM OVERVIEW                                              │
│  ┌──────────────────┐ ┌──────────────────┐ ┌────────────────┐ │
│  │ CPU              │ │ Memory           │ │ Disk           │ │
│  │ ████████░░ 45%   │ │ ██████░░░░ 51%   │ │ ████████░░ 64% │ │
│  │ 4 cores          │ │ 8.2G / 16G       │ │ 25G / 38G      │ │
│  │ Load: 0.52       │ │ Swap: 0.5G       │ │ Free: 13G      │ │
│  └──────────────────┘ └──────────────────┘ └────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│  DOCKER CONTAINERS                                            │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Container          │ Image        │ Status │ CPU │ Mem │   │
│  │ mission-control    │ mc:v2        │ 🟢 Up  │ 2%  │ 45M │   │
│  │ postgres           │ pg:16        │ 🟢 Up  │ 1%  │ 89M │   │
│  │ redis              │ redis:7      │ 🟢 Up  │ 0%  │ 12M │   │
│  └─────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│  NETWORK                                                      │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Interface │ RX       │ TX       │ Latency │ Status    │   │
│  │ eth0      │ 1.2 GB   │ 890 MB   │ 12ms    │ 🟢 OK     │   │
│  │ tailscale0│ 456 MB   │ 234 MB   │ 8ms     │ 🟢 OK     │   │
│  └─────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│  ACTIVE PROCESSES                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ PID   │ Name          │ CPU  │ Memory │ Status      │   │
│  │ 1234  │ python3       │ 2.3% │ 156MB  │ 🟢 Running  │   │
│  │ 1235  │ node          │ 1.1% │ 89MB   │ 🟢 Running  │   │
│  │ 1236  │ dockerd       │ 0.5% │ 234MB  │ 🟢 Running  │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

**Features:**
- Real-time CPU/RAM/Disk charts
- Docker container status
- Network monitoring
- Process list
- Tailscale status
- Cloud resource tracking
- Alert thresholds

---

### 5.9 AI Usage — Model Intelligence

**Purpose:** "Which models are we using? How are they performing?"

**Layout:**
```
┌─────────────────────────────────────────────────────────────┐
│  MODEL PERFORMANCE                                            │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Model              │ Calls │ Avg Latency │ Success │   │
│  │ gpt-4o             │ 234   │ 1.2s        │ 99%     │   │
│  │ claude-sonnet-4    │ 189   │ 2.1s        │ 97%     │   │
│  │ deepseek-v4-flash  │ 456   │ 0.8s        │ 95%     │   │
│  │ qwen3.6-plus       │ 123   │ 1.5s        │ 98%     │   │
│  └─────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│  TOKEN USAGE BY MODEL                                         │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Model              │ Input    │ Output   │ Total     │   │
│  │ gpt-4o             │ 890K     │ 234K     │ 1.1M      │   │
│  │ claude-sonnet-4    │ 456K     │ 189K     │ 645K      │   │
│  │ deepseek-v4-flash  │ 1.2M     │ 456K     │ 1.7M      │   │
│  │ qwen3.6-plus       │ 234K     │ 123K     │ 357K      │   │
│  └─────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│  PROVIDER FALLBACKS                                           │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Primary → Fallback │ Count │ Avg Time │ Success   │   │
│  │ OpenAI → Anthropic │ 12    │ 2.3s     │ 100%      │   │
│  │ Anthropic → DeepSeek│ 8     │ 1.8s     │ 100%      │   │
│  │ DeepSeek → OpenRouter│ 3    │ 3.1s     │ 67%       │   │
│  └─────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│  QUALITY SCORES                                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Model              │ Quality │ Speed │ Cost │ Overall  │   │
│  │ gpt-4o             │ 95%     │ 85%   │ 70%  │ 83%     │   │
│  │ claude-sonnet-4    │ 98%     │ 75%   │ 65%  │ 79%     │   │
│  │ deepseek-v4-flash  │ 88%     │ 95%   │ 95%  │ 93%     │   │
│  │ qwen3.6-plus       │ 90%     │ 80%   │ 90%  │ 87%     │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

**Features:**
- Model performance comparison
- Token usage breakdown
- Provider fallback tracking
- Quality scores (Q-SCORE system)
- Cost-quality tradeoff analysis
- Model recommendation engine

---

### 5.10 Content Pipeline — ContentForge Operations

**Purpose:** "What's in the content pipeline?"

**Layout:**
```
┌─────────────────────────────────────────────────────────────┐
│  CONTENT QUEUE                                                │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Topic                    │ Score │ Status │ Account │   │
│  │ Kubernetes networking      │ 8.5   │ Ready  │ @devops │   │
│  │ CI/CD best practices       │ 7.8   │ Ready  │ @devops │   │
│  │ Docker tips              │ 9.2   │ Ready  │ @devops │   │
│  │ Market analysis            │ 7.5   │ Draft  │ @unplug │   │
│  └─────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│  PUBLISHED (Last 7 Days)                                      │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Post                │ Views │ Likes │ Reposts │ Date │   │
│  │ Docker Best Practices│ 1.2K  │ 45    │ 12      │ Today│   │
│  │ K8s Tips            │ 890   │ 32    │ 8       │ yest │   │
│  │ DevOps Trends       │ 2.1K  │ 89    │ 34      │ 2d   │   │
│  └─────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│  14-DAY METRICS                                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Metric        │ Value  │ Trend │ vs Last Period      │   │
│  │ Posts         │ 14     │ ↑     │ +2                  │   │
│  │ Avg Views     │ 1.4K   │ ↑     │ +15%                │   │
│  │ Engagement    │ 4.2%   │ ↑     │ +0.3%               │   │
│  │ Followers     │ 12.3K  │ ↑     │ +234                │   │
│  └─────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│  EXPERIMENTS                                                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Experiment          │ Status │ Result │ Confidence │   │
│  │ Thread vs Single    │ Active │ +23%   │ 87%        │   │
│  │ Morning vs Evening  │ Done   │ +12%   │ 92%        │   │
│  │ Image vs Text       │ Done   │ +45%   │ 95%        │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

**Features:**
- Content queue with quality scores
- Published post metrics
- 14-day rolling analytics
- A/B experiment tracking
- Account performance comparison
- Engagement trend analysis

---

## 6. Technical Architecture (V2)

### 6.1 Stack

| Layer | Technology | Reason |
|-------|-----------|--------|
| **Frontend** | React 19 + Vite + TypeScript | Modern, fast, type-safe |
| **Styling** | Tailwind CSS v3 + shadcn/ui | Utility-first, component-rich |
| **State** | Zustand | Lightweight, no boilerplate |
| **Charts** | Recharts | React-native, customizable |
| **Backend** | Python stdlib (keep) | Zero dependencies, portable |
| **API** | REST + Server-Sent Events | Simple, real-time capable |
| **Data** | SQLite + JSONL | Structured + append-only |
| **Events** | In-memory event bus | Simple, no external deps |
| **Search** | SQLite FTS5 | Full-text, no external service |
| **Auth** | Tailscale-only | Zero-config, secure |

### 6.2 Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│                        FRONTEND                              │
│  React 19 + Vite + Tailwind + shadcn/ui + Zustand + Recharts│
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │  Home        │  │  Agents      │  │  Missions    │   │
│  │  Dashboard   │  │  Profile     │  │  Workflow    │   │
│  └──────────────┘  └──────────────┘  └──────────────┘   │
│                           │                                  │
│                           │ REST API + SSE                   │
│                           ▼                                  │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                        BACKEND                               │
│  Python stdlib HTTP Server (server.py)                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │  API Router  │  │  Event Bus   │  │  Data Layer  │   │
│  │  /api/*      │  │  pub/sub     │  │  SQLite/JSONL│   │
│  └──────────────┘  └──────────────┘  └──────────────┘   │
│                           │                                  │
│                           │ Read/Write                       │
│                           ▼                                  │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                        DATA SOURCES                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │  SQLite      │  │  JSONL Logs  │  │  System      │   │
│  │  state.db    │  │  runs.jsonl  │  │  df, ps,     │   │
│  │  metrics.db  │  │  events.jsonl│  │  journalctl  │   │
│  └──────────────┘  └──────────────┘  └──────────────┘   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │  Hermes      │  │  ContentForge│  │  External    │   │
│  │  cron/jobs   │  │  ideas.json  │  │  GitHub, X   │   │
│  │  profiles    │  │  posted.json │  │  APIs        │   │
│  └──────────────┘  └──────────────┘  └──────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### 6.3 API Design (V2 Additions)

```
# Existing endpoints (keep)
GET  /healthz
GET  /api/status
GET  /api/services/health
GET  /api/reliability/limits
GET  /api/workflows
GET  /api/workflows/<id>/timeline
POST /api/workflows/<id>/resume
POST /api/workflows/<id>/cancel
GET  /api/dispatch
POST /api/dispatch/enqueue
POST /api/dispatch/<id>/start
POST /api/dispatch/<id>/cancel

# New endpoints (V2)
GET  /api/v2/metrics/realtime          # Real-time metrics stream (SSE)
GET  /api/v2/cost/summary              # Cost summary
GET  /api/v2/cost/by-provider          # Cost breakdown by provider
GET  /api/v2/cost/by-agent             # Cost breakdown by agent
GET  /api/v2/cost/trend                # Cost trend (daily/weekly/monthly)
GET  /api/v2/agents/performance        # Agent performance metrics
GET  /api/v2/agents/routing            # Routing accuracy
GET  /api/v2/intelligence/patterns     # Discovered patterns
GET  /api/v2/intelligence/anomalies    # Detected anomalies
GET  /api/v2/intelligence/recommendations # AI recommendations
GET  /api/v2/content/queue             # Content queue
GET  /api/v2/content/published        # Published content
GET  /api/v2/content/metrics           # Content metrics
GET  /api/v2/content/experiments       # A/B experiments
GET  /api/v2/repos/health              # Repository health
GET  /api/v2/repos/debt                # Technical debt
GET  /api/v2/repos/dependencies        # Dependency updates
GET  /api/v2/infra/system              # System health
GET  /api/v2/infra/docker              # Docker containers
GET  /api/v2/infra/network             # Network status
GET  /api/v2/ai/models                 # Model performance
GET  /api/v2/ai/tokens                 # Token usage
GET  /api/v2/ai/fallbacks              # Fallback tracking
GET  /api/v2/search?q=...              # Global search
GET  /api/v2/events/stream             # Event stream (SSE)
POST /api/v2/actions/execute           # Execute action
POST /api/v2/nightly/trigger           # Trigger nightly build
POST /api/v2/cleanup/disk              # Trigger disk cleanup
```

### 6.4 Event Bus

```python
# Simple in-memory event bus
class EventBus:
    def __init__(self):
        self.subscribers: dict[str, list[callable]] = {}
    
    def subscribe(self, event_type: str, handler: callable):
        self.subscribers.setdefault(event_type, []).append(handler)
    
    def publish(self, event_type: str, payload: dict):
        for handler in self.subscribers.get(event_type, []):
            handler(payload)

# Event types
EVENT_DISPATCH_STARTED = "dispatch.started"
EVENT_DISPATCH_COMPLETED = "dispatch.completed"
EVENT_DISPATCH_FAILED = "dispatch.failed"
EVENT_WORKFLOW_STARTED = "workflow.started"
EVENT_WORKFLOW_COMPLETED = "workflow.completed"
EVENT_CRON_TRIGGERED = "cron.triggered"
EVENT_CRON_FAILED = "cron.failed"
EVENT_SERVICE_DEGRADED = "service.degraded"
EVENT_COST_THRESHOLD = "cost.threshold"
EVENT_ANOMALY_DETECTED = "anomaly.detected"
EVENT_PATTERN_DISCOVERED = "pattern.discovered"
```

### 6.5 Real-Time Updates

```javascript
// Server-Sent Events for real-time updates
const eventSource = new EventSource('/api/v2/events/stream');

eventSource.addEventListener('dispatch.started', (e) => {
    const data = JSON.parse(e.data);
    updateRunningNow(data);
});

eventSource.addEventListener('dispatch.completed', (e) => {
    const data = JSON.parse(e.data);
    updateMetrics(data);
    showToast(`${data.profile} completed`, 'success');
});

eventSource.addEventListener('anomaly.detected', (e) => {
    const data = JSON.parse(e.data);
    showAlert(data.severity, data.message);
});
```

---

## 7. Implementation Plan

### Phase 1: Foundation (Week 1-2)

| Task | Deliverable |
|------|-------------|
| Set up React 19 + Vite + TypeScript | `dashboard/` directory with build pipeline |
| Install Tailwind + shadcn/ui | Component library ready |
| Create design system tokens | `src/styles/tokens.css` |
| Build app shell | Sidebar, top bar, content area |
| Implement navigation | Section routing, command palette |
| Create API client | `src/lib/api.ts` with fetch + SSE |

### Phase 2: Core Modules (Week 3-4)

| Task | Deliverable |
|------|-------------|
| Home module | Status hero, metrics, running now, attention |
| Agents module | Profile cards, routing accuracy, memory |
| Missions module | Kanban board, timeline view |
| Services module | Health cards, actions, logs |
| Real-time updates | SSE integration, live data |

### Phase 3: Intelligence (Week 5-6)

| Task | Deliverable |
|------|-------------|
| Cost tracking | Cost by provider, agent, trend |
| Pattern detection | Failure pattern analysis |
| Anomaly detection | Statistical anomaly detection |
| Recommendations | AI-generated optimization suggestions |
| Knowledge graph | Relationship visualization |

### Phase 4: Advanced Features (Week 7-8)

| Task | Deliverable |
|------|-------------|
| Content pipeline | Queue, published, metrics, experiments |
| Repository health | Code health, debt, dependencies |
| Infrastructure monitoring | CPU, RAM, disk, Docker, network |
| AI usage analytics | Model performance, token usage, fallbacks |
| Search | Global search across all data |

### Phase 5: Polish (Week 9-10)

| Task | Deliverable |
|------|-------------|
| Mobile responsiveness | Bottom nav, simplified cards |
| Keyboard shortcuts | ⌘K palette, vim-style navigation |
| Dark/light mode | Theme toggle, system preference |
| Performance optimization | Lazy loading, virtualization |
| Documentation | Complete docs, examples, runbook |

---

## 8. Data Model (V2)

### 8.1 SQLite Schema

```sql
-- Metrics (time-series)
CREATE TABLE metrics (
    id INTEGER PRIMARY KEY,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    category TEXT NOT NULL,  -- 'cost', 'performance', 'system'
    metric TEXT NOT NULL,    -- 'tokens', 'latency', 'cpu'
    value REAL NOT NULL,
    unit TEXT,               -- 'usd', 'ms', 'percent'
    tags TEXT                -- JSON array
);

-- Events (append-only)
CREATE TABLE events (
    id INTEGER PRIMARY KEY,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    type TEXT NOT NULL,
    source TEXT NOT NULL,    -- 'cron', 'dispatch', 'workflow'
    payload TEXT,            -- JSON
    severity TEXT            -- 'info', 'warn', 'error', 'critical'
);

-- Patterns (discovered)
CREATE TABLE patterns (
    id INTEGER PRIMARY KEY,
    discovered_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    pattern TEXT NOT NULL,
    confidence REAL NOT NULL,
    occurrences INTEGER NOT NULL,
    source TEXT NOT NULL,
    action_taken TEXT
);

-- Anomalies (detected)
CREATE TABLE anomalies (
    id INTEGER PRIMARY KEY,
    detected_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    metric TEXT NOT NULL,
    expected_value REAL NOT NULL,
    actual_value REAL NOT NULL,
    deviation_percent REAL NOT NULL,
    severity TEXT NOT NULL,
    resolved_at DATETIME,
    resolution TEXT
);

-- Costs (tracked)
CREATE TABLE costs (
    id INTEGER PRIMARY KEY,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    agent TEXT NOT NULL,
    tokens_input INTEGER NOT NULL,
    tokens_output INTEGER NOT NULL,
    cost_usd REAL NOT NULL,
    run_id TEXT
);

-- Full-text search
CREATE VIRTUAL TABLE search_index USING fts5(
    content,
    source,
    timestamp
);
```

### 8.2 JSONL Files (Keep Existing)

```
data/
├── action_log.jsonl          # (keep) Every action
├── dispatch_queue.jsonl      # (keep) Dispatch state
├── runs.jsonl                # (keep) All runs
├── routing_history.jsonl     # (keep) Routing decisions
├── workflow_events.jsonl     # (keep) Workflow events
├── v2/
│   ├── metrics.jsonl         # (new) Time-series metrics
│   ├── events.jsonl          # (new) System events
│   ├── patterns.jsonl        # (new) Discovered patterns
│   ├── anomalies.jsonl       # (new) Detected anomalies
│   └── costs.jsonl           # (new) Cost records
```

---

## 9. Integration Points

### 9.1 Hermes Agent

| Integration | Method | Data |
|-------------|--------|------|
| Cron jobs | Read `~/.hermes/cron/jobs.json` | Schedule, status, history |
| Profiles | Read `~/.hermes/profiles/` | Config, routing, memory |
| Skills | Read `~/.hermes/skills/` | Available capabilities |
| State | Read `~/.hermes/state.db` | SQLite state |
| Output | Read `~/.hermes/cron/output/` | Job logs |

### 9.2 ContentForge

| Integration | Method | Data |
|-------------|--------|------|
| Ideas | Read `/tmp/contentforge/ideas.json` | Content queue |
| Posted | Read `/tmp/contentforge/posted.json` | Published content |
| Metrics | Read `/tmp/contentforge/metrics.json` | Performance |
| Queue | Read `/tmp/contentforge/queue.json` | Pending items |

### 9.3 External APIs

| Integration | API | Data |
|-------------|-----|------|
| GitHub | REST API | Repos, issues, PRs, commits |
| X/Twitter | Xquik API | Posts, metrics, engagement |
| Telegram | Bot API | Notifications, summaries |
| Tailscale | API | Network status, devices |

---

## 10. Security & Safety

### 10.1 Action Safety Model (Keep Existing)

| Risk Level | Examples | UI Behavior |
|------------|----------|-------------|
| **Safe** | Refresh, view logs, export | Execute immediately, show toast |
| **Medium** | Restart service, run cron | Approval code modal |
| **High** | Delete data, modify config | Blocked in UI, require CLI |

### 10.2 Authentication

- **Tailscale-only access** — No open ports, no passwords
- **SSH key auth** — For VPS access
- **No API keys in frontend** — All secrets stay on server

### 10.3 Audit Trail

Every action logged to `data/action_log.jsonl`:
```json
{
  "timestamp": "2026-06-29T10:30:00Z",
  "user": "kishore",
  "action": "restart_service",
  "target": "mission-control.service",
  "risk": "medium",
  "approval_code": "123456",
  "result": "success",
  "ip": "100.64.123.45"
}
```

---

## 11. Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Page load time | < 1s | Lighthouse |
| Time to first paint | < 200ms | Lighthouse |
| API response time | < 100ms | Server logs |
| Real-time latency | < 500ms | SSE timestamps |
| Uptime | > 99.9% | Health checks |
| Cost visibility | 100% | All LLM calls tracked |
| Failure detection | < 5min | Anomaly detection |
| Mobile usability | > 90 | Lighthouse mobile |

---

## 12. Appendix

### 12.1 File Structure

```
kishore-hermes-mission-control/
├── README.md
├── AGENTS.md
├── SETUP.md
├── OPERATIONS.md
├── ARCHITECTURE.md
├── SECURITY.md
├── CHANGE_WORKFLOW.md
├── CONTRIBUTING.md
├── CHANGELOG.md
│
├── Makefile
├── server.py                    # API server (keep, extend)
├── dispatch_engine.py           # Workflow engine (keep, extend)
├── event_bus.py                 # NEW: Event bus
├── cost_tracker.py              # NEW: Cost tracking
├── pattern_detector.py          # NEW: Pattern detection
├── anomaly_detector.py          # NEW: Anomaly detection
├── recommendation_engine.py     # NEW: AI recommendations
│
├── .env.example
├── .gitignore
├── mission-control.service.example
│
├── dashboard/                   # NEW: React frontend
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── tailwind.config.js
│   ├── index.html
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx
│   │   ├── index.css
│   │   ├── components/
│   │   │   ├── ui/            # shadcn/ui components
│   │   │   ├── layout/          # Shell, sidebar, topbar
│   │   │   ├── home/            # Home module
│   │   │   ├── agents/          # Agents module
│   │   │   ├── missions/        # Missions module
│   │   │   ├── builds/          # Nightly builds module
│   │   │   ├── repos/           # Repositories module
│   │   │   ├── intelligence/    # Intelligence module
│   │   │   ├── cost/            # Cost analytics module
│   │   │   ├── infra/           # Infrastructure module
│   │   │   ├── ai/              # AI usage module
│   │   │   └── content/         # Content pipeline module
│   │   ├── hooks/
│   │   │   ├── useApi.ts
│   │   │   ├── useRealtime.ts
│   │   │   ├── useSearch.ts
│   │   │   └── useTheme.ts
│   │   ├── lib/
│   │   │   ├── api.ts           # API client
│   │   │   ├── sse.ts           # SSE connection
│   │   │   ├── utils.ts         # Utilities
│   │   │   └── constants.ts     # Constants
│   │   ├── stores/
│   │   │   ├── useStore.ts      # Zustand store
│   │   │   └── slices/          # Store slices
│   │   ├── types/
│   │   │   └── index.ts         # TypeScript types
│   │   └── styles/
│   │       └── tokens.css         # Design tokens
│   └── public/
│       └── favicon.ico
│
├── static/                      # OLD: Keep for backward compat
│   ├── index.html
│   ├── app.js
│   └── styles.css
│
├── data/                        # Runtime data (gitignored)
│   ├── .gitkeep
│   ├── action_log.jsonl
│   ├── dispatch_queue.jsonl
│   ├── runs.jsonl
│   ├── routing_history.jsonl
│   ├── workflow_events.jsonl
│   ├── workflows.json
│   ├── services.json
│   ├── nightly_builds.json
│   ├── tasks.json
│   ├── docs.json
│   ├── profile_settings.json
│   ├── profile_routing_index.json
│   ├── routing_threshold.json
│   └── v2/                      # NEW: V2 data
│       ├── metrics.jsonl
│       ├── events.jsonl
│       ├── patterns.jsonl
│       ├── anomalies.jsonl
│       └── costs.jsonl
│
├── scripts/
│   ├── verify_mission_control.sh
│   ├── audit_scheduled_jobs.sh
│   └── setup_v2.sh              # NEW: V2 setup script
│
├── docs/
│   ├── ui_research_mission_control.md
│   ├── mission_control_ui_redesign_plan.md
│   └── PRD_V2.md              # THIS DOCUMENT
│
├── tests/
│   └── test_portability.py
│
└── examples/
```

### 12.2 Environment Variables

```bash
# Existing
MISSION_CONTROL_HOST=127.0.0.1
MISSION_CONTROL_PORT=8090
HERMES_HOME=/root/.hermes
MC_MAX_CONCURRENT_DISPATCHES=3
MC_MAX_QUEUED_DISPATCHES=25
MC_MAX_CONCURRENT_WORKFLOWS=2
MC_MAX_WORKFLOW_RUNTIME_SECONDS=3600
MC_MAX_RETRIES_PER_WORKFLOW=6

# New (V2)
MC_V2_DASHBOARD_PATH=./dashboard/dist
MC_V2_ENABLE_REALTIME=true
MC_V2_ENABLE_COST_TRACKING=true
MC_V2_ENABLE_ANOMALY_DETECTION=true
MC_V2_COST_BUDGET_DAILY=20.00
MC_V2_COST_BUDGET_MONTHLY=500.00
MC_V2_ANOMALY_THRESHOLD=2.0  # Standard deviations
MC_V2_PATTERN_MIN_CONFIDENCE=0.75
MC_V2_ENABLE_TELEGRAM_ALERTS=true
MC_V2_TELEGRAM_BOT_TOKEN=     # From env, not committed
```

### 12.3 Color System (Design Tokens)

```css
:root {
  /* Background */
  --bg-base: #090b0f;
  --bg-surface: #111318;
  --bg-elevated: #171a22;
  --bg-sidebar: #0c0e13;
  --bg-hover: #1a1d26;
  --bg-active: #22262f;
  
  /* Border */
  --border: #1e2230;
  --border-hover: #2a3040;
  --border-active: #3a4050;
  
  /* Text */
  --text-primary: #e8ecf4;
  --text-secondary: #8892a8;
  --text-muted: #555d70;
  --text-inverse: #090b0f;
  
  /* Accent */
  --accent: #4da6ff;
  --accent-dim: #3a7ecc;
  --accent-hover: #6ab8ff;
  
  /* Status */
  --status-ok: #34d399;
  --status-warn: #f59e0b;
  --status-error: #ef4444;
  --status-info: #60a5fa;
  --status-idle: #6b7280;
  
  /* Severity backgrounds */
  --severity-error-bg: rgba(239, 68, 68, 0.1);
  --severity-warn-bg: rgba(245, 158, 11, 0.1);
  --severity-info-bg: rgba(96, 165, 250, 0.1);
  
  /* Typography */
  --font-sans: ui-sans-serif, system-ui, -apple-system, sans-serif;
  --font-mono: ui-monospace, 'Cascadia Code', 'Fira Code', monospace;
  
  /* Spacing */
  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-5: 20px;
  --space-6: 24px;
  --space-8: 32px;
  --space-12: 48px;
  
  /* Radius */
  --radius-sm: 6px;
  --radius-md: 10px;
  --radius-lg: 14px;
  --radius-pill: 999px;
}
```

---

## 13. Conclusion

Mission Control V2 is the evolution from a functional operations panel to an **AI Operating System**. It unifies every aspect of Hermes operations into a single, beautiful, intelligent interface.

**Key differentiators:**
1. **Real-time** — Live updates via SSE, no refresh needed
2. **Intelligent** — Pattern detection, anomaly detection, recommendations
3. **Cost-aware** — Every token tracked, every dollar accounted
4. **Self-improving** — Learns from failures, optimizes over time
5. **Beautiful** — Inspired by the best, designed for speed

**Next steps:**
1. Clone the repository
2. Set up the React frontend (`dashboard/`)
3. Implement Phase 1 (Foundation)
4. Iterate with nightly builds
5. Evolve every day

---

*Mission Control is not a destination. It is a journey of continuous improvement.*

*Built for the Hermes Agent Army.*
*Every day, it gets smarter.*
