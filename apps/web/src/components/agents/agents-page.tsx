"use client";

import { useQuery } from "@tanstack/react-query";
import { agentsApi, dispatchApi } from "@hermes/sdk";
import { Badge, Card, EmptyState, Skeleton } from "@hermes/ui";
import Link from "next/link";

export function AgentsPage() {
  const profiles = useQuery({ queryKey: ["profiles"], queryFn: agentsApi.profiles });
  const workflows = useQuery({ queryKey: ["workflows"], queryFn: agentsApi.workflows });
  const active = useQuery({ queryKey: ["dispatch", "active"], queryFn: dispatchApi.active });

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Agents & Automation</h1>
        <div className="flex gap-2 text-sm">
          <Link href="/agents/dispatch" className="text-primary hover:underline">Dispatch</Link>
          <Link href="/agents/workflows" className="text-primary hover:underline">Workflows</Link>
          <Link href="/agents/nightly" className="text-primary hover:underline">Nightly</Link>
        </div>
      </div>

      <section>
        <h2 className="text-sm font-medium uppercase tracking-wide text-muted-foreground mb-3">Agent fleet</h2>
        {profiles.isLoading ? (
          <div className="grid md:grid-cols-3 gap-4">{[1, 2, 3].map((i) => <Skeleton key={i} className="h-28" />)}</div>
        ) : (
          <div className="grid md:grid-cols-3 gap-4">
            {((profiles.data?.items ?? []) as Array<{ name?: string; role?: string }>).map((p, i) => (
              <Card key={i}>
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-xl">◈</span>
                  <span className="font-medium">{p.name ?? `Profile ${i + 1}`}</span>
                </div>
                <p className="text-xs text-muted-foreground">{p.role ?? "Hermes profile"}</p>
                <Badge variant="success" className="mt-2">idle</Badge>
              </Card>
            ))}
            {(profiles.data?.items ?? []).length === 0 && (
              <EmptyState title="No profiles" description="Configure workflows.json agents on the VPS." />
            )}
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
                  <p className="text-xs text-muted-foreground truncate max-w-md">{String(d.prompt)}</p>
                </div>
                <Link href={`/agents/dispatch?id=${d.dispatch_id}`} className="text-xs text-primary">Live →</Link>
              </Card>
            ))}
            {(active.data?.items ?? []).length === 0 && (
              <EmptyState title="No active dispatches" description="Enqueue a dispatch from the queue." />
            )}
          </div>
        )}
      </section>

      <section>
        <h2 className="text-sm font-medium uppercase tracking-wide text-muted-foreground mb-3">Workflows</h2>
        {workflows.isLoading ? <Skeleton className="h-20" /> : (
          <div className="grid md:grid-cols-2 gap-4">
            {((workflows.data?.items ?? []) as Array<Record<string, unknown>>).slice(0, 4).map((w, i) => (
              <Card key={String(w.id ?? i)}>
                <p className="font-medium">{String(w.title ?? `Workflow ${i + 1}`)}</p>
                <Badge className="mt-2">{String(w.status ?? "unknown")}</Badge>
              </Card>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
