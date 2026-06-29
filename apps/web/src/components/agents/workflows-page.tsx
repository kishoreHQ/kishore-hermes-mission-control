"use client";

import { useQuery } from "@tanstack/react-query";
import { agentsApi } from "@hermes/sdk";
import { Badge, Card, Skeleton } from "@hermes/ui";

export function WorkflowsPage() {
  const workflows = useQuery({ queryKey: ["workflows"], queryFn: agentsApi.workflows });

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Workflows</h1>
      {workflows.isLoading ? (
        <Skeleton className="h-40" />
      ) : (
        <div className="space-y-3">
          {((workflows.data?.items ?? []) as Array<Record<string, unknown>>).map((w, i) => (
            <Card key={String(w.id ?? i)} className="flex justify-between items-center">
              <div>
                <p className="font-medium">{String(w.title ?? w.name ?? w.id)}</p>
                <p className="text-xs text-muted-foreground mt-1">{String(w.purpose ?? "")}</p>
              </div>
              <Badge>{String(w.status ?? w.runtime_state ?? "unknown")}</Badge>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
