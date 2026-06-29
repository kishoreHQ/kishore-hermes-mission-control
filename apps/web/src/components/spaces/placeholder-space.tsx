"use client";

import { EmptyState } from "@hermes/ui";

const PLUGINS: Record<string, { title: string; description: string }> = {
  create: { title: "Create", description: "Content Studio, Video Pipeline, Publishing — plugin Phase 5" },
  knowledge: { title: "Knowledge", description: "Research Lab, Knowledge Graph, Learning Hub — plugin Phase 5" },
  wealth: { title: "Wealth", description: "Finance Hub, Stock Dashboard — StockForge integration" },
  life: { title: "Life", description: "Goals, Habits, Journal, Calendar, Career" },
  insights: { title: "Insights", description: "Reports, Analytics, Timeline, Activity Feed" },
};

export function PlaceholderSpace({ space }: { space: string }) {
  const meta = PLUGINS[space] ?? { title: space, description: "Coming in a future phase." };
  return (
    <EmptyState
      title={meta.title}
      description={meta.description}
    />
  );
}
