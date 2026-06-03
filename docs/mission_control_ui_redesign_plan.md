# Mission Control UI Redesign Plan

Based on research in `docs/ui_research_mission_control.md`
Implementation target: `9ce67a2` baseline

## Overview

Transform Mission Control from a functional admin panel into a modern AI operations cockpit. Single-page app with sidebar navigation, drawer detail views, and a calm, intentional visual language.

## Visual Style

### Color System
```
--bg-base:      #090b0f    (deepest background)
--bg-surface:   #111318    (card backgrounds)
--bg-elevated:  #171a22    (drawers, modals)
--bg-sidebar:   #0c0e13    (sidebar, slightly dimmer)
--border:       #1e2230    (soft borders)
--border-hover: #2a3040    (hover state)

--text-primary: #e8ecf4    (main text)
--text-secondary: #8892a8  (labels, meta)
--text-muted:    #555d70   (disabled, hints)

--accent:       #4da6ff    (primary actions, links)
--accent-dim:   #3a7ecc    (hover/active)

--status-ok:    #34d399    (healthy, succeeded)
--status-warn:  #f59e0b    (degraded, in-progress)
--status-error: #ef4444    (failed, critical)
--status-info:  #60a5fa    (running, neutral)
--status-idle:  #6b7280    (queued, idle)

--severity-error-bg: #ef444410
--severity-warn-bg:  #f59e0b10
```

### Typography
Single font family: system-ui stack (fast, no downloads)
```
--font-sans: ui-sans-serif, system-ui, -apple-system, sans-serif
--font-mono: ui-monospace, 'Cascadia Code', 'Fira Code', monospace
```

Sizes: 11px (meta), 12px (body), 13px (labels), 14px (cards), 16px (headings), 20px (section titles)

### Spacing Scale
4px, 8px, 12px, 16px, 20px, 24px, 32px, 48px

### Corner Radius
6px (small), 10px (cards), 14px (modals), 999px (badges, pills)

## Layout System

### App Shell
```
┌──────────┬──────────────────────────────────────────┐
│ SIDEBAR  │ TOP BAR (search, profile, refresh)        │
│ 220px    ├──────────────────────────────────────────┤
│ fixed    │ CONTENT AREA                             │
│          │ scrollable, max-w 1200px, centered       │
│ dim bg   │                                          │
│          │ ┌─ Section Header ───────────────────┐   │
│ icon+txt │ │ Title          [action button]     │   │
│ 10 items │ └────────────────────────────────────┘   │
│          │ ┌─ Cards Grid ─┐ ┌─ Cards Grid ─┐       │
│  footer  │ │              │ │              │       │
│ status   │ └──────────────┘ └──────────────┘       │
└──────────┴──────────────────────────────────────────┘
```

### Sidebar
- Background: darker than content area
- Width: 220px, fixed position
- Items: icon + label, 10px padding, 10px gap
- Active item: subtle highlight (accent border-left + tinted bg)
- Hover: slight bg lighten
- Footer: pulse dot + "Action-capable" status + action safety classification
- Collapsible on mobile (hamburger or bottom tab bar)

### Top Bar
- Height: 48px
- Left: search input (⌘K hint)
- Center: profile mode selector
- Right: refresh button, send summary button
- Subtle bottom border

### Content Area
- Max width: 1200px
- Centered with auto margins
- Vertical scroll with padding
- Section spacing: 32px between sections

## Navigation Model

### Primary: Sidebar
1. ⌂ Home (Command Center)
2. ⏵ Runs
3. 🔄 Workflows
4. ◈ Agents
5. ▦ Tasks
6. ▣ Services
7. ☰ Logs
8. ☾ Nightly
9. ⏱ Cron
10. ? Docs

### Secondary: Command Palette (Cmd+K)
- Fuzzy search across all actions
- "Create workflow" → prompts for title
- "View logs mission-control" → jumps to logs with service pre-selected
- "Dispatch subtask" → opens workflow dispatch
- "Go to runs" → navigates to Runs section
- Keyboard shortcut next to each item

### Tertiary: Drawer Navigation
- Click run/workflow card → detail drawer slides from right
- Drawer: 480px wide, overlay backdrop
- Close: X button, Escape key, click backdrop

## Information Architecture

### 1. Home (Command Center)
**Purpose**: "What needs Kishore's attention right now?"

Layout (top to bottom):
1. Health Summary Bar — 5 service dots + status label
2. Alert Banner (if critical issues)
3. Metric Cards Row (4 cards): Running, Failed, Needs Review, Pending Approvals
4. Running Now — horizontal scroll of active run cards
5. Recent Failures — compact list (last 5)
6. Needs Attention — mixed: blocked workflows + failed crons + degraded services
7. Quick Actions — 4 large icon buttons: Create Workflow, Test Adapter, Refresh All, Send Summary
8. Recent Activity — chronological feed of actions, runs, Telegram updates

### 2. Runs
**Purpose**: "What executed, what failed, what's running?"

Layout:
1. Filter bar: All | Active | Succeeded | Failed | Needs Review
2. Search within runs
3. Run cards grid (3 columns)
4. Click → Run Detail Drawer

Run Detail Drawer:
- Header: title + status badge
- Meta grid: run_id, profile, confidence, duration, timestamps
- Steps timeline (vertical, color-coded)
- Logs section (collapsed by default)
- Output section
- Error section (highlighted if present)
- Telegram updates
- Actions: Retry, Copy JSON, View Related Workflow

### 3. Workflows
**Purpose**: "What multi-profile workflows are active?"

Layout:
1. Create Workflow button (prominent)
2. Workflow cards (2 columns)
3. Click → Workflow Detail Drawer

Workflow Card:
- Title + status badge
- Profile pipeline (A → B → C)
- Progress bar
- Subtask status dots
- Actions: Start, Pause, Synthesize

Workflow Detail Drawer:
- Meta: coordinator, mode, progress
- Subtask timeline (vertical)
- Each subtask: profile badge, title, status, actions (Start, Complete, Fail, Retry, Reroute)
- Synthesis panel (if exists)
- Telegram updates

### 4. Agents (Profiles)
**Purpose**: "Which profiles are handling what?"

Layout:
1. Profile cards grid (3 columns, 2 rows)
2. Each card: avatar icon, name, SOUL.md status, active runs, routing accuracy
3. Click → Agent Detail Drawer

Agent Detail Drawer:
- SOUL.md summary
- Routing keywords
- Recent runs
- Task templates
- Actions: Test Routing, Reload, Edit Description

### 5. Tasks (Kanban)
**Purpose**: "What tasks are in flight?"

Layout:
1. 4-column board: In Progress | Needs Review | Scheduled | Archived
2. Drag-and-drop cards
3. Each card: title, assignee dropdown, priority badge, archive button
4. Click → Task Detail Drawer

### 6. Services
**Purpose**: "Is everything running?"

Layout:
1. Service cards grid (5 cards)
2. Each: name, type, port, status dot, systemd status, HTTP health
3. Actions per card: Open, Logs, Restart (if allowed)
4. Click → Service Detail Drawer

### 7. Logs
**Purpose**: "What do the logs say?"

Layout:
1. Service selector dropdown
2. Log viewer (monospace, terminal-style)
3. Severity highlighting
4. Actions: Refresh, Copy Error, Generate Fix Prompt

### 8. Nightly Builds
**Purpose**: "What experiments are in progress?"

Layout:
1. + Register Build button
2. Build cards grid
3. Each: name, status, checklist, screenshots, linked runs
4. Actions: Test, Good, Promote, Reject, Archive, Attach Screenshot

### 9. Cron
**Purpose**: "What automations are scheduled?"

Layout:
1. Review queue (if any)
2. Cron cards grid
3. Each: name, schedule, last/next run, status, delivery
4. Actions: Run, Pause/Resume, Output, Fix

### 10. Docs
**Purpose**: "What's documented?"

Layout:
1. Internal docs sections
2. Recent files list
3. Governance score
4. Cost tracker

## Interaction Patterns

### Keyboard Shortcuts
- ⌘K — Command palette
- Esc — Close drawer/modal
- R — Refresh data
- / — Focus search

### Loading States
- Skeleton cards (animated shimmer) for initial load
- Spinner for actions in progress
- "Loading…" text for inline loads

### Empty States
- Icon + message + CTA button
- Example: "No workflows yet" → "Create your first workflow"
- Never leave a blank section

### Error States
- Top banner for critical failures
- Inline error for section-level failures
- Retry button always available
- Last error message shown

### Confirmation Flows
- Safe actions: execute immediately, show toast
- Medium actions: approval code modal
- High actions: blocked (not available in UI)

### Toast Notifications
- Bottom-right, auto-dismiss 3s
- Success: green
- Error: red
- Info: accent

## Component System

All components use consistent BEM-style naming:

### Layout
- `.mc-shell` — outer grid container
- `.mc-sidebar` — fixed left panel
- `.mc-topbar` — top action bar
- `.mc-content` — scrollable main area
- `.mc-section` — titled content block
- `.mc-drawer` — slide-in detail panel
- `.mc-drawer-backdrop` — overlay behind drawer

### Data Display
- `.mc-metric` — single KPI card
- `.mc-card` — generic content card
- `.mc-badge` — status/type indicator
- `.mc-progress` — progress bar
- `.mc-timeline` — vertical event sequence
- `.mc-timeline-step` — single event in timeline

### Actions
- `.mc-btn` — base button
- `.mc-btn-primary` — main action
- `.mc-btn-danger` — destructive
- `.mc-btn-ghost` — minimal/no border
- `.mc-btn-icon` — icon-only

### Feedback
- `.mc-toast` — notification
- `.mc-skeleton` — loading placeholder
- `.mc-empty` — empty state
- `.mc-error` — error state

### Inputs
- `.mc-input` — text input
- `.mc-select` — dropdown
- `.mc-filter-bar` — horizontal chips
- `.mc-search` — search with icon

## Implementation Plan

### Phase 0: Branch and Baseline
Status: complete on branch `feat/ui-revamp`; tagged the pre-revamp baseline as `pre-ui-revamp` and verified the unchanged baseline with `VERIFY_OK`.

### Phase 1: Palette and Navigation Consistency
Status: complete. The command palette is hidden by default, `openPalette()`/`closePalette()` toggle both the palette and backdrop, and sidebar active state is driven by `navTo()` rather than static initial markup.

### Phase 2: Design-System Pass
Status: complete. Existing token names were preserved while values were retuned for clearer base/surface/elevated separation, dimmer sidebar/topbar chrome, tighter type sizing, tabular numerals across the UI, and warning/error badge glyphs on top of the existing dot-and-label pattern.

### Phase 3: Home Cockpit
Status: complete. Home now includes an operational verdict hero derived from status and service health signals, bento-style metric tiles, a service issue metric, and de-duplicated Needs Attention cards. Synthetic test records are hidden by default and can be revealed with the Show test data toggle.

### Phase 4: Execution Timelines
Status: complete. Workflow detail now orders pending/running work first and uses clearer colored timeline states. Dispatch cards and live detail include compact timeline markers, and stdout/stderr live output is collapsed by default behind details controls.

### Phase 5: Density and Width
Pending. Replace the fixed content max width with fluid responsive grids, tighten card padding, and polish empty/loading states while preserving the existing mobile bottom-bar breakpoint.

## Responsive Behavior

### Desktop (>900px)
- Full sidebar + content grid
- 2-3 column card grids
- Drawer detail views

### Tablet (600-900px)
- Collapsed sidebar (icons only, 56px)
- 1-2 column card grids
- Full-width drawers

### Mobile (<600px)
- Bottom tab bar (5 items: Home, Runs, WFs, Logs, More)
- 1 column cards
- Full-screen detail views
- Simplified interactions

## File Changes Expected

- `static/styles.css` — complete rewrite
- `static/index.html` — new shell, nav, sections
- `static/app.js` — new rendering, drawer, palette
- `docs/ui_research_mission_control.md` — research (done)
- `docs/mission_control_ui_redesign_plan.md` — this document
- `server.py` — unchanged (API stays the same)
