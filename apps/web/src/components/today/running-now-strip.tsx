"use client";

import { Badge, Card } from "@hermes/ui";
import type { RunningNowItem } from "@hermes/sdk";

export function RunningNowStrip({ items }: { items: RunningNowItem[] }) {
  if (items.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">Nothing running right now.</p>
    );
  }
  return (
    <div className="flex gap-3 overflow-x-auto pb-2">
      {items.map((item) => (
        <Card key={`${item.type}-${item.id}`} className="min-w-[160px] shrink-0 p-3 space-y-2">
          <div className="flex items-center justify-between gap-2">
            <span className="text-sm font-medium truncate">{item.name}</span>
            <Badge variant="info">{item.type}</Badge>
          </div>
          <p className="text-xs text-muted-foreground capitalize">{item.status}</p>
          {item.progress > 0 && (
            <div className="h-1.5 rounded-full bg-muted overflow-hidden">
              <div className="h-full bg-primary" style={{ width: `${Math.min(item.progress, 100)}%` }} />
            </div>
          )}
        </Card>
      ))}
    </div>
  );
}
