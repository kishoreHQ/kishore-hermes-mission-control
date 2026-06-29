"use client";

import { useQuery } from "@tanstack/react-query";
import { infraApi } from "@hermes/sdk";
import { Badge, Card, MetricCard, Skeleton } from "@hermes/ui";

export function InfrastructurePage() {
  const health = useQuery({ queryKey: ["services", "health"], queryFn: infraApi.health });
  const system = useQuery({ queryKey: ["system"], queryFn: infraApi.system });

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Infrastructure</h1>
      <p className="text-muted-foreground text-sm">{health.data?.summary ?? "Loading…"}</p>

      {system.isLoading ? (
        <Skeleton className="h-20" />
      ) : (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <MetricCard label="Load" value={String(system.data?.load ?? "—").split(" ")[0] ?? "—"} />
          <MetricCard label="Memory" value={String(system.data?.memory_mb ?? "—")} sub="used / total MB" />
          <MetricCard label="Disk" value={String(system.data?.disk ?? "—")} />
          <MetricCard label="Crons" value={Number(system.data?.cron_count ?? 0)} />
        </div>
      )}

      {health.isLoading ? (
        <div className="grid md:grid-cols-3 gap-4">{[1, 2, 3].map((i) => <Skeleton key={i} className="h-24" />)}</div>
      ) : (
        <div className="grid md:grid-cols-3 gap-4">
          {(health.data?.items ?? []).map((s) => {
            const svc = s as { id?: string; name?: string; status?: string; health?: string; port?: number };
            const st = svc.status ?? svc.health ?? "unknown";
            return (
              <Card key={svc.id}>
                <p className="font-medium">{svc.name}</p>
                <p className="text-xs text-muted-foreground">:{svc.port}</p>
                <Badge variant={st === "online" ? "success" : st === "degraded" ? "warning" : "error"} className="mt-2">
                  {st}
                </Badge>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
