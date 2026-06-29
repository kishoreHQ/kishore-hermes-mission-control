# 02 — UX Review & Design Audit

**Scope:** Current Mission Control UI + prior redesign research  
**References:** `docs/ui_research_mission_control.md`, `docs/mission_control_ui_redesign_plan.md`

---

## 1. UX Review — Current State

### What Works

| Pattern | Assessment |
|---------|------------|
| Command palette (⌘K) | Good — fuzzy action finder, keyboard-first |
| Drawer detail views | Good — no page jumps, context preserved |
| Operations cockpit (Home) | Good — verdict hero, bento metrics, needs-attention |
| Safety classification UI | Good — safe/medium/high visible in sidebar footer |
| Status color language | Consistent — green/yellow/red/blue/gray |
| Mobile bottom bar | Present — 5-item nav at <900px |
| Empty states | Improved in Phase 5 — icon + message + CTA |
| Timeline views | Workflow/dispatch timelines with colored states |

### What Fails

| Problem | Impact | Severity |
|---------|--------|----------|
| **Ops-only mental model** | Home answers "what's broken?" not "what should I do today?" | Critical |
| **11 flat nav items** | Cognitive overload; no domain grouping | High |
| **30s polling** | Feels stale; no live dispatch streaming | High |
| **Stubbed search** | Search bar is decorative | High |
| **No daily briefing** | Nothing compels morning open | Critical |
| **No AI interaction** | Dashboard doesn't feel AI-native | Critical |
| **Profile mode in top bar** | Ops concept, not user-facing | Medium |
| **Docs as nav item** | Governance buried; should be contextual help | Low |
| **Synthetic test data toggle** | Dev artifact exposed in production UI | Medium |
| **Browser `prompt()` for approval** | Weak UX and security for medium-risk actions | High |

### Workflow Audit — Daily Use

**Morning (current):** Open MC → see ops verdict → check failures → maybe trigger cron. **Missing:** briefing, agenda, content ideas, investment updates, learning suggestions, AI news.

**Day (current):** Monitor runs/workflows/dispatch. **Missing:** task prioritization, quick capture, cross-domain search.

**Night (current):** Nightly section is manual build tracker. **Missing:** automated pipeline status, morning report preview, artifact review.

**Verdict:** Current UX serves **operators debugging automation**, not **a person running their life and work**.

---

## 2. Design Audit — "Calm Command" System

### Strengths (Keep in V2)

```
Color tokens (from mission_control_ui_redesign_plan.md):
--bg-base:      #090b0f
--bg-surface:   #111318
--bg-elevated:  #171a22
--accent:       #4da6ff
--status-ok:    #34d399
--status-warn:  #f59e0b
--status-error: #ef4444
```

- Dark-first, warm neutrals (not cold high-contrast)
- Single accent (electric blue) used sparingly
- Soft 1px borders, structure felt not seen
- Tabular numerals for metrics
- Monospace for logs
- Spacing scale: 4/8/12/16/20/24/32/48px
- Corner radius: 6/10/14/999px

### Weaknesses (Fix in V2)

| Issue | Fix |
|-------|-----|
| system-ui font only | Add Inter/Geist via `next/font` |
| No design tokens package | Extract to `packages/ui` shadcn theme |
| No component Storybook | Add for `packages/ui` |
| No motion system | Add Framer Motion for drawer/palette |
| No loading skeletons everywhere | Standardize `Skeleton` component |
| No reduced-motion support | Add `prefers-reduced-motion` |
| Icon inconsistency | Standardize on Lucide |
| No light mode | Optional; dark-first is correct |

### Comparison to Inspiration Products

| Product | What MC Has | What MC Lacks |
|---------|-------------|---------------|
| **Linear** | Command palette, sidebar | Issue-centric views, keyboard shortcuts on every action |
| **Vercel** | Deployment-like status cards | Environment grouping, commit/branch context |
| **Raycast** | ⌘K palette | Extension model, instant search everywhere |
| **Superhuman** | — | Speed, keyboard-first email-like triage |
| **Notion** | Kanban tasks | Block editor, databases, templates |
| **Grafana** | Health summary, log viewer | Custom dashboards, template variables, drill-down |
| **Temporal** | Workflow timelines | Compact/Timeline/History three views |
| **Langfuse** | Run history | Token/cost per step, trace trees, eval |

---

## 3. Navigation Redesign (V2)

### Current (11 flat items)

Home · Runs · Workflows · Dispatch · Agents · Tasks · Services · Logs · Nightly · Cron · Docs

### Proposed (9 Spaces)

| Space | Modules | Default Landing |
|-------|---------|-----------------|
| **Today** | Briefing, agenda, alerts, nightly report, recommendations | **Yes** |
| **Agents & Automation** | Fleet, Workflows, Dispatch, Cron, Nightly, Prompts, LLM Analytics | |
| **Create** | Content Studio, Video Pipeline, Publishing | |
| **Knowledge** | Research Lab, Knowledge Graph, Learning Hub, Docs, Memory | |
| **Wealth** | Finance Hub, Stock Dashboard, Investing | |
| **Life** | Goals, Habits, Journal, Calendar, Career, Health | |
| **Infrastructure** | Servers, Services, Logs, System Health | |
| **Insights** | Reports, Analytics, Timeline, Activity Feed | |
| **System** | Settings, Plugins, Workspaces, Search | |

### Navigation Model

1. **Primary:** Left sidebar — 9 spaces, icon + label
2. **Secondary:** Space sub-nav (tabs or secondary sidebar)
3. **Global:** Command palette (⌘K) — jump anywhere, run actions
4. **Global:** AI chat bar (⌘J or floating) — ask dashboard anything
5. **Tertiary:** Right drawer — entity detail without leaving context

---

## 4. Dashboard Layout — Today Surface (Wireframe)

```
┌──────────┬──────────────────────────────────────────────────────┐
│ SIDEBAR  │ TOP BAR  [⌘K Search]  [AI Chat]  [Refresh] [Profile] │
│ 9 spaces ├──────────────────────────────────────────────────────┤
│          │  Good morning, Kishore.  Mon Jun 29 · 3 items need you │
│ Today ●  │                                                      │
│ Agents   │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐      │
│ Create   │  │ Nightly │ │ Agents  │ │ Content │ │ Stocks  │      │
│ ...      │  │ ✓ 12/14 │ │ 2 active│ │ 3 ideas │ │ NIFTY ▲ │      │
│          │  └─────────┘ └─────────┘ └─────────┘ └─────────┘      │
│          │                                                      │
│          │  NEEDS ATTENTION (3)                                  │
│          │  • StockPulse failed at 02:14 — [View] [Retry]        │
│          │  • ContentForge queue empty — [Generate ideas]        │
│          │  • Career Ops: 2 new matches — [Review]               │
│          │                                                      │
│          │  TODAY'S AGENDA          │  NIGHTLY REPORT (summary)   │
│          │  □ Review stock picks    │  AI tools researched: 4    │
│          │  □ Publish queued post   │  Learning roadmap updated  │
│          │  □ DevSecOps practice    │  Recommendations: 2        │
│          │                                                      │
│          │  QUICK ACTIONS  [Dispatch] [Run cron] [Capture idea] │
└──────────┴──────────────────────────────────────────────────────┘
```

---

## 5. Component Inventory (V2 Target)

### Layout
- `AppShell`, `Sidebar`, `TopBar`, `SpaceNav`, `ContentArea`, `Drawer`, `CommandPalette`, `AIChatBar`

### Data Display
- `MetricCard`, `BentoGrid`, `StatusBadge`, `ProgressBar`, `Timeline`, `TimelineStep`, `RunCard`, `WorkflowCard`, `AgentCard`, `ServiceCard`, `LogViewer`, `KanbanBoard`, `ActivityFeed`, `BriefingCard`

### Actions
- `Button` (primary/secondary/ghost/danger), `IconButton`, `ActionMenu`, `ApprovalModal`, `Toast`

### Feedback
- `Skeleton`, `EmptyState`, `ErrorBanner`, `LoadingSpinner`

### Inputs
- `SearchInput`, `Select`, `FilterBar`, `TagBadge`, `DatePicker`

### AI-Native
- `AskPanel`, `RecommendationCard`, `SemanticSearchResults`, `RCASummary`, `SpanTree` (agent trace)

---

## 6. Deletions (Do Not Preserve)

| Feature | Reason |
|---------|--------|
| Separate `mission-control-dashboard` repo | Diverged spec, never built |
| Inline dispatch code in server.py (lines ~2556–3087) | Dead code, shadowed by dispatch_engine |
| Browser `prompt()` approval | Replace with proper modal + TOTP/session |
| Docs as top-level nav | Move to contextual help / System space |
| Synthetic test data toggle in production | Dev-only flag behind env |
| 11-item flat sidebar | Replace with 9 Spaces |

---

*Next: [03-gap-analysis.md](./03-gap-analysis.md)*
