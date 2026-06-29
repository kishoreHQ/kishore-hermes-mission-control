"use client";

import { MetricCard } from "@hermes/ui";
import type { BentoMetrics } from "@hermes/sdk";

export function BentoMetrics({ bento }: { bento: BentoMetrics }) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3">
      <MetricCard label="Running" value={bento.running} sub="active" />
      <MetricCard label="Failed" value={bento.failed} sub="dispatches" />
      <MetricCard label="Review" value={bento.review} sub="items" />
      <MetricCard label="Blocked" value={bento.blocked} sub="tasks" />
      <MetricCard label="Workflows" value={bento.workflows} sub="total" />
      <MetricCard label="Cost" value={`$${bento.cost_usd.toFixed(2)}`} sub="est." />
      <MetricCard label="Tokens" value={bento.tokens > 1e6 ? `${(bento.tokens / 1e6).toFixed(1)}M` : bento.tokens} sub="session" />
    </div>
  );
}
