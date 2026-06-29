import { apiFetch } from "./client";

export interface StatusHero {
  level: "operational" | "attention" | "action_required";
  summary: string;
  active_runs: number;
  services_monitored: number;
  enabled_crons: number;
}

export interface BentoMetrics {
  running: number;
  failed: number;
  review: number;
  blocked: number;
  workflows: number;
  cost_usd: number;
  tokens: number;
}

export interface RunningNowItem {
  id: string;
  name: string;
  type: string;
  progress: number;
  status: string;
}

export interface TodayData {
  greeting: string;
  date: string;
  updated_at?: string;
  attention_count: number;
  status_hero?: StatusHero;
  bento?: BentoMetrics;
  running_now?: RunningNowItem[];
  metrics: {
    nightly: { status: string; succeeded: number; total: number };
    agents_active: number;
    content_queued: number;
    stocks: { symbol: string; change: string };
  };
  attention: Array<{
    id: string;
    severity: string;
    title: string;
    actions: string[];
    action_targets?: Record<string, string>;
  }>;
  agenda: Array<{ id: string; title: string; done: boolean }>;
  nightly_report: { summary: string; artifacts: string[] };
  recommendations: Array<{ id: string; text: string }>;
  quick_actions: string[];
}

export const todayApi = {
  get: () => apiFetch<TodayData>("/api/v1/today"),
};

export const statusApi = {
  get: (heavy = true) => apiFetch<Record<string, unknown>>(`/api/v1/status?heavy=${heavy}`),
};

export const dispatchApi = {
  list: () => apiFetch<{ items: unknown[] }>("/api/v1/dispatch"),
  active: () => apiFetch<{ items: unknown[] }>("/api/v1/dispatch/active"),
  enqueue: (body: { profile: string; prompt: string; toolsets?: string }) =>
    apiFetch<{ ok: boolean; dispatch: unknown }>("/api/v1/dispatch/enqueue", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  cancel: (id: string) =>
    apiFetch<{ ok: boolean }>(`/api/v1/dispatch/${id}/cancel`, { method: "POST" }),
};

export const agentsApi = {
  profiles: () => apiFetch<{ items: unknown[] }>("/api/v1/profiles"),
  workflows: () => apiFetch<{ items: unknown[] }>("/api/v1/workflows"),
  workflowTimeline: (id: string) => apiFetch<{ items: unknown[] }>(`/api/v1/workflows/${id}/timeline`),
  tasks: () => apiFetch<{ items: unknown[] }>("/api/v1/tasks"),
  cron: () => apiFetch<{ items: unknown[] }>("/api/v1/cron"),
};

export const tasksApi = {
  list: () => apiFetch<{ items: unknown[] }>("/api/v1/tasks"),
  move: (id: string, lane: string) =>
    apiFetch<{ ok: boolean; task: unknown }>("/api/v1/tasks/move", {
      method: "POST",
      body: JSON.stringify({ id, lane }),
    }),
  archive: (id: string) =>
    apiFetch<{ ok: boolean; task: unknown }>("/api/v1/tasks/archive", {
      method: "POST",
      body: JSON.stringify({ id }),
    }),
};

export const infraApi = {
  services: () => apiFetch<{ items: unknown[] }>("/api/v1/services"),
  health: () => apiFetch<{ summary: string; items: unknown[] }>("/api/v1/services/health"),
  logs: (service: string) => apiFetch<{ content: string }>(`/api/v1/logs?service=${encodeURIComponent(service)}`),
  system: () => apiFetch<Record<string, unknown>>("/api/v1/system"),
};

export const nightlyApi = {
  latest: () => apiFetch<{ run: unknown }>("/api/v1/nightly/runs/latest"),
  trigger: () => apiFetch<{ run: unknown }>("/api/v1/nightly/trigger", { method: "POST" }),
  dag: () => apiFetch<unknown>("/api/v1/nightly/dag"),
};

export const aiApi = {
  ask: (message: string) =>
    apiFetch<{ answer: string }>("/api/v1/ai/ask", {
      method: "POST",
      body: JSON.stringify({ message }),
    }),
  recommendations: () => apiFetch<{ items: unknown[] }>("/api/v1/ai/recommendations"),
};

export const pluginsApi = {
  list: () => apiFetch<{ items: unknown[] }>("/api/v1/plugins"),
  todayWidgets: () => apiFetch<{ items: unknown[] }>("/api/v1/plugins/widgets/today"),
};

export const actionsApi = {
  prepare: (action: string, payload?: Record<string, unknown>) =>
    apiFetch<{ approval_id: string; approval_code?: string; auto_execute?: boolean }>(
      "/api/v1/actions/prepare",
      { method: "POST", body: JSON.stringify({ action, payload }) },
    ),
  execute: (approval_id: string, approval_code: string) =>
    apiFetch<{ ok: boolean }>("/api/v1/actions/execute", {
      method: "POST",
      body: JSON.stringify({ approval_id, approval_code }),
    }),
};

export const insightsApi = {
  cost: (days = 7) => apiFetch<{ total_usd: number; daily: Array<{ day: string; cost_usd: number }> }>(`/api/v1/insights/cost?days=${days}`),
  anomalies: () => apiFetch<{ items: unknown[] }>("/api/v1/insights/anomalies"),
  repos: () => apiFetch<{ items: Array<{ name: string; updated_at?: string }> }>("/api/v1/insights/repos"),
};

export const contentApi = {
  queue: () => apiFetch<{ items: unknown[] }>("/api/v1/content/queue"),
  published: () => apiFetch<{ items: unknown[] }>("/api/v1/content/published"),
  metrics: () => apiFetch<Record<string, unknown>>("/api/v1/content/metrics"),
};

export const searchApi = {
  query: (q: string) => apiFetch<{ items: unknown[] }>(`/api/v1/search?q=${encodeURIComponent(q)}`),
};
