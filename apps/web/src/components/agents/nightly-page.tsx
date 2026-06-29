"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { nightlyApi } from "@hermes/sdk";
import { Button, Card, MetricCard, Skeleton } from "@hermes/ui";

export function NightlyPage() {
  const qc = useQueryClient();
  const latest = useQuery({ queryKey: ["nightly"], queryFn: nightlyApi.latest });
  const dag = useQuery({ queryKey: ["nightly", "dag"], queryFn: nightlyApi.dag });
  const trigger = useMutation({
    mutationFn: nightlyApi.trigger,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["nightly"] }),
  });

  const run = latest.data?.run as Record<string, unknown> | null | undefined;
  const jobs = (dag.data as { jobs?: Record<string, unknown> })?.jobs ?? {};

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-semibold">Nightly Pipeline</h1>
        <Button onClick={() => trigger.mutate()} disabled={trigger.isPending}>
          {trigger.isPending ? "Running…" : "Trigger now"}
        </Button>
      </div>

      {latest.isLoading ? <Skeleton className="h-24" /> : run ? (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <MetricCard label="Status" value={String(run.status)} />
          <MetricCard label="Succeeded" value={String(run.jobs_succeeded ?? 0)} />
          <MetricCard label="Failed" value={String(run.jobs_failed ?? 0)} />
          <MetricCard label="Total jobs" value={String(run.jobs_total ?? 0)} />
        </div>
      ) : (
        <Card><p className="text-sm text-muted-foreground">No nightly runs yet. Trigger manually or wait for 2 AM schedule.</p></Card>
      )}

      <section>
        <h2 className="text-sm font-medium text-muted-foreground mb-2">DAG jobs</h2>
        <div className="grid md:grid-cols-2 gap-2">
          {Object.entries(jobs).map(([key, job]) => (
            <Card key={key} className="text-sm">
              <span className="font-medium">{key}</span>
              <p className="text-xs text-muted-foreground mt-1">
                {(job as { profile?: string; type?: string }).profile ?? (job as { type?: string }).type ?? "dispatch"}
              </p>
            </Card>
          ))}
        </div>
      </section>

      {run?.report_markdown ? (
        <Card>
          <h2 className="text-sm font-medium mb-2">Morning report</h2>
          <pre className="text-sm whitespace-pre-wrap">{String(run.report_markdown)}</pre>
        </Card>
      ) : null}
    </div>
  );
}
