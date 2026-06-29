"use client";

import { useQuery } from "@tanstack/react-query";
import { insightsApi, todayApi } from "@hermes/sdk";
import { Card, MetricCard, Skeleton } from "@hermes/ui";

export function InsightsPage() {
  const cost = useQuery({ queryKey: ["insights", "cost"], queryFn: () => insightsApi.cost(7) });
  const anomalies = useQuery({ queryKey: ["insights", "anomalies"], queryFn: insightsApi.anomalies });
  const repos = useQuery({ queryKey: ["insights", "repos"], queryFn: insightsApi.repos });
  const today = useQuery({ queryKey: ["today"], queryFn: todayApi.get });

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-semibold">Insights</h1>
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        {cost.isLoading ? (
          <Skeleton className="h-24" />
        ) : (
          <>
            <MetricCard label="7-day cost" value={`$${(cost.data?.total_usd ?? 0).toFixed(2)}`} />
            <MetricCard label="Tokens" value={today.data?.bento?.tokens ?? 0} sub="tracked" />
            <MetricCard label="Anomalies" value={anomalies.data?.items?.length ?? 0} sub="open" />
          </>
        )}
      </div>
      <section>
        <h2 className="text-sm font-medium uppercase tracking-wide text-muted-foreground mb-3">Daily cost</h2>
        <Card className="space-y-2">
          {(cost.data?.daily ?? []).map((d) => (
            <div key={d.day} className="flex justify-between text-sm">
              <span>{d.day}</span>
              <span>${Number(d.cost_usd).toFixed(2)}</span>
            </div>
          ))}
          {(cost.data?.daily ?? []).length === 0 && (
            <p className="text-sm text-muted-foreground">No cost data yet — ingested from Hermes sessions.</p>
          )}
        </Card>
      </section>
      <section>
        <h2 className="text-sm font-medium uppercase tracking-wide text-muted-foreground mb-3">Repositories</h2>
        <Card className="space-y-2">
          {(repos.data?.items ?? []).map((r) => (
            <div key={r.name} className="flex justify-between text-sm">
              <span>{r.name}</span>
              <span className="text-muted-foreground">{r.updated_at?.slice(0, 10) ?? ""}</span>
            </div>
          ))}
          {(repos.data?.items ?? []).length === 0 && (
            <p className="text-sm text-muted-foreground">Set GITHUB_TOKEN on the API host for live repo list.</p>
          )}
        </Card>
      </section>
      <section>
        <h2 className="text-sm font-medium uppercase tracking-wide text-muted-foreground mb-3">Recommendations</h2>
        <div className="space-y-2">
          {(today.data?.recommendations ?? []).map((r) => (
            <Card key={r.id} className="text-sm">{r.text}</Card>
          ))}
        </div>
      </section>
    </div>
  );
}
