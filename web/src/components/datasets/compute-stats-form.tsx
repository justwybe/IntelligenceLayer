"use client";

import { useState } from "react";
import { useDatasets, useDatasetConstants } from "@/hooks/use-datasets";
import { useCreateRun } from "@/hooks/use-runs";
import { RunLogViewer } from "./run-log-viewer";

interface Props {
  projectId: string | null;
}

export function ComputeStatsForm({ projectId }: Props) {
  const { data: datasets } = useDatasets(projectId);
  const { data: constants } = useDatasetConstants();
  const createRun = useCreateRun(projectId);

  const [selectedDataset, setSelectedDataset] = useState("");
  const [embodiment, setEmbodiment] = useState("new_embodiment");
  const [activeRunId, setActiveRunId] = useState<string | null>(null);

  const embodimentChoices = constants?.embodiment_choices ?? [];

  function handleCompute() {
    const datasetPath = selectedDataset.includes("|")
      ? selectedDataset.split("|")[1].trim()
      : selectedDataset;
    if (!datasetPath.trim() || !projectId) return;

    createRun.mutate(
      {
        run_type: "stats_computation",
        config: {
          dataset_path: datasetPath,
          embodiment_tag: embodiment,
        },
      },
      {
        onSuccess: (run) => setActiveRunId(run.id),
      },
    );
  }

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div>
          <label className="block text-xs text-wybe-text-muted mb-1">Dataset</label>
          <select
            value={selectedDataset}
            onChange={(e) => setSelectedDataset(e.target.value)}
            className="w-full bg-wybe-bg-tertiary border border-wybe-border rounded px-3 py-1.5 text-sm text-wybe-text focus:outline-none focus:border-wybe-accent"
          >
            <option value="">Select dataset...</option>
            {datasets?.map((ds) => (
              <option key={ds.id} value={`${ds.name} | ${ds.path}`}>
                {ds.name}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-xs text-wybe-text-muted mb-1">
            Embodiment Tag
          </label>
          <select
            value={embodiment}
            onChange={(e) => setEmbodiment(e.target.value)}
            className="w-full bg-wybe-bg-tertiary border border-wybe-border rounded px-3 py-1.5 text-sm text-wybe-text focus:outline-none focus:border-wybe-accent"
          >
            {embodimentChoices.map((e) => (
              <option key={e} value={e}>
                {e}
              </option>
            ))}
          </select>
        </div>
      </div>

      <button
        onClick={handleCompute}
        disabled={!projectId || !selectedDataset || createRun.isPending}
        className="px-4 py-1.5 bg-wybe-accent text-wybe-bg-primary text-sm font-medium rounded hover:bg-wybe-accent-hover transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {createRun.isPending ? "Launching..." : "Compute Stats"}
      </button>

      {createRun.isError && (
        <p className="text-xs text-wybe-danger">
          {(createRun.error as Error).message}
        </p>
      )}

      <RunLogViewer runId={activeRunId} />
    </div>
  );
}
