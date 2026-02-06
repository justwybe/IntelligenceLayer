"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api-client";
import type { Project } from "@/types";
import { useProjectStore } from "@/stores/project-store";

export function ShellBar() {
  const { currentProjectId, setCurrentProjectId, toggleSidebar, toggleAssistant } =
    useProjectStore();

  const queryClient = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState("");
  const [embodiment, setEmbodiment] = useState("new_embodiment");
  const [baseModel, setBaseModel] = useState("nvidia/GR00T-N1.6-3B");

  const { data } = useQuery({
    queryKey: ["projects"],
    queryFn: () =>
      api.get<{ projects: Project[] }>("/api/projects").then((r) => r.projects),
    staleTime: 30_000,
  });

  const createProject = useMutation({
    mutationFn: (body: { name: string; embodiment_tag: string; base_model: string }) =>
      api.post<Project>("/api/projects", body),
    onSuccess: (project) => {
      queryClient.invalidateQueries({ queryKey: ["projects"] });
      setCurrentProjectId(project.id);
      setShowForm(false);
      setName("");
    },
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

      {/* New Project button */}
      <div className="relative">
        <button
          onClick={() => setShowForm(!showForm)}
          className="bg-wybe-accent/10 border border-wybe-accent/30 rounded-lg px-2.5 py-1.5 text-sm text-wybe-accent hover:bg-wybe-accent/20 transition-colors"
        >
          + New
        </button>

        {showForm && (
          <div className="absolute top-full left-0 mt-2 w-72 bg-wybe-bg-secondary border border-wybe-border rounded-lg p-4 shadow-lg z-50">
            <h3 className="text-sm font-semibold text-wybe-text-bright mb-3">
              New Project
            </h3>
            <form
              onSubmit={(e) => {
                e.preventDefault();
                if (!name.trim()) return;
                createProject.mutate({
                  name: name.trim(),
                  embodiment_tag: embodiment,
                  base_model: baseModel,
                });
              }}
              className="space-y-2"
            >
              <input
                type="text"
                placeholder="Project name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full bg-wybe-bg-tertiary border border-wybe-border rounded px-3 py-1.5 text-sm text-wybe-text focus:outline-none focus:border-wybe-accent"
                autoFocus
              />
              <input
                type="text"
                placeholder="Embodiment tag"
                value={embodiment}
                onChange={(e) => setEmbodiment(e.target.value)}
                className="w-full bg-wybe-bg-tertiary border border-wybe-border rounded px-3 py-1.5 text-sm text-wybe-text focus:outline-none focus:border-wybe-accent"
              />
              <input
                type="text"
                placeholder="Base model"
                value={baseModel}
                onChange={(e) => setBaseModel(e.target.value)}
                className="w-full bg-wybe-bg-tertiary border border-wybe-border rounded px-3 py-1.5 text-sm text-wybe-text focus:outline-none focus:border-wybe-accent"
              />
              <div className="flex gap-2 pt-1">
                <button
                  type="submit"
                  disabled={!name.trim() || createProject.isPending}
                  className="flex-1 bg-wybe-accent text-wybe-bg-primary text-sm font-medium py-1.5 rounded hover:bg-wybe-accent-hover transition-colors disabled:opacity-50"
                >
                  {createProject.isPending ? "Creating..." : "Create"}
                </button>
                <button
                  type="button"
                  onClick={() => setShowForm(false)}
                  className="px-3 py-1.5 text-sm text-wybe-text-muted hover:text-wybe-text transition-colors"
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        )}
      </div>

      <div className="flex-1" />

      {/* Assistant toggle */}
      <button
        onClick={toggleAssistant}
        className="bg-wybe-accent/10 border border-wybe-accent/30 rounded-lg px-3 py-1.5 text-sm text-wybe-accent hover:bg-wybe-accent/20 transition-colors"
      >
        Assistant
      </button>

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
