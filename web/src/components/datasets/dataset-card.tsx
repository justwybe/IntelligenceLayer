"use client";

import type { Dataset } from "@/types";
import { SourceBadge } from "./source-badge";

interface Props {
  dataset: Dataset;
  onDelete?: (id: string) => void;
}

export function DatasetCard({ dataset, onDelete }: Props) {
  return (
    <div className="bg-wybe-bg-secondary border border-wybe-border rounded-lg p-4 flex flex-col gap-2">
      <div className="flex items-start justify-between gap-2">
        <h3 className="text-sm font-semibold text-wybe-text-bright truncate">
          {dataset.name}
        </h3>
        <SourceBadge source={dataset.source} />
      </div>

      <p className="text-xs text-wybe-text-muted truncate" title={dataset.path}>
        {dataset.path}
      </p>

      <div className="flex items-center justify-between mt-auto pt-2 border-t border-wybe-border">
        <span className="text-xs text-wybe-text-muted">
          {dataset.episode_count != null
            ? `${dataset.episode_count} episodes`
            : "unknown episodes"}
        </span>
        {onDelete && (
          <button
            onClick={() => onDelete(dataset.id)}
            className="text-xs text-wybe-text-muted hover:text-wybe-danger transition-colors"
          >
            Delete
          </button>
        )}
      </div>
    </div>
  );
}
