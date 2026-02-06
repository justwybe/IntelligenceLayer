"use client";

import { useState } from "react";
import { useInspectDataset } from "@/hooks/use-datasets";

export function DatasetInspector() {
  const [path, setPath] = useState("");
  const inspectMutation = useInspectDataset();

  function handleInspect() {
    if (!path.trim()) return;
    inspectMutation.mutate(path.trim());
  }

  const data = inspectMutation.data;

  return (
    <div className="space-y-3">
      <div className="flex items-end gap-3">
        <div className="flex-1">
          <label className="block text-xs text-wybe-text-muted mb-1">
            Dataset Path
          </label>
          <input
            type="text"
            value={path}
            onChange={(e) => setPath(e.target.value)}
            placeholder="/path/to/dataset"
            className="w-full bg-wybe-bg-tertiary border border-wybe-border rounded px-3 py-1.5 text-sm text-wybe-text placeholder:text-wybe-text-muted/50 focus:outline-none focus:border-wybe-accent"
          />
        </div>
        <button
          onClick={handleInspect}
          disabled={inspectMutation.isPending}
          className="px-4 py-1.5 bg-wybe-bg-tertiary border border-wybe-border text-sm text-wybe-text rounded hover:bg-wybe-bg-hover transition-colors disabled:opacity-50"
        >
          {inspectMutation.isPending ? "Loading..." : "Inspect"}
        </button>
      </div>

      {inspectMutation.isError && (
        <p className="text-xs text-wybe-danger">
          {(inspectMutation.error as Error).message}
        </p>
      )}

      {data && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
          <MetaBlock label="info.json" content={data.info} />
          <MetaBlock label="modality.json" content={data.modality} />
          <MetaBlock label="tasks.jsonl" content={data.tasks} />
          <MetaBlock label="stats.json (summary)" content={data.stats} />
        </div>
      )}
    </div>
  );
}

function MetaBlock({ label, content }: { label: string; content: string }) {
  if (!content) {
    return (
      <div className="bg-wybe-bg-primary border border-wybe-border rounded-lg p-3">
        <h4 className="text-xs font-medium text-wybe-text-muted mb-1">{label}</h4>
        <p className="text-xs text-wybe-text-muted italic">Not found</p>
      </div>
    );
  }

  return (
    <div className="bg-wybe-bg-primary border border-wybe-border rounded-lg p-3">
      <h4 className="text-xs font-medium text-wybe-text-muted mb-1">{label}</h4>
      <pre className="text-xs text-wybe-text font-mono max-h-48 overflow-auto whitespace-pre-wrap">
        {content}
      </pre>
    </div>
  );
}
