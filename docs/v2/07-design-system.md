# 07 — Design System Proposal

**Codename:** Calm Command v2  
**Package:** `packages/ui` (shadcn/ui + Tailwind)

---

## Design Principles

1. **Dark-first** — Default theme; optional light later
2. **Structure felt, not seen** — Soft borders, receding chrome (Linear-inspired)
3. **Content is hero** — Sidebar dims; Today briefing dominates
4. **Keyboard-first** — Every action reachable via ⌘K
5. **Information dense, not cluttered** — Bento grids, tabular numerals
6. **Motion with purpose** — Drawer slide, palette fade; respect reduced-motion

---

## Color Tokens

```css
/* Surfaces */
--background:        222 47% 4%;    /* #090b0f */
--card:              222 41% 7%;    /* #111318 */
--popover:           222 35% 10%;   /* #171a22 */
--sidebar:           222 45% 5%;    /* #0c0e13 */

/* Text */
--foreground:        220 27% 93%;   /* #e8ecf4 */
--muted-foreground:  220 14% 58%;   /* #8892a8 */
--muted:             222 30% 12%;

/* Accent */
--primary:           211 100% 65%;  /* #4da6ff */
--primary-foreground: 222 47% 4%;

/* Status */
--success:           160 60% 52%;   /* #34d399 */
--warning:           38 92% 50%;    /* #f59e0b */
--destructive:       0 84% 60%;    /* #ef4444 */
--info:              213 94% 68%;   /* #60a5fa */

/* Borders */
--border:            222 25% 15%;   /* #1e2230 */
--ring:              211 100% 65%;
```

### Status Mapping

| State | Token | Use |
|-------|-------|-----|
| healthy, succeeded, ok | `--success` | Service up, cron ok |
| warning, degraded, in-progress | `--warning` | Retry, partial |
| failed, critical, error | `--destructive` | Dispatch fail |
| running, info | `--info` | Active dispatch |
| idle, pending, unknown | `--muted-foreground` | Queued |

---

## Typography

```css
--font-sans: 'Geist', ui-sans-serif, system-ui, sans-serif;
--font-mono: 'Geist Mono', ui-monospace, monospace;
```

| Scale | Size | Use |
|-------|------|-----|
| xs | 11px | Meta, timestamps |
| sm | 12px | Body, labels |
| base | 14px | Cards, inputs |
| lg | 16px | Section headings |
| xl | 20px | Page titles |
| 2xl | 24px | Briefing greeting |

`font-variant-numeric: tabular-nums` on all metrics.

---

## Spacing & Radius

**Spacing:** 4, 8, 12, 16, 20, 24, 32, 48 (Tailwind default)

**Radius:**
- `sm`: 6px — buttons, inputs
- `md`: 10px — cards
- `lg`: 14px — modals, drawers
- `full`: 999px — badges, pills

---

## Layout

### App Shell

```
┌──────────┬──────────────────────────────────────────┐
│ Sidebar  │ TopBar (48px)                             │
│ 240px    ├──────────────────────────────────────────┤
│ fixed    │ Main (max-w-7xl, px-6, py-8)             │
│          │                                           │
│ Spaces   │  [Space content]                          │
│          │                                           │
│ footer   │                                           │
└──────────┴──────────────────────────────────────────┘
```

- Sidebar: `w-60`, `bg-sidebar`, border-r
- Mobile (<768px): sidebar hidden, bottom tab bar (5 items: Today, Agents, Create, Insights, More)
- Drawer: `w-[480px]` right slide, backdrop `bg-black/50`

### Bento Grid (Today)

```css
.bento {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
}
```

---

## Component Inventory (shadcn mapping)

| Hermes Component | shadcn Base |
|------------------|-------------|
| `MetricCard` | `Card` + custom |
| `StatusBadge` | `Badge` variant |
| `CommandPalette` | `Command` (cmdk) |
| `Drawer` | `Sheet` |
| `LogViewer` | `ScrollArea` + mono |
| `Timeline` | Custom + `Separator` |
| `KanbanBoard` | Custom drag-drop |
| `Toast` | `Sonner` |
| `ApprovalModal` | `AlertDialog` |
| `Skeleton` | `Skeleton` |
| `EmptyState` | Custom |
| `AIChatBar` | `Sheet` or fixed bottom panel |

---

## Interaction Patterns

### Keyboard Shortcuts

| Key | Action |
|-----|--------|
| ⌘K | Command palette |
| ⌘J | AI chat |
| Esc | Close drawer/modal |
| R | Refresh current space |
| / | Focus search |
| g t | Go to Today |
| g a | Go to Agents |

### Loading
- Skeleton cards on initial load
- Optimistic updates for task move, dispatch enqueue
- Spinner on button during action

### Empty States
- Icon (Lucide) + message + primary CTA
- Never blank sections

### Error States
- Top `Alert` banner for critical
- Inline retry for section failures
- Toast for action errors

---

## Wireframes

See [assets/wireframes.md](./assets/wireframes.md) for ASCII mockups of:
- Today surface
- Agents dispatch live view
- Command palette
- Nightly pipeline status

---

## Accessibility

- WCAG 2.1 AA contrast on all text
- Focus rings on interactive elements
- `aria-label` on icon-only buttons
- `prefers-reduced-motion: reduce` disables drawer animation
- Skip link to main content

---

*Next: [08-target-architecture.md](./08-target-architecture.md)*
