# 04 — Competitor & Industry Benchmark

**Research date:** June 2026  
**Purpose:** Extract patterns, not copy products

---

## 1. AI Agent Orchestration

### LangGraph Studio
| Pattern | Extract for Hermes OS |
|---------|----------------------|
| Real-time graph visualization | Workflow span-tree in Agents space |
| Time-travel debugging | Dispatch history with rerun-from-step |
| Interrupt before tool calls | Human-in-the-loop approval gates (already have medium-risk) |
| State editing mid-run | Manual output injection (already have) |

### CrewAI AMP
| Pattern | Extract |
|---------|---------|
| Unified control plane | Single Today + Agents surface |
| Tracing & observability | Per-dispatch token/cost/latency |
| Role-based agents | Profile cards with SOUL.md (already have) |

### AutoGen Studio
| Pattern | Extract |
|---------|---------|
| Drag-and-drop team canvas | Future: visual workflow builder |
| Message flow between agents | Workflow subtask timeline |

### Headless UI Libraries
| Library | Use |
|---------|-----|
| agent-prism | Span tree for dispatch/workflow traces |
| agenttrace-react | Approval gates, status dashboards |
| agent-observability-ui | shadcn metrics, transcripts |

**Verdict:** Use LangGraph-style trace trees + existing dispatch engine. Don't rebuild orchestration.

---

## 2. Developer Experience Tools

### Linear
| Pattern | Extract |
|---------|---------|
| ⌘K command palette | **Already have** — enhance with fuzzy search all spaces |
| Sidebar dims after nav | Adopt in V2 shell |
| Keyboard shortcut on every palette item | Add |
| Warm neutral tones | Calm Command already aligned |
| Progressive customization | Start with Today; add widgets over time |

### Vercel
| Pattern | Extract |
|---------|---------|
| Dense deployment lists by environment | Group cron jobs by tag (#content, #finance) |
| Branch + commit at a glance | Run metadata: profile, trigger, duration |
| Status per deployment | Status badge per agent/cron |

### Raycast
| Pattern | Extract |
|---------|---------|
| Extension/plugin model | **Plugin registry for Hermes OS** |
| Instant search everywhere | Semantic search + ⌘K |
| Quick actions | Today quick-action bar |

### Cursor
| Pattern | Extract |
|---------|---------|
| AI chat integrated in shell | Global AI chat bar (⌘J) |
| Context-aware suggestions | Recommendations on Today surface |
| Command palette for everything | Unified palette |

### Superhuman
| Pattern | Extract |
|---------|---------|
| Speed as feature | <200ms page transitions, optimistic UI |
| Keyboard-first triage | Triage needs-attention with j/k |

---

## 3. Observability & Ops

### Grafana / Datadog
| Pattern | Extract |
|---------|---------|
| Aggregate health top, trends middle, tables bottom | Today layout hierarchy |
| Click spike → jump to logs | Alert → drawer with logs |
| Template variables | Space-level filters |
| North Star metrics top-left | Briefing metric cards |

### Temporal
| Pattern | Extract |
|---------|---------|
| Compact / Timeline / History views | Dispatch detail 3-tab view |
| Pending activities at top | Needs-attention section |
| Event groups with colored dots | Timeline steps (already have) |

### Langfuse / Helicone
| Pattern | Extract |
|---------|---------|
| usage_details + cost_details per generation | LLM analytics module |
| Filter traces by tenant/feature | Filter by profile/workflow |
| Proxy-based cost capture | Middleware on Hermes dispatch |
| Prompt versioning | Prompt library in Agents space |

### Sentry
| Pattern | Extract |
|---------|---------|
| Issue grouping + recommended event | Group failures by failure_reason |
| Breadcrumbs timeline | Workflow event log |
| Stack trace with context | stderr tail + fix-prompt generator (have) |

---

## 4. Personal OS & Life Dashboards

### Life OS (Sebastián Aliaga)
| Pattern | Extract |
|---------|---------|
| Warm structured design | Calm Command alignment |
| Home as execution surface | **Today space** |
| Stat row + today list + daily plan panel | Briefing layout |
| Learning module with scroll-sync | Learning Hub plugin |

### Eidetic OS / Atlas
| Pattern | Extract |
|---------|---------|
| Vault → searchable AI knowledge base | Knowledge space + pgvector |
| 7 live panels dashboard | Widget registry model |
| Nightly autonomous agents | **Nightly DAG** |
| D3 knowledge graph | Knowledge Graph module |

### LifeOS-OSS (Obsidian)
| Pattern | Extract |
|---------|---------|
| 14 specialized agents ("The Cabinet") | Profile fleet |
| Dataview dashboards | Insights analytics |
| Nested feedback loops (daily→yearly) | Today → Insights rollup |

### How to Think AI — Life Dashboards
| Pattern | Extract |
|---------|---------|
| 3–4 domains max initially | Ship Today with 4 domain cards |
| One honest signal per domain | Metric cards: agents, content, stocks, learning |
| Weekly synthesis sentence | Insights weekly report |

---

## 5. Homelab & Infrastructure Dashboards

### Homepage (gethomepage.dev)
| Pattern | Extract |
|---------|---------|
| YAML/config-driven widgets | Plugin manifest JSON |
| 100+ service widgets | Per-service health cards |
| Docker label auto-discovery | Auto-register Hermes services |

### Homarr
| Pattern | Extract |
|---------|---------|
| Drag-and-drop widget editor | Future: customizable Today layout |
| Built-in auth (OIDC) | Tailscale + session auth |

### Glance
| Pattern | Extract |
|---------|---------|
| Feed-first briefing page | Today surface inspiration |
| RSS, weather, markets panels | External feed widgets on Today |
| Lightweight single binary | Keep API lean |

### OliveTin
| Pattern | Extract |
|---------|---------|
| Run shell scripts from web button | Quick actions on Today |
| Action buttons with confirmation | Safe action model (have) |

---

## 6. Content & Automation

### n8n / Flowise / Langflow
| Pattern | Extract |
|---------|---------|
| Visual workflow builder | Future Phase 5+ |
| Node-based automation | Nightly DAG as declarative YAML |

### Open WebUI
| Pattern | Extract |
|---------|---------|
| Multi-model chat interface | Global AI chat |
| RAG over documents | Semantic search |

---

## 7. Synthesis — What Hermes OS Should Steal

### Must Include (from benchmark)
1. **Today briefing** (Glance + Life OS + Eidetic)
2. **⌘K palette** (Linear + Raycast) — enhance
3. **Span-tree traces** (LangGraph + agent-prism)
4. **Plugin/widget registry** (Homepage + Raycast extensions)
5. **SSE streaming** (Langfuse + Temporal live)
6. **Cost per dispatch** (Langfuse + Helicone)
7. **Needs-attention triage** (Superhuman + Sentry)
8. **Global AI chat** (Cursor + Open WebUI)
9. **Nightly autonomous pipeline** (Eidetic + Airflow DAG)
10. **Knowledge graph** (Eidetic D3 viewer)

### Avoid
- Drag-and-drop workflow builder in v1 (n8n complexity)
- 100 widgets on day one (Homepage trap)
- Gamification (Life OS Dashboard competitor noise)
- Multi-tenant RBAC before single-user works

---

## 8. Competitive Position

Hermes OS is **not competing** with Linear, Notion, or Grafana individually.

It is the **meta-layer** that:
- Coordinates your AI agent fleet (like CrewAI control plane)
- Surfaces your daily life/work briefing (like Life OS)
- Monitors your infrastructure (like Homepage)
- Provides AI-native interaction (like Cursor)

**Unique moat:** Deep integration with Hermes CLI profiles, cron ecosystem, and personal domains — no SaaS can replicate your exact stack.

---

*Next: [05-vision.md](./05-vision.md)*
