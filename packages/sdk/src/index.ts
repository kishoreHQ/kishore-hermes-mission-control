import { apiFetch } from "./client";

export interface TodayData {
  greeting: string;
  date: string;
  attention_count: number;
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
  }>;
  agenda: Array<{ id: string; title: string; done: boolean }>;
  nightly_report: { summary: string; artifacts: string[] };
  recommendations: Array<{ id: string; text: string }>;
  quick_actions: string[];
}

export const todayApi = {
  get: () => apiFetch<TodayData>("/api/v1/today"),
};

export const dispatchApi = {
  list: () => apiFetch<{ items: unknown[] }>("/api/v1/dispatch"),
  active: () => apiFetch<{ items: unknown[] }>("/api/v1/dispatch/active"),
};

export const agentsApi = {
  profiles: () => apiFetch<{ items: unknown[] }>("/api/v1/profiles"),
  workflows: () => apiFetch<{ items: unknown[] }>("/api/v1/workflows"),
  tasks: () => apiFetch<{ items: unknown[] }>("/api/v1/tasks"),
  cron: () => apiFetch<{ items: unknown[] }>("/api/v1/cron"),
};

export const infraApi = {
  services: () => apiFetch<{ items: unknown[] }>("/api/v1/services"),
  health: () => apiFetch<{ summary: string; items: unknown[] }>("/api/v1/services/health"),
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
