"use client";

import { Button } from "@hermes/ui";
import { useUIStore } from "@/stores/ui-store";

export function TopBar() {
  const setCommandPaletteOpen = useUIStore((s) => s.setCommandPaletteOpen);
  const setAiChatOpen = useUIStore((s) => s.setAiChatOpen);

  return (
    <header className="sticky top-0 z-20 flex h-12 items-center gap-3 border-b border-border bg-background/80 backdrop-blur px-4">
      <button
        type="button"
        onClick={() => setCommandPaletteOpen(true)}
        className="flex flex-1 max-w-md items-center gap-2 rounded-md border border-border bg-secondary/30 px-3 py-1.5 text-sm text-muted-foreground hover:bg-secondary/50"
        aria-label="Open command palette"
      >
        <span aria-hidden>⌕</span>
        <span className="flex-1 text-left">Search or run a command…</span>
        <kbd className="hidden sm:inline text-xs bg-secondary px-1.5 rounded">⌘K</kbd>
      </button>
      <Button variant="ghost" onClick={() => setAiChatOpen(true)} aria-label="Open AI chat">
        💬 AI
      </Button>
      <Button variant="secondary" onClick={() => window.location.reload()} aria-label="Refresh">
        ↻
      </Button>
    </header>
  );
}
