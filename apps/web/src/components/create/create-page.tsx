"use client";

import { useQuery } from "@tanstack/react-query";
import { contentApi } from "@hermes/sdk";
import { Badge, Card, EmptyState, Skeleton } from "@hermes/ui";

export function CreatePage() {
  const queue = useQuery({ queryKey: ["content", "queue"], queryFn: contentApi.queue });
  const published = useQuery({ queryKey: ["content", "published"], queryFn: contentApi.published });
  const metrics = useQuery({ queryKey: ["content", "metrics"], queryFn: contentApi.metrics });

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-semibold">Create — Content Pipeline</h1>
      <section>
        <h2 className="text-sm font-medium uppercase tracking-wide text-muted-foreground mb-3">Queue</h2>
        {queue.isLoading ? <Skeleton className="h-32" /> : (
          <div className="space-y-2">
            {((queue.data?.items ?? []) as Array<Record<string, unknown>>).map((item, i) => (
              <Card key={i} className="flex justify-between">
                <span className="text-sm">{String(item.topic ?? item.title ?? item.id ?? "Item")}</span>
                <Badge>{String(item.status ?? "queued")}</Badge>
              </Card>
            ))}
            {(queue.data?.items ?? []).length === 0 && (
              <EmptyState title="Queue empty" description="ContentForge data at /tmp/contentforge when running." />
            )}
          </div>
        )}
      </section>
      <section>
        <h2 className="text-sm font-medium uppercase tracking-wide text-muted-foreground mb-3">Published (recent)</h2>
        <Card className="text-sm text-muted-foreground">
          {(published.data?.items ?? []).length} posts tracked
        </Card>
      </section>
      <section>
        <h2 className="text-sm font-medium uppercase tracking-wide text-muted-foreground mb-3">Metrics</h2>
        <Card className="text-sm">
          <pre className="text-xs overflow-auto">{JSON.stringify(metrics.data ?? {}, null, 2)}</pre>
        </Card>
      </section>
    </div>
  );
}
