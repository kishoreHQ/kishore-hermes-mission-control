"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";

const API_URL =
  process.env.NEXT_PUBLIC_API_URL === undefined
    ? "http://localhost:8000"
    : process.env.NEXT_PUBLIC_API_URL;

export function SSEProvider({ children }: { children: React.ReactNode }) {
  const queryClient = useQueryClient();

  useEffect(() => {
    let es: EventSource | null = null;
    try {
      es = new EventSource(`${API_URL}/api/v1/stream/events`);
      es.addEventListener("heartbeat", () => {
        queryClient.invalidateQueries({ queryKey: ["dispatch", "active"] });
      });
      es.addEventListener("dispatch.updated", () => {
        queryClient.invalidateQueries({ queryKey: ["dispatch"] });
      });
      es.addEventListener("nightly.completed", () => {
        queryClient.invalidateQueries({ queryKey: ["today"] });
        queryClient.invalidateQueries({ queryKey: ["nightly"] });
      });
    } catch {
      // SSE unavailable in SSR or offline
    }
    return () => es?.close();
  }, [queryClient]);

  return <>{children}</>;
}
