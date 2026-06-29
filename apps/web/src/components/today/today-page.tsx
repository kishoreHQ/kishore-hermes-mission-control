"use client";

import { useQuery } from "@tanstack/react-query";
import { Badge, Button, Card, MetricCard, Skeleton } from "@hermes/ui";
import { todayApi } from "@hermes/sdk";
import { AttentionFeed } from "./attention-feed";
import { BentoMetrics } from "./bento-metrics";
import { RunningNowStrip } from "./running-now-strip";
import { StatusHero } from "./status-hero";

export function TodayPage() {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["today"],
    queryFn: todayApi.get,
  });

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-32 w-full" />
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[1, 2, 3, 4, 5, 6, 7].map((i) => <Skeleton key={i} className="h-24" />)}
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <Card>
        <p className="text-destructive">Could not load Today briefing.</p>
        <Button className="mt-3" onClick={() => refetch()}>Retry</Button>
      </Card>
    );
  }

  const hero = data.status_hero ?? {
    level: "operational" as const,
    summary: "Loading status",
    active_runs: data.metrics.agents_active,
    services_monitored: 0,
    enabled_crons: 0,
  };

  const bento = data.bento ?? {
    running: data.metrics.agents_active,
    failed: 0,
    review: data.attention_count,
    blocked: 0,
    workflows: 0,
    cost_usd: 0,
    tokens: 0,
  };

  return (
    <div className="space-y-8">
      <StatusHero hero={hero} greeting={data.greeting} date={data.date} />
      <BentoMetrics bento={bento} />

      <section aria-labelledby="running-heading">
        <h2 id="running-heading" className="text-sm font-medium uppercase tracking-wide text-muted-foreground mb-3">
          Running now
        </h2>
        <RunningNowStrip items={data.running_now ?? []} />
      </section>

      <section aria-labelledby="attention-heading">
        <h2 id="attention-heading" className="text-sm font-medium uppercase tracking-wide text-muted-foreground mb-3">
          Needs attention
        </h2>
        <AttentionFeed items={data.attention} />
      </section>

      <div className="grid md:grid-cols-2 gap-6">
        <section aria-labelledby="agenda-heading">
          <h2 id="agenda-heading" className="text-sm font-medium uppercase tracking-wide text-muted-foreground mb-3">
            Today&apos;s agenda
          </h2>
          <Card className="space-y-2">
            {data.agenda.length === 0 ? (
              <p className="text-sm text-muted-foreground">No tasks scheduled.</p>
            ) : (
              data.agenda.map((t) => (
                <label key={t.id} className="flex items-center gap-2 text-sm">
                  <input type="checkbox" checked={t.done} readOnly className="rounded" />
                  {t.title}
                </label>
              ))
            )}
          </Card>
        </section>

        <section aria-labelledby="nightly-heading">
          <h2 id="nightly-heading" className="text-sm font-medium uppercase tracking-wide text-muted-foreground mb-3">
            Nightly report
          </h2>
          <Card>
            <p className="text-sm">{data.nightly_report.summary}</p>
          </Card>
        </section>
      </div>

      {data.recommendations.length > 0 && (
        <section aria-labelledby="recs-heading">
          <h2 id="recs-heading" className="text-sm font-medium uppercase tracking-wide text-muted-foreground mb-3">
            Recommendations
          </h2>
          <div className="space-y-2">
            {data.recommendations.map((r) => (
              <Card key={r.id} className="text-sm text-muted-foreground">{r.text}</Card>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
