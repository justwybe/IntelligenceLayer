"use client";

import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api-client";
import type { Project } from "@/types";
import { useProjectStore } from "@/stores/project-store";

export function ShellBar() {
  const { currentProjectId, setCurrentProjectId, toggleSidebar } =
    useProjectStore();

  const { data } = useQuery({
    queryKey: ["projects"],
    queryFn: () =>
      api.get<{ projects: Project[] }>("/api/projects").then((r) => r.projects),
    staleTime: 30_000,
  });

  const projects = data ?? [];

  return (
    <header className="flex items-center gap-3 border-b border-wybe-border bg-wybe-bg-secondary px-5 h-14 sticky top-0 z-50">
      {/* Logo */}
      <span className="text-xl font-bold text-wybe-text-bright tracking-tight select-none">
        wybe<span className="text-wybe-accent">.</span>
      </span>

      {/* Project selector */}
      <select
        className="bg-wybe-bg-tertiary border border-wybe-border rounded-lg px-3 py-1.5 text-sm text-wybe-text w-52 focus:outline-none focus:border-wybe-accent"
        value={currentProjectId ?? ""}
        onChange={(e) => setCurrentProjectId(e.target.value || null)}
      >
        <option value="">Select Project</option>
        {projects.map((p) => (
          <option key={p.id} value={p.id}>
            {p.name}
          </option>
        ))}
      </select>

      <div className="flex-1" />

      {/* Dashboard toggle */}
      <button
        onClick={toggleSidebar}
        className="bg-wybe-bg-tertiary border border-wybe-border rounded-lg px-3 py-1.5 text-sm text-wybe-text-muted hover:border-wybe-accent hover:text-wybe-text transition-colors"
      >
        Dashboard
      </button>
    </header>
  );
}
