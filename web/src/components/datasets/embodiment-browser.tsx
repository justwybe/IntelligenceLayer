"use client";

import { useState } from "react";
import { useDatasetConstants, useEmbodimentConfig } from "@/hooks/use-datasets";

export function EmbodimentBrowser() {
  const { data: constants } = useDatasetConstants();
  const [tag, setTag] = useState("libero_panda");
  const { data: config, isLoading, isError, error } = useEmbodimentConfig(tag);

  const choices = constants?.embodiment_choices ?? [];

  return (
    <div className="space-y-3">
      <div className="flex items-end gap-3">
        <div>
          <label className="block text-xs text-wybe-text-muted mb-1">
            Embodiment Tag
          </label>
          <select
            value={tag}
            onChange={(e) => setTag(e.target.value)}
            className="bg-wybe-bg-tertiary border border-wybe-border rounded px-3 py-1.5 text-sm text-wybe-text focus:outline-none focus:border-wybe-accent"
          >
            {choices.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </div>
      </div>

      {isLoading && (
        <p className="text-xs text-wybe-text-muted">Loading config...</p>
      )}

      {isError && (
        <p className="text-xs text-wybe-danger">
          {(error as Error).message}
        </p>
      )}

      {config && (
        <pre className="bg-wybe-bg-primary border border-wybe-border rounded-lg p-3 text-xs text-wybe-text font-mono max-h-96 overflow-auto whitespace-pre-wrap">
          {JSON.stringify(config, null, 2)}
        </pre>
      )}
    </div>
  );
}
