import { create } from "zustand";
import { persist } from "zustand/middleware";

interface ProjectStore {
  currentProjectId: string | null;
  sidebarVisible: boolean;
  setCurrentProjectId: (id: string | null) => void;
  toggleSidebar: () => void;
  setSidebarVisible: (visible: boolean) => void;
}

export const useProjectStore = create<ProjectStore>()(
  persist(
    (set) => ({
      currentProjectId: null,
      sidebarVisible: false,
      setCurrentProjectId: (id) => set({ currentProjectId: id }),
      toggleSidebar: () =>
        set((state) => ({ sidebarVisible: !state.sidebarVisible })),
      setSidebarVisible: (visible) => set({ sidebarVisible: visible }),
    }),
    { name: "wybe-project-store" },
  ),
);
