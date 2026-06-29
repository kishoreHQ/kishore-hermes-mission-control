"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { searchApi } from "@hermes/sdk";
import { Card, Skeleton } from "@hermes/ui";

export function KnowledgePage() {
  const [q, setQ] = useState("");
  const search = useQuery({
    queryKey: ["search", q],
    queryFn: () => searchApi.query(q),
    enabled: q.length >= 2,
  });

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Knowledge</h1>
      <input
        className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
        placeholder="Search cron, tasks, services…"
        value={q}
        onChange={(e) => setQ(e.target.value)}
      />
      {search.isFetching ? (
        <Skeleton className="h-32" />
      ) : (
        <div className="space-y-2">
          {((search.data?.items ?? []) as Array<Record<string, unknown>>).map((hit, i) => (
            <Card key={i} className="text-sm flex justify-between">
              <span>{String(hit.title)}</span>
              <span className="text-muted-foreground">{String(hit.source)}</span>
            </Card>
          ))}
          {q.length >= 2 && (search.data?.items ?? []).length === 0 && (
            <p className="text-sm text-muted-foreground">No results.</p>
          )}
        </div>
      )}
    </div>
  );
}
