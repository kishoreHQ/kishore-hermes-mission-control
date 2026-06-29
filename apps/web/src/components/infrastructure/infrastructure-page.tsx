"use client";

import { useQuery } from "@tanstack/react-query";
import { infraApi } from "@hermes/sdk";
import { Badge, Card, Skeleton } from "@hermes/ui";

export function InfrastructurePage() {
  const health = useQuery({ queryKey: ["services", "health"], queryFn: infraApi.health });

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Infrastructure</h1>
      <p className="text-muted-foreground text-sm">{health.data?.summary ?? "Loading…"}</p>
      {health.isLoading ? (
        <div className="grid md:grid-cols-3 gap-4">{[1, 2, 3].map((i) => <Skeleton key={i} className="h-24" />)}</div>
      ) : (
        <div className="grid md:grid-cols-3 gap-4">
          {(health.data?.items ?? []).map((s) => {
            const svc = s as { id?: string; name?: string; health?: string; port?: number };
            return (
            <Card key={svc.id}>
              <p className="font-medium">{svc.name}</p>
              <p className="text-xs text-muted-foreground">:{svc.port}</p>
              <Badge variant={svc.health === "degraded" ? "warning" : "success"} className="mt-2">
                {svc.health ?? "unknown"}
              </Badge>
            </Card>
          );})}
        </div>
      )}
    </div>
  );
}
