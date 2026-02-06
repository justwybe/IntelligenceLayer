"use client";

import { useState } from "react";
import { useCreateDataset, useDatasetConstants } from "@/hooks/use-datasets";

interface Props {
  projectId: string | null;
  defaultSource?: string;
}

export function ImportDatasetForm({ projectId, defaultSource = "imported" }: Props) {
  const [name, setName] = useState("");
  const [path, setPath] = useState("");
  const [source, setSource] = useState(defaultSource);
  const createMutation = useCreateDataset(projectId);
  const { data: constants } = useDatasetConstants();

  const sourceOptions = constants?.source_options ?? [
    "imported",
    "recorded",
    "mimic",
    "dreams",
    "urban_memory",
  ];

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim() || !path.trim() || !projectId) return;
    createMutation.mutate(
      { name: name.trim(), path: path.trim(), source },
      {
        onSuccess: () => {
          setName("");
          setPath("");
        },
      },
    );
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div>
          <label className="block text-xs text-wybe-text-muted mb-1">Name</label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="cube_to_bowl_training"
            className="w-full bg-wybe-bg-tertiary border border-wybe-border rounded px-3 py-1.5 text-sm text-wybe-text placeholder:text-wybe-text-muted/50 focus:outline-none focus:border-wybe-accent"
          />
        </div>
        <div>
          <label className="block text-xs text-wybe-text-muted mb-1">
            Dataset Path
          </label>
          <input
            type="text"
            value={path}
            onChange={(e) => setPath(e.target.value)}
            placeholder="/path/to/lerobot_v2_dataset"
            className="w-full bg-wybe-bg-tertiary border border-wybe-border rounded px-3 py-1.5 text-sm text-wybe-text placeholder:text-wybe-text-muted/50 focus:outline-none focus:border-wybe-accent"
          />
        </div>
      </div>

      <div className="flex items-end gap-3">
        <div>
          <label className="block text-xs text-wybe-text-muted mb-1">Source</label>
          <select
            value={source}
            onChange={(e) => setSource(e.target.value)}
            className="bg-wybe-bg-tertiary border border-wybe-border rounded px-3 py-1.5 text-sm text-wybe-text focus:outline-none focus:border-wybe-accent"
          >
            {sourceOptions.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </div>
        <button
          type="submit"
          disabled={!projectId || createMutation.isPending}
          className="px-4 py-1.5 bg-wybe-accent text-wybe-bg-primary text-sm font-medium rounded hover:bg-wybe-accent-hover transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {createMutation.isPending ? "Importing..." : "Import Dataset"}
        </button>
      </div>

      {createMutation.isSuccess && (
        <p className="text-xs text-wybe-success">
          Dataset registered: {createMutation.data.id}
          {createMutation.data.episode_count != null &&
            ` (${createMutation.data.episode_count} episodes)`}
        </p>
      )}
      {createMutation.isError && (
        <p className="text-xs text-wybe-danger">
          {(createMutation.error as Error).message}
        </p>
      )}
    </form>
  );
}
