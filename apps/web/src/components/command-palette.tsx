"use client";

import { Command } from "cmdk";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { SPACES } from "@/lib/spaces";
import { useUIStore } from "@/stores/ui-store";

export function CommandPalette() {
  const open = useUIStore((s) => s.commandPaletteOpen);
  const setOpen = useUIStore((s) => s.setCommandPaletteOpen);
  const router = useRouter();

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setOpen(!open);
      }
      if (e.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, setOpen]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 bg-black/50" onClick={() => setOpen(false)} role="presentation">
      <div
        className="fixed left-1/2 top-[20%] w-full max-w-lg -translate-x-1/2 rounded-xl border border-border bg-popover shadow-2xl overflow-hidden"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-label="Command palette"
      >
        <Command label="Command palette">
          <Command.Input
            placeholder="Type a command or search…"
            className="w-full border-b border-border bg-transparent px-4 py-3 text-sm outline-none"
          />
          <Command.List className="max-h-80 overflow-y-auto p-2">
            <Command.Empty className="py-6 text-center text-sm text-muted-foreground">No results.</Command.Empty>
            <Command.Group heading="Navigate" className="text-xs text-muted-foreground px-2 py-1">
              {SPACES.map((s) => (
                <Command.Item
                  key={s.id}
                  value={`go ${s.label}`}
                  onSelect={() => {
                    router.push(s.href);
                    setOpen(false);
                  }}
                  className="flex cursor-pointer items-center gap-2 rounded-md px-2 py-2 text-sm aria-selected:bg-primary/10"
                >
                  <span>{s.icon}</span> Go to {s.label}
                </Command.Item>
              ))}
            </Command.Group>
            <Command.Group heading="Actions" className="text-xs text-muted-foreground px-2 py-1 mt-2">
              <Command.Item
                value="missions"
                onSelect={() => { router.push("/missions"); setOpen(false); }}
                className="flex cursor-pointer rounded-md px-2 py-2 text-sm aria-selected:bg-primary/10"
              >
                ◈ Open Missions board
              </Command.Item>
              <Command.Item
                value="dispatch"
                onSelect={() => { router.push("/agents/dispatch"); setOpen(false); }}
                className="flex cursor-pointer rounded-md px-2 py-2 text-sm aria-selected:bg-primary/10"
              >
                ⚡ Dispatch queue
              </Command.Item>
              <Command.Item
                value="nightly"
                onSelect={() => { router.push("/agents/nightly"); setOpen(false); }}
                className="flex cursor-pointer rounded-md px-2 py-2 text-sm aria-selected:bg-primary/10"
              >
                🌙 Nightly builds
              </Command.Item>
              <Command.Item
                value="refresh"
                onSelect={() => { window.location.reload(); setOpen(false); }}
                className="flex cursor-pointer rounded-md px-2 py-2 text-sm aria-selected:bg-primary/10"
              >
                ↻ Refresh all
              </Command.Item>
              <Command.Item
                value="ask failed"
                onSelect={() => { router.push("/system"); setOpen(false); }}
                className="flex cursor-pointer rounded-md px-2 py-2 text-sm aria-selected:bg-primary/10"
              >
                💬 Ask: What failed last night?
              </Command.Item>
            </Command.Group>
          </Command.List>
        </Command>
      </div>
    </div>
  );
}
