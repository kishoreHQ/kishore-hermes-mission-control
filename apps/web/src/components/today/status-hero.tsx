"use client";

import { Badge } from "@hermes/ui";
import type { StatusHero } from "@hermes/sdk";

const LEVEL_LABEL = {
  operational: { label: "Operational", variant: "success" as const },
  attention: { label: "Attention", variant: "warning" as const },
  action_required: { label: "Action required", variant: "error" as const },
};

export function StatusHero({ hero, greeting, date }: { hero: StatusHero; greeting: string; date: string }) {
  const meta = LEVEL_LABEL[hero.level] ?? LEVEL_LABEL.operational;
  return (
    <div className="rounded-lg border border-border bg-card p-6 space-y-3">
      <div className="flex flex-wrap items-center gap-3">
        <Badge variant={meta.variant}>{meta.label}</Badge>
        <span className="text-sm text-muted-foreground">{hero.summary}</span>
      </div>
      <h1 className="text-2xl font-semibold">{greeting}</h1>
      <p className="text-sm text-muted-foreground">
        {date} · {hero.active_runs} active runs · {hero.services_monitored} services · {hero.enabled_crons} crons
      </p>
    </div>
  );
}
