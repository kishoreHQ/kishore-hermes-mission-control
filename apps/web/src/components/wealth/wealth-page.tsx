"use client";

import { useQuery } from "@tanstack/react-query";
import { todayApi } from "@hermes/sdk";
import { Card, MetricCard, Skeleton } from "@hermes/ui";

export function WealthPage() {
  const today = useQuery({ queryKey: ["today"], queryFn: todayApi.get });

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Wealth</h1>
      {today.isLoading ? (
        <Skeleton className="h-24" />
      ) : (
        <div className="grid grid-cols-2 gap-4">
          <MetricCard
            label={today.data?.metrics.stocks.symbol ?? "Market"}
            value={today.data?.metrics.stocks.change ?? "—"}
            sub="StockPulse / Nightly research"
          />
          <Card className="text-sm text-muted-foreground p-4">
            Full StockPulse charts connect when nightly stock_research artifacts are available.
          </Card>
        </div>
      )}
    </div>
  );
}
