# 06 — Information Architecture

---

## Navigation Model

### Level 1: Spaces (Sidebar — 9 items)
Primary navigation. Each space is a domain.

### Level 2: Modules (Sub-nav within space)
Tabs or secondary sidebar. Context-specific.

### Level 3: Entities (Drawer / detail panel)
Runs, workflows, dispatches, tasks, builds — slide-in from right.

### Global: Command Palette (⌘K)
Jump to any space, module, action, or entity.

### Global: AI Chat (⌘J)
Ask anything; context-aware across spaces.

---

## Space Definitions

### 1. Today (Default Landing)
**Question:** "What should I focus on right now?"

| Module | Source | Priority |
|--------|--------|----------|
| Morning briefing | Nightly report + manual agenda | P0 |
| Needs attention | Failed crons, degraded services, blocked workflows | P0 |
| Metric cards | Agents active, nightly status, content queue, stocks | P0 |
| Today's agenda | Tasks due today + calendar (future) | P1 |
| Quick actions | Dispatch, run cron, capture idea, send summary | P0 |
| Recommendations | AI-generated from nightly pipeline | P1 |
| Recent activity | Chronological feed | P1 |

### 2. Agents & Automation
**Question:** "What is my AI workforce doing?"

| Module | Maps from V1 | Priority |
|--------|--------------|----------|
| Agent Fleet | agents-section + cron tags | P0 |
| Workflows | workflows-section | P0 |
| Dispatch Queue | dispatch-section | P0 |
| Automation / Cron | cron-section | P0 |
| Nightly Builds | nightly-section → automated pipeline | P1 |
| Prompt Library | New | P2 |
| Model / Token / Cost | docs cost tracker + state.db | P2 |

### 3. Create
**Question:** "What am I making?"

| Module | Integration | Priority |
|--------|-------------|----------|
| Content Studio | ContentForge `/tmp/contentforge/` | P2 |
| Video Pipeline | AI Creator lane | P3 |
| Publishing Center | Posted queue + metrics | P2 |

### 4. Knowledge
**Question:** "What do I know?"

| Module | Integration | Priority |
|--------|-------------|----------|
| Research Lab | DeepResearch profile + morning intelligence | P2 |
| Knowledge Graph | `/root/wiki` + wikilinks | P2 |
| Learning Hub | DevSecOps + Tutor profile | P2 |
| Document Library | Recent files | P2 |
| Memory | Hermes memory + pgvector | P1 |

### 5. Wealth
**Question:** "How are my investments?"

| Module | Integration | Priority |
|--------|-------------|----------|
| Finance Hub | Overview | P2 |
| Stock Dashboard | StockForge + StockPulse cron | P2 |
| Investing | Research artifacts | P3 |

### 6. Life
**Question:** "How am I living intentionally?"

| Module | Priority |
|--------|----------|
| Goals | P3 |
| Habits | P3 |
| Journal | P3 |
| Calendar | P2 |
| Career | career-ops lane | P2 |
| Health | P3 |

### 7. Infrastructure
**Question:** "Is everything running?"

| Module | Maps from V1 | Priority |
|--------|--------------|----------|
| Services | services-section | P0 |
| System Health | Home health bar + probes | P0 |
| Logs | logs-section | P0 |
| Servers | services.json + systemd | P1 |

### 8. Insights
**Question:** "What patterns emerge?"

| Module | Priority |
|--------|----------|
| Reports | Nightly + manual exports | P1 |
| Analytics | LLM cost, productivity | P2 |
| Timeline | Unified event stream | P2 |
| Activity Feed | action_log + runs + cron | P1 |

### 9. System
**Question:** "How is it configured?"

| Module | Priority |
|--------|----------|
| Settings | Profile mode, thresholds, refresh | P0 |
| Plugin Marketplace | Widget/plugin registry | P1 |
| Workspaces | Multi-layout presets | P3 |
| Search | Global semantic search | P1 |
| Docs / Help | Former docs-section | P1 |

---

## URL Structure (Next.js App Router)

```
/                          → redirect to /today
/today                     → Today space
/agents                    → Agents & Automation (default: fleet)
/agents/workflows
/agents/dispatch
/agents/cron
/agents/nightly
/create                    → Create space
/create/content
/knowledge                 → Knowledge space
/wealth                    → Wealth space
/life                      → Life space
/infrastructure            → Infrastructure space
/infrastructure/services
/infrastructure/logs
/insights                  → Insights space
/system                    → System space
/system/settings
/system/plugins
```

---

## Command Palette Actions

| Category | Examples |
|----------|----------|
| Navigate | "Go to Today", "Go to Dispatch" |
| Create | "Create workflow", "Enqueue dispatch", "Capture idea" |
| Run | "Run cron job", "Refresh all", "Send summary" |
| Search | "Search stock research", "Find failed runs" |
| AI | "Ask: what failed last night?" |

---

## Widget Registry (Plugin Model)

Each module can register widgets for **Today** and **Insights**:

```json
{
  "id": "contentforge-queue",
  "space": "create",
  "module": "content-studio",
  "todayWidget": true,
  "component": "@hermes/plugin-content/QueueWidget",
  "dataEndpoint": "/api/v1/content/queue",
  "refreshInterval": 60
}
```

Today layout = default widgets + user-pinned plugins.

---

## Migration Map (V1 → V2)

| V1 Section | V2 Destination |
|------------|----------------|
| home | Today |
| runs-section | Agents → (runs in Insights timeline too) |
| workflows-section | Agents → Workflows |
| dispatch-section | Agents → Dispatch |
| agents-section | Agents → Fleet |
| tasks-section | Today agenda + Life → Tasks |
| services-section | Infrastructure → Services |
| logs-section | Infrastructure → Logs |
| nightly-section | Agents → Nightly (automated) |
| cron-section | Agents → Cron |
| docs-section | System → Help |

---

*Next: [07-design-system.md](./07-design-system.md)*
