# 05 — Product Vision: Hermes OS

---

## Mission Statement

**Hermes OS is the single interface you open every morning — your personal AI operating system for life, work, learning, creation, investing, and automation.**

It is not an admin dashboard. It is not another Notion clone. It is the **coordination layer** between you and your AI workforce.

---

## Purpose

| Principle | Meaning |
|-----------|---------|
| **Remove repetitive work** | Nightly pipelines research, index, summarize, backup — you review |
| **Coordinate AI workforce** | 6+ Hermes profiles, 14+ cron jobs, workflows — one fleet view |
| **Automate life** | Morning briefing, content pipeline, stock alerts — proactive |
| **Help you think** | Ask-anything, semantic search, recommendations across domains |
| **Help you create** | Content studio, research lab, prompt library — creation flows |
| **Save time** | Command palette, quick actions, failure auto-RCA |

---

## What Hermes OS Is NOT

- Not a generic SaaS dashboard template
- Not a replacement for Obsidian, Linear, or Grafana (it integrates with them)
- Not a no-code workflow builder (v1)
- Not a multi-tenant product (v1 is personal, single-user)
- Not 45 modules on day one

---

## Target User

**Primary:** Kishore — solo operator of a Hermes agent fleet on a VPS, spanning content, finance, career, learning, infrastructure, and personal knowledge.

**Mental model:** Iron Man's JARVIS meets Linear's speed meets a Life OS briefing.

---

## Four Laws (Non-Negotiable)

### 1. Surface, Don't Store
The dashboard tells you what matters **now**. Raw data, logs, and archives live behind search and drawers. Today shows 3–7 items needing attention, not 300.

### 2. Coordinate the AI Workforce
Agents (profiles), workflows, dispatch, and cron are first-class. You steer; they execute. Status is always visible.

### 3. Automate the Repetitive
Every night at ~2 AM, Hermes runs pipelines: research, index, backup, generate ideas, update roadmaps, produce morning report. You wake up to results.

### 4. Help Me Think and Create
Natural language over everything. "What failed last night?" "Summarize my stock research." "Draft a post about Kubernetes." Context spans all domains.

---

## Domain Taxonomy

Organize life's complexity into **9 Spaces**:

```
┌─────────────────────────────────────────────────────────┐
│                    HERMES OS                             │
├─────────────┬─────────────┬─────────────┬───────────────┤
│   OPERATE   │   CREATE    │   KNOW      │   GROW        │
│ Today       │ Create      │ Knowledge   │ Wealth        │
│ Agents      │             │             │ Life          │
│ Infra       │             │             │               │
├─────────────┴─────────────┴─────────────┴───────────────┤
│   UNDERSTAND          │   CONFIGURE                      │
│ Insights              │ System                           │
└───────────────────────┴──────────────────────────────────┘
```

| Domain | Spaces | Core Question |
|--------|--------|---------------|
| **Operate** | Today, Agents & Automation, Infrastructure | What's running? What broke? |
| **Create** | Create | What am I making? |
| **Know** | Knowledge | What do I know? |
| **Grow** | Wealth, Life | How am I progressing? |
| **Understand** | Insights | What patterns emerge? |
| **Configure** | System | How is it set up? |

---

## Success Metrics

| Metric | Target (6 months) |
|--------|-------------------|
| Daily opens | ≥1/day (morning habit) |
| Time to morning clarity | <30 seconds on Today |
| Nightly pipeline success rate | ≥90% |
| Dispatch visibility latency | <2s (SSE) |
| Modules shipped | Today + Agents + 3 domain plugins |
| Manual cron triggers | ↓50% (automation handles it) |

---

## 10-Year Horizon

| Year | Capability |
|------|------------|
| Y1 | Personal OS: Today, Agents, Nightly, AI chat, 3 domain plugins |
| Y2 | Plugin marketplace, mobile PWA, multi-device sync |
| Y3 | Predictive insights, auto-workflow suggestions |
| Y4+ | Optional multi-user; API for third-party integrations |

---

## Relationship to Hermes Ecosystem

```
┌──────────────────────────────────────────┐
│              HERMES OS (UI)               │
│  Today · Agents · Create · Knowledge ...  │
└──────────────────┬───────────────────────┘
                   │ FastAPI Gateway
┌──────────────────▼───────────────────────┐
│         Hermes Core Services              │
│  Dispatch · Scheduler · AI · Search       │
└──────────────────┬───────────────────────┘
                   │
    ┌──────────────┼──────────────┐
    ▼              ▼              ▼
 Hermes CLI    Cron Jobs    External APIs
 (profiles)    (14+ jobs)   (stocks, RSS, etc.)
```

Hermes OS is the **face**. Hermes CLI + cron + pipelines are the **muscle**. Postgres/Redis are the **memory**.

---

*Next: [06-information-architecture.md](./06-information-architecture.md)*
