"use client";

import { useQuery } from "@tanstack/react-query";
import { todayApi } from "@hermes/sdk";
import { Card, Skeleton } from "@hermes/ui";

export function LifePage() {
  const today = useQuery({ queryKey: ["today"], queryFn: todayApi.get });

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-semibold">Life</h1>
      <p className="text-sm text-muted-foreground">Personal agenda and routines from Today briefing.</p>
      {today.isLoading ? (
        <Skeleton className="h-48" />
      ) : (
        <Card className="space-y-3">
          <h2 className="text-sm font-medium uppercase tracking-wide text-muted-foreground">Today&apos;s agenda</h2>
          {(today.data?.agenda ?? []).length === 0 ? (
            <p className="text-sm text-muted-foreground">No agenda items.</p>
          ) : (
            today.data?.agenda.map((t) => (
              <label key={t.id} className="flex items-center gap-2 text-sm">
                <input type="checkbox" checked={t.done} readOnly className="rounded" />
                {t.title}
              </label>
            ))
          )}
        </Card>
      )}
    </div>
  );
}
