import { create } from "zustand";
import type { SpaceId } from "@/lib/spaces";

interface UIState {
  commandPaletteOpen: boolean;
  aiChatOpen: boolean;
  drawerOpen: boolean;
  drawerContent: { type: string; id: string } | null;
  setCommandPaletteOpen: (open: boolean) => void;
  setAiChatOpen: (open: boolean) => void;
  openDrawer: (type: string, id: string) => void;
  closeDrawer: () => void;
}

export const useUIStore = create<UIState>((set) => ({
  commandPaletteOpen: false,
  aiChatOpen: false,
  drawerOpen: false,
  drawerContent: null,
  setCommandPaletteOpen: (open) => set({ commandPaletteOpen: open }),
  setAiChatOpen: (open) => set({ aiChatOpen: open }),
  openDrawer: (type, id) => set({ drawerOpen: true, drawerContent: { type, id } }),
  closeDrawer: () => set({ drawerOpen: false, drawerContent: null }),
}));
