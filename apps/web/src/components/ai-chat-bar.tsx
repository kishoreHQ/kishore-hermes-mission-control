"use client";

import { Button } from "@hermes/ui";
import { useState } from "react";
import { aiApi } from "@hermes/sdk";
import { useUIStore } from "@/stores/ui-store";

export function AIChatBar() {
  const open = useUIStore((s) => s.aiChatOpen);
  const setOpen = useUIStore((s) => s.setAiChatOpen);
  const [message, setMessage] = useState("");
  const [answer, setAnswer] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  if (!open) return null;

  const submit = async () => {
    if (!message.trim()) return;
    setLoading(true);
    try {
      const res = await aiApi.ask(message);
      setAnswer(res.answer);
    } catch {
      setAnswer("Could not reach API. Start apps/api on port 8000.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed bottom-0 md:bottom-4 right-4 left-4 md:left-auto z-40 w-auto md:w-96 rounded-xl border border-border bg-popover shadow-2xl p-4" role="dialog" aria-label="AI chat">
      <div className="flex justify-between items-center mb-3">
        <span className="font-medium text-sm">Ask Hermes</span>
        <button type="button" onClick={() => setOpen(false)} className="text-muted-foreground hover:text-foreground" aria-label="Close">✕</button>
      </div>
      <textarea
        value={message}
        onChange={(e) => setMessage(e.target.value)}
        placeholder="Ask anything about your dashboard…"
        className="w-full rounded-md border border-border bg-secondary/30 px-3 py-2 text-sm min-h-[80px] resize-none outline-none focus:ring-1 focus:ring-ring"
        onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); submit(); } }}
      />
      <div className="flex justify-end mt-2">
        <Button onClick={submit} disabled={loading}>{loading ? "…" : "Ask"}</Button>
      </div>
      {answer && (
        <p className="mt-3 text-sm text-muted-foreground border-t border-border pt-3">{answer}</p>
      )}
    </div>
  );
}
