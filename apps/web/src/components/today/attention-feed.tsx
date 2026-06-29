"use client";

import { useMutation } from "@tanstack/react-query";
import { Badge, Button, Card } from "@hermes/ui";
import { actionsApi } from "@hermes/sdk";

function severityVariant(s: string): "error" | "warning" | "info" | "success" {
  if (s === "error") return "error";
  if (s === "warning") return "warning";
  if (s === "info") return "info";
  return "success";
}

export function AttentionFeed({
  items,
}: {
  items: Array<{
    id: string;
    severity: string;
    title: string;
    actions: string[];
    action_targets?: Record<string, string>;
  }>;
}) {
  const runAction = useMutation({
    mutationFn: async ({ action, targets }: { action: string; targets?: Record<string, string> }) => {
      const prep = await actionsApi.prepare(action, targets);
      if (prep.auto_execute && prep.approval_code) {
        return actionsApi.execute(prep.approval_id, prep.approval_code);
      }
      if (prep.approval_code) {
        return actionsApi.execute(prep.approval_id, prep.approval_code);
      }
      return prep;
    },
  });

  return (
    <div className="space-y-2">
      {items.map((item) => (
        <Card key={item.id} className="flex items-center justify-between gap-4 py-3">
          <div className="flex items-center gap-3 min-w-0">
            <Badge variant={severityVariant(item.severity)}>{item.severity}</Badge>
            <span className="text-sm truncate">{item.title}</span>
          </div>
          <div className="flex gap-2 shrink-0">
            {item.actions.map((a) => (
              <Button
                key={a}
                variant="ghost"
                className="text-xs capitalize"
                disabled={runAction.isPending}
                onClick={() =>
                  runAction.mutate({
                    action: a === "retry" ? "retry_dispatch" : a === "restart" ? "restart_service" : a,
                    targets: item.action_targets,
                  })
                }
              >
                {a}
              </Button>
            ))}
          </div>
        </Card>
      ))}
    </div>
  );
}
