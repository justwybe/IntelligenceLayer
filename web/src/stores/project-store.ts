import { create } from "zustand";
import { persist } from "zustand/middleware";

interface ProjectStore {
  currentProjectId: string | null;
  sidebarVisible: boolean;
  assistantVisible: boolean;
  setCurrentProjectId: (id: string | null) => void;
  toggleSidebar: () => void;
  setSidebarVisible: (visible: boolean) => void;
  toggleAssistant: () => void;
  setAssistantVisible: (visible: boolean) => void;
}

export const useProjectStore = create<ProjectStore>()(
  persist(
    (set) => ({
      currentProjectId: null,
      sidebarVisible: false,
      assistantVisible: false,
      setCurrentProjectId: (id) => set({ currentProjectId: id }),
      toggleSidebar: () =>
        set((state) => ({ sidebarVisible: !state.sidebarVisible })),
      setSidebarVisible: (visible) => set({ sidebarVisible: visible }),
      toggleAssistant: () =>
        set((state) => ({ assistantVisible: !state.assistantVisible })),
      setAssistantVisible: (visible) => set({ assistantVisible: visible }),
    }),
    { name: "wybe-project-store" },
  ),
);
