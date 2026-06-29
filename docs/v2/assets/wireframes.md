# Wireframes & Layout Mockups

ASCII wireframes for Hermes OS V2 key surfaces.

---

## 1. Today Surface (Default Landing)

```
┌──────────┬────────────────────────────────────────────────────────────┐
│ ⌂ Today  │  ⌕ Search…                              ⌘K    💬 AI   ↻      │
│ ◈ Agents │────────────────────────────────────────────────────────────│
│ ✎ Create │                                                            │
│ ◉ Know   │  Good morning, Kishore.                    Mon Jun 29, 2026 │
│ $ Wealth │  3 items need your attention                               │
│ ♡ Life   │                                                            │
│ ▣ Infra  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│ ◎ Insights│  │ Nightly  │ │ Agents   │ │ Content  │ │ Stocks   │       │
│ ⚙ System │  │ 12/14 ✓  │ │ 2 active │ │ 3 queued │ │ NIFTY ▲  │       │
│          │  └──────────┘ └──────────┘ └──────────┘ └──────────┘       │
│ ──────── │                                                            │
│ ● Online │  ⚠ NEEDS ATTENTION                                         │
│          │  ┌────────────────────────────────────────────────────┐    │
│          │  │ 🔴 StockPulse nightly failed · 02:14    [Logs][Retry]│    │
│          │  │ 🟡 ContentForge queue empty             [Generate]   │    │
│          │  │ 🔵 Career Ops: 2 new matches            [Review]     │    │
│          │  └────────────────────────────────────────────────────┘    │
│          │                                                            │
│          │  TODAY'S AGENDA              │  NIGHTLY REPORT (2:00 AM)    │
│          │  ☐ Review stock picks        │  • 4 AI tools researched     │
│          │  ☐ Publish queued post       │  • Learning roadmap updated    │
│          │  ☐ DevSecOps practice        │  • 2 content ideas generated │
│          │                              │  • Backup completed          │
│          │  QUICK ACTIONS                                               │
│          │  [+ Dispatch] [▶ Run Cron] [💡 Capture] [📤 Summary]        │
└──────────┴────────────────────────────────────────────────────────────┘
```

---

## 2. Agents — Dispatch Live View

```
┌──────────┬────────────────────────────────────────────────────────────┐
│ Agents ▶ │  Dispatch Queue                          [+ Enqueue]       │
│  Fleet   │────────────────────────────────────────────────────────────│
│  Workflows│  ACTIVE (2)                                                  │
│ ● Dispatch│  ┌─────────────────────────────────────────────────────┐   │
│  Cron    │  │ ● running  d-8f2a  Coder  "Fix auth middleware"      │   │
│  Nightly │  │   ████████░░ 72%  ·  4m 12s  ·  PID 48291            │   │
│          │  │   [Live Logs ▼] [Cancel]                            │   │
│          │  │   stdout: Applying patch to server.py...              │   │
│          │  └─────────────────────────────────────────────────────┘   │
│          │                                                            │
│          │  QUEUED (1)  ·  COMPLETED TODAY (8)  ·  FAILED (1)         │
│          │                                                            │
│          │  ┌─ Drawer: d-8f2a detail ─────────────────────────┐      │
│          │  │ Timeline: enqueued → starting → running           │      │
│          │  │ Profile: Coder · Retry: 0/3 · Timeout: 3600s      │      │
│          │  │ [Retry] [Manual Output] [Copy JSON]               │      │
│          │  └───────────────────────────────────────────────────┘      │
└──────────┴────────────────────────────────────────────────────────────┘
```

---

## 3. Command Palette (⌘K)

```
                    ┌─────────────────────────────────────┐
                    │ ⌕ Type a command or search…         │
                    ├─────────────────────────────────────┤
                    │ Navigate                            │
                    │   ⌂  Go to Today              g t   │
                    │   ◈  Go to Agents             g a   │
                    │   ⚡ Go to Dispatch                 │
                    ├─────────────────────────────────────┤
                    │ Actions                             │
                    │   +  Create workflow                │
                    │   +  Enqueue dispatch               │
                    │   ▶  Run cron: StockPulse           │
                    │   ↻  Refresh all                    │
                    ├─────────────────────────────────────┤
                    │ AI                                  │
                    │   💬 Ask: What failed last night?   │
                    └─────────────────────────────────────┘
```

---

## 4. Nightly Pipeline Status

```
┌──────────┬────────────────────────────────────────────────────────────┐
│ Nightly  │  Last run: Jun 29, 02:00 AM  ·  Duration: 47m  ·  12/14 ✓  │
│          │────────────────────────────────────────────────────────────│
│          │  PIPELINE DAG                                                │
│          │                                                            │
│          │  [Research AI tools]──────┐                                │
│          │  [Update learning]────────┼──► [Generate morning report]   │
│          │  [Stock research]─────────┤                                │
│          │  [Content ideas]──────────┤                                │
│          │  [Index knowledge]────────┤                                │
│          │  [Backup data]────────────┘                                │
│          │                                                            │
│          │  FAILURES                                                  │
│          │  🔴 StockPulse refresh — timeout after 600s  [RCA] [Retry] │
│          │                                                            │
│          │  ARTIFACTS (4)                                             │
│          │  📄 ai-tools-summary.md  📄 learning-roadmap.json          │
│          │  📄 content-ideas.json   📄 morning-report.md              │
│          │                                                            │
│          │  TREND (7 days)  ████████████░░ 86% success rate           │
└──────────┴────────────────────────────────────────────────────────────┘
```

---

## 5. Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                     BROWSER (Next.js)                            │
│  Today · Agents · Create · … · ⌘K · ⌘J · SSE client             │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTPS
┌────────────────────────────▼────────────────────────────────────┐
│                   FastAPI Gateway (:8000)                          │
│  /api/v1/*  ·  /api/v1/stream  ·  Auth  ·  OpenAPI              │
└──────┬─────────────────┬──────────────────┬────────────────────┘
       │                 │                  │
       ▼                 ▼                  ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  Dispatch    │  │  Scheduler   │  │  AI Service  │
│  (engine)    │  │  (nightly)   │  │  (ask/RAG)   │
└──────┬───────┘  └──────┬───────┘  └──────┬───────┘
       │                 │                  │
       └────────┬────────┴────────┬─────────┘
                ▼                 ▼
         ┌────────────┐    ┌────────────┐
         │  Postgres  │    │   Redis    │
         │  +pgvector │    │ queue/pub  │
         └────────────┘    └────────────┘
                │
                ▼
         ┌────────────┐
         │ Hermes CLI │
         │ + Cron     │
         └────────────┘
```

---

*Referenced from [07-design-system.md](../07-design-system.md)*
