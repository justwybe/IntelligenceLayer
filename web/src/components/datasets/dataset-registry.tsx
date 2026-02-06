"use client";

import { useDatasets, useDeleteDataset } from "@/hooks/use-datasets";
import { DatasetCard } from "./dataset-card";

interface Props {
  projectId: string | null;
}

export function DatasetRegistry({ projectId }: Props) {
  const { data: datasets, isLoading } = useDatasets(projectId);
  const deleteMutation = useDeleteDataset(projectId);

  if (!projectId) {
    return (
      <p className="text-sm text-wybe-text-muted">Select a project first.</p>
    );
  }

  if (isLoading) {
    return <p className="text-sm text-wybe-text-muted">Loading datasets...</p>;
  }

  if (!datasets || datasets.length === 0) {
    return (
      <p className="text-sm text-wybe-text-muted">
        No datasets registered yet. Import one above.
      </p>
    );
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
      {datasets.map((ds) => (
        <DatasetCard
          key={ds.id}
          dataset={ds}
          onDelete={(id) => {
            if (confirm(`Delete dataset "${ds.name}"?`)) {
              deleteMutation.mutate(id);
            }
          }}
        />
      ))}
    </div>
  );
}
