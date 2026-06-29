"use client";

import { useQuery } from "@tanstack/react-query";
import { agentsApi } from "@hermes/sdk";
import { Badge, Card, Skeleton } from "@hermes/ui";

const LANES = ["in_progress", "scheduled", "needs_review", "blocked", "archived"] as const;

export function MissionsPage() {
  const tasks = useQuery({ queryKey: ["tasks"], queryFn: agentsApi.tasks });

  const items = (tasks.data?.items ?? []) as Array<Record<string, unknown>>;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Missions</h1>
      {tasks.isLoading ? (
        <Skeleton className="h-64" />
      ) : (
        <div className="grid md:grid-cols-3 lg:grid-cols-5 gap-4">
          {LANES.map((lane) => (
            <div key={lane} className="space-y-2">
              <h2 className="text-xs font-medium uppercase tracking-wide text-muted-foreground capitalize">
                {lane.replace("_", " ")}
              </h2>
              {items
                .filter((t) => (t.lane as string) === lane)
                .map((t) => (
                  <Card key={String(t.id)} className="p-3">
                    <p className="text-sm font-medium">{String(t.title)}</p>
                    {t.profile ? <Badge className="mt-2">{String(t.profile)}</Badge> : null}
                  </Card>
                ))}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
