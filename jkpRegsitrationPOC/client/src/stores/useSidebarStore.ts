import { create } from "zustand";
import { MOBILE_BREAKPOINT } from "@/constants";

interface SidebarState {
  isOpen: boolean;
  toggle: () => void;
  setOpen: (open: boolean) => void;
}

// Start expanded on desktop, closed on mobile (avoids flash of open drawer)
const isDesktop =
  typeof window !== "undefined" && window.innerWidth >= MOBILE_BREAKPOINT;

export const useSidebarStore = create<SidebarState>((set) => ({
  isOpen: isDesktop,
  toggle: () => set((s) => ({ isOpen: !s.isOpen })),
  setOpen: (open) => set({ isOpen: open }),
}));
