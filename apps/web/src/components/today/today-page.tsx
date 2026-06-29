"use client";

import { useQuery } from "@tanstack/react-query";
import { Badge, Button, Card, MetricCard, Skeleton } from "@hermes/ui";
import { todayApi } from "@hermes/sdk";

function severityVariant(s: string): "error" | "warning" | "info" | "success" {
  if (s === "error") return "error";
  if (s === "warning") return "warning";
  if (s === "info") return "info";
  return "success";
}

export function TodayPage() {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["today"],
    queryFn: todayApi.get,
  });

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-64" />
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => <Skeleton key={i} className="h-24" />)}
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <Card>
        <p className="text-destructive">Could not load Today briefing.</p>
        <p className="text-sm text-muted-foreground mt-1">Ensure API is running on port 8000.</p>
        <Button className="mt-3" onClick={() => refetch()}>Retry</Button>
      </Card>
    );
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold">{data.greeting}</h1>
        <p className="text-muted-foreground text-sm mt-1">
          {data.date} · {data.attention_count} item{data.attention_count !== 1 ? "s" : ""} need you
        </p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MetricCard
          label="Nightly"
          value={`${data.metrics.nightly.succeeded}/${data.metrics.nightly.total || "—"}`}
          sub={data.metrics.nightly.status}
        />
        <MetricCard label="Agents" value={data.metrics.agents_active} sub="active" />
        <MetricCard label="Content" value={data.metrics.content_queued} sub="queued" />
        <MetricCard label={data.metrics.stocks.symbol} value={data.metrics.stocks.change} />
      </div>

      <section aria-labelledby="attention-heading">
        <h2 id="attention-heading" className="text-sm font-medium uppercase tracking-wide text-muted-foreground mb-3">
          Needs attention
        </h2>
        <div className="space-y-2">
          {data.attention.map((item) => (
            <Card key={item.id} className="flex items-center justify-between gap-4 py-3">
              <div className="flex items-center gap-3 min-w-0">
                <Badge variant={severityVariant(item.severity)}>{item.severity}</Badge>
                <span className="text-sm truncate">{item.title}</span>
              </div>
              <div className="flex gap-2 shrink-0">
                {item.actions.map((a) => (
                  <Button key={a} variant="ghost" className="text-xs capitalize">{a}</Button>
                ))}
              </div>
            </Card>
          ))}
        </div>
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

      <div className="flex flex-wrap gap-2">
        {data.quick_actions.map((a) => (
          <Button key={a} variant="secondary" className="capitalize">{a.replace("_", " ")}</Button>
        ))}
      </div>
    </div>
  );
}
