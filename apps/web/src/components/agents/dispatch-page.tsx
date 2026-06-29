"use client";

import { useQuery } from "@tanstack/react-query";
import { dispatchApi } from "@hermes/sdk";
import { Badge, Card, Skeleton } from "@hermes/ui";

export function DispatchPage() {
  const all = useQuery({ queryKey: ["dispatch"], queryFn: dispatchApi.list, refetchInterval: 5000 });
  const active = useQuery({
    queryKey: ["dispatch", "active"],
    queryFn: dispatchApi.active,
    refetchInterval: 3000,
  });

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Dispatch Queue</h1>
      <p className="text-xs text-muted-foreground">Live updates via SSE + 3s polling</p>
      <section>
        <h2 className="text-sm font-medium text-muted-foreground mb-2">Active</h2>
        {active.isLoading ? <Skeleton className="h-16" /> : (
          <div className="space-y-2">
            {((active.data?.items ?? []) as Array<Record<string, unknown>>).map((d) => (
              <Card key={String(d.dispatch_id)}>
                <div className="flex gap-2 items-center">
                  <Badge variant="info">{String(d.status)}</Badge>
                  <span className="text-sm font-mono">{String(d.dispatch_id)}</span>
                  <span className="text-sm text-muted-foreground">{String(d.profile)}</span>
                </div>
                {d.stdout_tail ? (
                  <pre className="mt-2 text-xs font-mono bg-secondary/30 p-2 rounded max-h-32 overflow-auto">{String(d.stdout_tail)}</pre>
                ) : null}
              </Card>
            ))}
            {(active.data?.items ?? []).length === 0 && (
              <p className="text-sm text-muted-foreground">No active dispatches.</p>
            )}
          </div>
        )}
      </section>
      <section>
        <h2 className="text-sm font-medium text-muted-foreground mb-2">Recent</h2>
        <div className="space-y-2">
          {((all.data?.items ?? []) as Array<Record<string, unknown>>).slice(-10).reverse().map((d) => (
            <Card key={String(d.dispatch_id)} className="text-sm flex justify-between">
              <span className="font-mono">{String(d.dispatch_id)}</span>
              <Badge>{String(d.status)}</Badge>
            </Card>
          ))}
        </div>
      </section>
    </div>
  );
}
