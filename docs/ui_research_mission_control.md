# Mission Control UI/UX Research

Research conducted: May 2026
Purpose: Study modern dashboard patterns before redesigning Mission Control

## 1. What Modern Dashboards Do Well

### AI/LLM Ops (LangSmith, Langfuse)

**Observations-First Data Model**
- Every operation is a first-class row, not buried inside a trace
- Filters + saved views make the data table immediately useful
- Trace-level context (user_id, session_id) propagated to all observations

**Run/Trace Detail**
- Input → steps → output → error — chronological with expandable sections
- Recommended event surfaced (most context-rich, not just latest)
- Cost + latency per step, per trace
- Real-time polling with pause button

**Dashboard Architecture**
- Prebuilt dashboards for common views (traces, LLM calls, cost, tools, feedback)
- Custom dashboards with chart builder
- Group by metadata, tags, run type
- Line + bar charts for trends
- Responsive widgets, resizable/movable

### Workflow Orchestration (Temporal, Airflow)

**Execution Visualization**
- Three views: Compact (linear), Timeline (clock-time), History (full tree)
- Event groups with colored dots: green=complete, red=failed, blue=running
- Lines connect related events; dashed lines for pending
- Child workflow timelines viewable inline
- Pending activities surfaced at top, not hidden

**Navigation Patterns**
- Namespace/project switcher at top
- Saved views with one-click apply
- Task failures view as predefined saved view
- Tabs: Overview, Grid, Graph, Runs, Tasks, Events, Code, Details

**Grid View (Airflow)**
- Heatmap of task states across recent runs
- Click any cell → see task instance details
- Visual debugging of failure paths

### Observability (Grafana, Datadog)

**Information Hierarchy**
- Top: aggregate health (Critical/Warning/OK)
- Middle: trend charts (latency, errors, throughput)
- Bottom: deep-dive tables and logs
- Consistent color: green=OK, yellow=warning, red=critical

**Service Health**
- Multiple signals combined: monitors + incidents + anomaly detection
- Watchdog insights carousel for anomalies
- Summary cards: deployments, SLOs, incidents, security

**Dashboard Principles**
- Single pane of glass for operators
- Template variables for dynamic filtering
- Click spike → jump to relevant logs
- Deployment markers on timeline charts
- North Star metrics top-left

### Modern SaaS (Linear, Vercel, Railway)

**Linear's Approach**
- Command palette (Cmd+K) — fuzzy finder for every action
- Sidebar dims after navigation to let content take focus
- Tabs compact, not full-width
- Borders softened, structure felt not seen
- Warm neutral tones, less saturated accents
- Progressive customization (start simple, grow complex)
- Keyboard shortcuts shown next to every command palette item

**Vercel's Approach**
- Dense deployment lists grouped by environment
- Branch + commit visible at a glance
- Mobile-responsive list layouts
- Clear status indicators per deployment

**Railway's Approach**
- Project Canvas: visual map of services and connections
- Real-time collaborative view
- Deployment lifecycle: Initializing → Building → Deploying → Active/Failed
- Terminal-style log viewer with severity highlighting
- Singleton deploy pattern

### Error Tracking (Sentry)

**Issue Detail Layout**
- Header: error message, count, affected users, assign/resolve actions
- Event graph: distribution over time, filterable
- Search bar to narrow to specific event
- Stack trace with code context
- Breadcrumbs timeline leading to error
- Trace preview inline
- Tags in sidebar (issue-level) and main (event-level)
- Activity/comments sidebar (collapsible)
- Replay preview if available
- Screenshot attachments

**New Pattern: Flattened Navigation**
- Tabs replaced by expandable fold sections
- Everything visible at once, collapsed by preference
- Jump links between sections
- Event navigator moved into section header

## 2. Common Layout Patterns

### Shell Pattern (90% of tools)
```
┌──────────────────────────────────┐
│ Sidebar  │  Header (search, actions) │
│ (nav)    │──────────────────────────│
│          │  Content Area             │
│          │  (scrollable)             │
│          │                          │
│          │                          │
│ footer   │                          │
└──────────────────────────────────┘
```

### Detail Panel Pattern
- Main list/table on left
- Click item → detail panel slides in from right
- OR: expandable rows inline
- Detail stays in context, no page navigation

### Dashboard Pattern
- Top: summary metrics (4-8 cards)
- Middle: main charts (timeline, status)
- Bottom: lists/tables (recent items, errors)
- Filters affect all widgets

## 3. Navigation Patterns

### Primary Patterns Used
1. **Sidebar** — Linear, Grafana, Datadog, LangSmith, Airflow
2. **Top tabs** — Sentry (being replaced), Temporal
3. **Command palette** — Linear, Vercel, Railway
4. **Breadcrumbs** — sentry for issue → event navigation

### Best Practice
- Sidebar for primary navigation (5-10 items)
- Command palette for power users (Cmd+K)
- Tabs for sub-navigation within a view
- Breadcrumbs for deep hierarchy

## 4. Action Patterns

### Safety Classification (Universal)
- **Read/view** — always available, no confirmation
- **Create/draft** — single click, no confirmation
- **Modify/update** — inline edit or confirm
- **Delete/destroy** — confirmation dialog with typing required
- **Deploy/restart** — confirmation + audit log

### Action Placement
- Primary actions: visible buttons on cards/headers
- Secondary actions: dropdown menu (⋯)
- Destructive actions: separated, red-tinted, confirm
- Bulk actions: select → action bar appears

## 5. Status and Health Patterns

### Universal Color Language
- 🟢 Green = healthy, running, succeeded
- 🟡 Yellow/Orange = warning, degraded, in progress
- 🔴 Red = failed, critical, error
- ⚪ Gray = unknown, pending, idle
- 🔵 Blue = info, neutral, running (some tools)

### Status Display
- Dot + label (most common)
- Badge with count
- Progress bar for multi-step
- Timeline dot for history
- Animated pulse for live/running

### Health Summary
- Aggregate card: "3 critical, 2 warning, 12 healthy"
- Click to filter list by status
- Auto-refresh with manual refresh option

## 6. Workflow/Run Tracking Patterns

### Temporal's Three Views (Most Sophisticated)
1. **Compact**: Linear event groups, same-time stacked vertically
2. **Timeline**: Clock-time durations as line lengths, live updating
3. **History**: Git-tree style, all events connected

### Airflow's Grid View
- Tasks as rows, runs as columns
- Color-coded cells for quick scanning
- Click cell → task instance details

### Run Card Pattern (Common)
- Title + status badge
- Duration, started/finished
- Trigger source
- Profile/assignee
- Expand for details (logs, output, error)
- Actions: retry, cancel, view details

### Trace View (AI Ops)
- Chronological steps with expand/collapse
- Each step: input → processing → output
- Latency per step
- Token count / cost per LLM call
- Nested traces for sub-agents

## 7. Log Viewing Patterns

### Best Practices
- Terminal-style monospace viewer
- Severity highlighting (INFO/WARN/ERROR)
- Auto-scroll with pause button
- Search/filter within logs
- Copy button for error lines
- "Generate fix prompt" from error
- Link to related run/workflow

### Severity Colors
- ERROR: red background tint
- WARN: yellow/orange
- INFO: default
- DEBUG: muted/gray

## 8. Error Handling Patterns

### Sentry's Approach (Gold Standard)
- Error grouped into issues (dedup)
- Issue detail: header → graph → stack trace → breadcrumbs → tags
- Recommended event (most context-rich)
- Event navigator (prev/next within issue)
- Related issues from same trace
- Activity timeline (who viewed, commented, resolved)

### Dashboard Error States
- Error banner for top-level failures
- Inline error for widget-level failures
- Retry button with last error message
- Graceful degradation (show what you can)

## 9. Profile/Agent Orchestration UI Patterns

### Emerging Patterns (AI Agent Tools)
- Agent name + status dot (idle/busy/error)
- Active run count badge
- Recent runs list with status
- Configuration snippet (collapsed)
- Test/validate button
- Routing confidence indicator
- Manual override toggle

### Multi-Agent Patterns
- Parent workflow card with progress bar
- Subtask list with profile badges
- Dependency arrows or lines
- Sequential pipeline visualization
- Parallel execution indicators

## 10. What Should Be Copied as Inspiration

### Must Include
- **Command palette** (Linear-style) — Cmd+K for all actions
- **Sidebar navigation** — 8-12 items, dims when not active
- **Service health summary** — aggregate card with color dots
- **Run timeline view** — Temporal-inspired compact timeline
- **Workflow progress bars** — per-workflow completion
- **Log viewer with severity** — terminal-style with pause
- **Error detail with breadcrumbs** — chronological context
- **Saved views / filters** — for runs, workflows, tasks
- **Status colors consistent** — green/yellow/red/blue/gray
- **Detail panels not page jumps** — slide-in drawer
- **Toast notifications** — non-blocking confirmations

### Nice to Include
- **Project Canvas** (Railway-inspired) — visual service map
- **Grid view** (Airflow-inspired) — task status heatmap
- **Inline child timeline** (Temporal-inspired) — drill into subtasks

## 11. What Should Be Avoided

### Anti-Patterns
- Too many borders creating visual clutter
- Random/arbitrary colors for status
- Page jumps for details (use drawer/expand)
- Huge blocks of unformatted text
- Inconsistent button styles
- Weak status indicators (tiny dots, no labels)
- No empty states (confusing blanks)
- No loading states (users think it's broken)
- Everything at same visual weight (no hierarchy)
- Sidebar competing with content for attention
- Excessive animations that slow down operators
- Dark mode that's too dark (loss of contrast)

## 12. Recommended UI Direction for Mission Control

### Visual Identity
**"Calm command"** — Inspired by Linear's philosophy: structure felt, not seen.

- Dark-first with warm neutral base (#0a0b0f → #141620 → #1a1d2b)
- Single accent color (electric blue/cyan) used sparingly
- Soft borders (1px, low opacity) not hard lines
- Content area is the hero; sidebar recedes
- Typography: one font family, 3-4 weights
- Icons: consistent style, used for recognition not decoration

### Layout System
```
┌──────────┬─────────────────────────────────────┐
│ Sidebar  │ Top Bar (search ⌘K, profile mode,   │
│ (dim bg) │           refresh, send summary)     │
│          ├─────────────────────────────────────┤
│ ⌂ Home   │  [Health Summary Cards — 4-6]       │
│ ⏵ Runs   │                                     │
│ 🔄 WFs   │  [Running Now — horizontal scroll]  │
│ ◈ Agents │                                     │
│ ▦ Tasks  │  [Recent Failures / Needs Attention] │
│ ▣ Svcs   │                                     │
│ ☰ Logs   │  [Quick Actions — 4 buttons]        │
│ ☾ Nightly│                                     │
│ ⏱ Cron   │  [Recent Activity Feed]             │
│ ? Docs   │                                     │
└──────────┴─────────────────────────────────────┘
```

### Navigation Model
- **Sidebar**: 10 items, dim background, icons + labels
- **Cmd+K**: command palette for all actions ("create workflow", "view logs", "dispatch subtask", "go to runs")
- **Top bar**: search, profile mode selector, refresh, send summary
- **Detail views**: slide-in drawer from right

### Information Architecture
1. **Home (Command Center)** — health summary, running now, needs attention, quick actions
2. **Runs** — run history, filters, run detail drawer
3. **Workflows** — multi-profile workflows, subtask timeline, synthesis view
4. **Agents/Profiles** — 6 profiles, status, active runs, routing accuracy
5. **Tasks/Kanban** — board view, drag-drop, profile assignment
6. **Services** — 5 services, health, logs, restart
7. **Logs** — log explorer with severity filter
8. **Nightly Builds** — experiment lab, promotion workflow
9. **Automations/Cron** — scheduled jobs, run/pause/resume
10. **Docs** — internal docs, research, roadmap

### Component Library
Every component designed once, used everywhere:
- `mc-badge` — status indicator (color + label)
- `mc-card` — container with consistent padding/border
- `mc-section` — titled section with optional action button
- `mc-timeline` — vertical/horizontal event sequence
- `mc-drawer` — slide-in detail panel
- `mc-toast` — non-blocking notification
- `mc-skeleton` — loading placeholder
- `mc-empty` — empty state with illustration + CTA
- `mc-progress` — progress bar with label
- `mc-filter-bar` — horizontal filter chips
- `mc-action-btn` — primary/secondary/danger variants
