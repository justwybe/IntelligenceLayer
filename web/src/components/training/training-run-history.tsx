"use client";

import { useRuns } from "@/hooks/use-runs";
import { StatusBadge } from "@/components/ui/status-badge";
import type { Run } from "@/types";

interface Props {
  projectId: string | null;
}

function parseConfig(run: Run): Record<string, unknown> {
  try {
    return typeof run.config === "string" ? JSON.parse(run.config) : run.config;
  } catch {
    return {};
  }
}

function parseMetrics(run: Run): Record<string, unknown> {
  try {
    return run.metrics ? JSON.parse(run.metrics) : {};
  } catch {
    return {};
  }
}

export function TrainingRunHistory({ projectId }: Props) {
  const { data: trainingRuns } = useRuns(projectId, "training");
  const { data: rlRuns } = useRuns(projectId, "rl_training");

  const allRuns = [...(trainingRuns ?? []), ...(rlRuns ?? [])].sort(
    (a, b) => (b.started_at ?? "").localeCompare(a.started_at ?? ""),
  );

  if (allRuns.length === 0) {
    return (
      <p className="text-xs text-wybe-text-muted">No training runs yet</p>
    );
  }

  return (
    <div className="overflow-auto">
      <table className="w-full text-xs">
        <thead>
          <tr className="text-wybe-text-muted border-b border-wybe-border">
            <th className="text-left py-2 pr-3 font-medium">Run ID</th>
            <th className="text-left py-2 pr-3 font-medium">Dataset</th>
            <th className="text-left py-2 pr-3 font-medium">Status</th>
            <th className="text-left py-2 pr-3 font-medium">Loss</th>
            <th className="text-left py-2 pr-3 font-medium">Step</th>
            <th className="text-left py-2 font-medium">Started</th>
          </tr>
        </thead>
        <tbody>
          {allRuns.map((run) => {
            const config = parseConfig(run);
            const metrics = parseMetrics(run);
            const dataset = String(
              config.dataset_path ?? config.environment ?? "-",
            );
            const displayDataset =
              dataset.length > 40 ? "..." + dataset.slice(-37) : dataset;

            return (
              <tr
                key={run.id}
                className="border-b border-wybe-border/50 hover:bg-wybe-bg-secondary transition-colors"
              >
                <td className="py-2 pr-3 font-mono text-wybe-text">
                  {run.id.slice(0, 8)}
                </td>
                <td className="py-2 pr-3 text-wybe-text truncate max-w-[200px]">
                  {displayDataset}
                </td>
                <td className="py-2 pr-3">
                  <StatusBadge status={run.status} />
                </td>
                <td className="py-2 pr-3 text-wybe-text-muted">
                  {metrics.loss != null ? String(metrics.loss) : "-"}
                </td>
                <td className="py-2 pr-3 text-wybe-text-muted">
                  {metrics.step != null ? String(metrics.step) : "-"}
                </td>
                <td className="py-2 text-wybe-text-muted">
                  {run.started_at ? run.started_at.slice(0, 16) : "-"}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
