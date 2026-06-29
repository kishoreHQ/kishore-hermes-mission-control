"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { SPACES } from "@/lib/spaces";
import { cn } from "@hermes/ui";

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside
      className="hidden md:flex w-60 flex-col border-r border-border bg-[hsl(222,45%,5%)] fixed inset-y-0 left-0 z-30"
      aria-label="Main navigation"
    >
      <div className="flex items-center gap-2 px-4 h-12 border-b border-border">
        <span className="flex h-7 w-7 items-center justify-center rounded-md bg-primary text-primary-foreground text-sm font-bold">H</span>
        <span className="font-semibold text-sm">Hermes OS</span>
      </div>
      <nav className="flex-1 overflow-y-auto p-2 space-y-0.5">
        {SPACES.map((space) => {
          const active = pathname.startsWith(space.href);
          return (
            <Link
              key={space.id}
              href={space.href}
              className={cn(
                "flex items-center gap-2.5 rounded-md px-3 py-2 text-sm transition-colors",
                active
                  ? "bg-primary/10 text-primary border-l-2 border-primary"
                  : "text-muted-foreground hover:bg-secondary/50 hover:text-foreground"
              )}
            >
              <span aria-hidden>{space.icon}</span>
              {space.label}
            </Link>
          );
        })}
      </nav>
      <div className="p-3 border-t border-border text-xs text-muted-foreground flex items-center gap-2">
        <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" aria-hidden />
        Operational
      </div>
    </aside>
  );
}

export function MobileNav() {
  const pathname = usePathname();
  const mobile = SPACES.slice(0, 4).concat(SPACES.find((s) => s.id === "system")!);

  return (
    <nav
      className="md:hidden fixed bottom-0 inset-x-0 z-30 flex border-t border-border bg-card"
      aria-label="Mobile navigation"
    >
      {mobile.map((space) => {
        const active = pathname.startsWith(space.href);
        return (
          <Link
            key={space.id}
            href={space.href}
            className={cn(
              "flex-1 flex flex-col items-center py-2 text-xs",
              active ? "text-primary" : "text-muted-foreground"
            )}
          >
            <span className="text-lg" aria-hidden>{space.icon}</span>
            {space.label.split(" ")[0]}
          </Link>
        );
      })}
    </nav>
  );
}
