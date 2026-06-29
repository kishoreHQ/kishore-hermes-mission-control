"use client";

import { useQuery } from "@tanstack/react-query";
import { agentsApi, dispatchApi } from "@hermes/sdk";
import { Badge, Card, EmptyState, Skeleton } from "@hermes/ui";
import Link from "next/link";

export function AgentsPage() {
  const profiles = useQuery({ queryKey: ["profiles"], queryFn: agentsApi.profiles });
  const workflows = useQuery({ queryKey: ["workflows"], queryFn: agentsApi.workflows });
  const active = useQuery({ queryKey: ["dispatch", "active"], queryFn: dispatchApi.active });
  const cron = useQuery({ queryKey: ["cron"], queryFn: agentsApi.cron });

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h1 className="text-2xl font-semibold">Agents & Automation</h1>
        <div className="flex gap-2 text-sm">
          <Link href="/agents/dispatch" className="text-primary hover:underline">Dispatch</Link>
          <Link href="/agents/workflows" className="text-primary hover:underline">Workflows</Link>
          <Link href="/missions" className="text-primary hover:underline">Missions</Link>
          <Link href="/agents/nightly" className="text-primary hover:underline">Nightly</Link>
        </div>
      </div>

      <section>
        <h2 className="text-sm font-medium uppercase tracking-wide text-muted-foreground mb-3">
          Cron jobs ({cron.data?.items?.length ?? "—"})
        </h2>
        {cron.isLoading ? <Skeleton className="h-40" /> : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-muted-foreground border-b border-border">
                  <th className="py-2 pr-4">Name</th>
                  <th className="py-2 pr-4">Schedule</th>
                  <th className="py-2 pr-4">Last</th>
                  <th className="py-2">Status</th>
                </tr>
              </thead>
              <tbody>
                {((cron.data?.items ?? []) as Array<Record<string, unknown>>).map((j) => (
                  <tr key={String(j.id)} className="border-b border-border/50">
                    <td className="py-2 pr-4 font-medium">{String(j.name)}</td>
                    <td className="py-2 pr-4 text-muted-foreground">{String(j.schedule)}</td>
                    <td className="py-2 pr-4 text-muted-foreground">{String(j.last_run_at ?? "—")}</td>
                    <td className="py-2">
                      <Badge variant={j.needs_review ? "warning" : j.enabled ? "success" : "info"}>
                        {j.needs_review ? "review" : String(j.last_status ?? j.state)}
                      </Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {(cron.data?.items ?? []).length === 0 && (
              <EmptyState title="No cron jobs" description="Set HERMES_HOME on the API to load ~/.hermes/cron/jobs.json" />
            )}
          </div>
        )}
      </section>

      <section>
        <h2 className="text-sm font-medium uppercase tracking-wide text-muted-foreground mb-3">Agent fleet</h2>
        {profiles.isLoading ? (
          <div className="grid md:grid-cols-3 gap-4">{[1, 2, 3].map((i) => <Skeleton key={i} className="h-28" />)}</div>
        ) : (
          <div className="grid md:grid-cols-3 gap-4">
            {((profiles.data?.items ?? []) as Array<{ name?: string; id?: string; role?: string }>).map((p, i) => (
              <Card key={p.id ?? i}>
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-xl">◈</span>
                  <span className="font-medium">{p.name ?? p.id ?? `Profile ${i + 1}`}</span>
                </div>
                <p className="text-xs text-muted-foreground">{p.role ?? "Hermes profile"}</p>
              </Card>
            ))}
          </div>
        )}
      </section>

      <section>
        <h2 className="text-sm font-medium uppercase tracking-wide text-muted-foreground mb-3">Active dispatch</h2>
        {active.isLoading ? <Skeleton className="h-20" /> : (
          <div className="space-y-2">
            {((active.data?.items ?? []) as Array<Record<string, unknown>>).map((d) => (
              <Card key={String(d.dispatch_id)} className="flex justify-between items-start gap-4">
                <div>
                  <Badge variant="info">{String(d.status)}</Badge>
                  <p className="text-sm font-medium mt-1">{String(d.profile)}</p>
                </div>
                <Link href="/agents/dispatch" className="text-xs text-primary">Live →</Link>
              </Card>
            ))}
            {(active.data?.items ?? []).length === 0 && (
              <EmptyState title="No active dispatches" description="Enqueue from Dispatch." />
            )}
          </div>
        )}
      </section>

      <section>
        <h2 className="text-sm font-medium uppercase tracking-wide text-muted-foreground mb-3">Workflows</h2>
        {workflows.isLoading ? <Skeleton className="h-20" /> : (
          <div className="grid md:grid-cols-2 gap-4">
            {((workflows.data?.items ?? []) as Array<Record<string, unknown>>).slice(0, 6).map((w, i) => (
              <Card key={String(w.id ?? i)}>
                <p className="font-medium">{String(w.title ?? w.name ?? `Workflow ${i + 1}`)}</p>
                <Badge className="mt-2">{String(w.status ?? "unknown")}</Badge>
              </Card>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
