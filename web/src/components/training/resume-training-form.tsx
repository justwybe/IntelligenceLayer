"use client";

import { useState } from "react";

interface Props {
  onResume: (checkpointPath: string) => void;
  isPending: boolean;
}

export function ResumeTrainingForm({ onResume, isPending }: Props) {
  const [checkpointPath, setCheckpointPath] = useState("");

  return (
    <div className="space-y-2">
      <div>
        <label className="block text-xs text-wybe-text-muted mb-1">
          Checkpoint Path
        </label>
        <input
          type="text"
          value={checkpointPath}
          onChange={(e) => setCheckpointPath(e.target.value)}
          placeholder="/path/to/checkpoint-5000"
          className="w-full bg-wybe-bg-tertiary border border-wybe-border rounded px-3 py-1.5 text-sm text-wybe-text focus:outline-none focus:border-wybe-accent"
        />
      </div>
      <button
        onClick={() => {
          if (checkpointPath.trim()) onResume(checkpointPath.trim());
        }}
        disabled={!checkpointPath.trim() || isPending}
        className="px-3 py-1.5 bg-wybe-accent text-wybe-bg-primary text-xs font-medium rounded hover:bg-wybe-accent-hover transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {isPending ? "Launching..." : "Resume Training"}
      </button>
    </div>
  );
}
