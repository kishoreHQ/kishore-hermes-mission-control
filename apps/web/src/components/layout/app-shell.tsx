"use client";

import { Sidebar, MobileNav } from "./sidebar";
import { TopBar } from "./top-bar";
import { CommandPalette } from "../command-palette";
import { AIChatBar } from "../ai-chat-bar";

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen">
      <a href="#main-content" className="sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 bg-primary text-primary-foreground px-3 py-1 rounded">
        Skip to content
      </a>
      <Sidebar />
      <div className="md:pl-60 flex flex-col min-h-screen pb-16 md:pb-0">
        <TopBar />
        <main id="main-content" className="flex-1 px-4 py-6 md:px-8 max-w-7xl mx-auto w-full">
          {children}
        </main>
      </div>
      <MobileNav />
      <CommandPalette />
      <AIChatBar />
    </div>
  );
}
