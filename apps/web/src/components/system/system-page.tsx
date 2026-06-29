"use client";

import { useQuery } from "@tanstack/react-query";
import { pluginsApi } from "@hermes/sdk";
import { Card } from "@hermes/ui";

export function SystemPage() {
  const plugins = useQuery({ queryKey: ["plugins"], queryFn: pluginsApi.list });

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">System</h1>
      <section>
        <h2 className="text-sm font-medium text-muted-foreground mb-2">Plugin registry</h2>
        <div className="grid md:grid-cols-2 gap-3">
          {(plugins.data?.items ?? []).map((p) => {
            const plugin = p as { id: string; name: string; space: string; status: string };
            return (
            <Card key={plugin.id}>
              <p className="font-medium">{plugin.name}</p>
              <p className="text-xs text-muted-foreground">{plugin.space} · {plugin.status}</p>
            </Card>
          );})}
        </div>
      </section>
      <Card>
        <h2 className="text-sm font-medium mb-2">Settings</h2>
        <p className="text-sm text-muted-foreground">Profile mode, routing thresholds, and refresh interval — connect to /api/v1/settings in production.</p>
      </Card>
    </div>
  );
}
