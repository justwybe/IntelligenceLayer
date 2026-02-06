"use client";

import { useState } from "react";
import { useCreateRun } from "@/hooks/use-runs";
import { RunLogViewer } from "./run-log-viewer";

interface Props {
  projectId: string | null;
}

export function ConvertDatasetForm({ projectId }: Props) {
  const [repoId, setRepoId] = useState("");
  const [outputDir, setOutputDir] = useState("");
  const [activeRunId, setActiveRunId] = useState<string | null>(null);
  const createRun = useCreateRun(projectId);

  function handleConvert() {
    if (!repoId.trim() || !outputDir.trim() || !projectId) return;
    createRun.mutate(
      {
        run_type: "conversion",
        config: { repo_id: repoId.trim(), output_dir: outputDir.trim() },
      },
      {
        onSuccess: (run) => setActiveRunId(run.id),
      },
    );
  }

  return (
    <div className="space-y-3">
      <p className="text-xs text-wybe-text-muted">
        Download and convert a LeRobot v3 dataset from HuggingFace to v2 format.
      </p>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div>
          <label className="block text-xs text-wybe-text-muted mb-1">
            HuggingFace Repo ID
          </label>
          <input
            type="text"
            value={repoId}
            onChange={(e) => setRepoId(e.target.value)}
            placeholder="lerobot/aloha_sim_insertion_human"
            className="w-full bg-wybe-bg-tertiary border border-wybe-border rounded px-3 py-1.5 text-sm text-wybe-text placeholder:text-wybe-text-muted/50 focus:outline-none focus:border-wybe-accent"
          />
        </div>
        <div>
          <label className="block text-xs text-wybe-text-muted mb-1">
            Output Directory
          </label>
          <input
            type="text"
            value={outputDir}
            onChange={(e) => setOutputDir(e.target.value)}
            placeholder="/path/to/output"
            className="w-full bg-wybe-bg-tertiary border border-wybe-border rounded px-3 py-1.5 text-sm text-wybe-text placeholder:text-wybe-text-muted/50 focus:outline-none focus:border-wybe-accent"
          />
        </div>
      </div>

      <button
        onClick={handleConvert}
        disabled={!projectId || !repoId.trim() || !outputDir.trim() || createRun.isPending}
        className="px-4 py-1.5 bg-wybe-accent text-wybe-bg-primary text-sm font-medium rounded hover:bg-wybe-accent-hover transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {createRun.isPending ? "Launching..." : "Convert"}
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
