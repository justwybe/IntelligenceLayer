"use client";

import { useRunStatus } from "@/hooks/use-runs";
import { useEvalMetrics } from "@/hooks/use-simulation";
import { StatusBadge } from "@/components/ui/status-badge";
import { EvalMetricsTable } from "./eval-metrics-table";

interface Props {
  runId: string | null;
}

export function IsaacSimMonitor({ runId }: Props) {
  const { data: runStatus } = useRunStatus(runId, !!runId);
  const { data: evalMetrics } = useEvalMetrics(runId, !!runId);

  if (!runId) {
    return (
      <div className="flex items-center justify-center h-64 text-sm text-wybe-text-muted">
        Launch a simulation to see monitoring here
      </div>
    );
  }

  const status = runStatus?.status ?? "pending";

  return (
    <div className="space-y-4">
      {/* Status */}
      <div className="flex items-center gap-3">
        <StatusBadge status={status} />
        <span className="text-xs text-wybe-text-muted font-mono">
          {runId.slice(0, 8)}
        </span>
      </div>

      {/* Log tail */}
      {runStatus?.log_tail && (
        <div>
          <p className="text-xs font-semibold text-wybe-text-bright mb-1">
            Log Output
          </p>
          <pre className="bg-wybe-bg-primary border border-wybe-border rounded-lg p-3 text-xs text-wybe-text font-mono max-h-48 overflow-auto whitespace-pre-wrap">
            {runStatus.log_tail}
          </pre>
        </div>
      )}

      {/* Metrics */}
      {evalMetrics && (
        <div>
          <p className="text-xs font-semibold text-wybe-text-bright mb-1">
            Results
          </p>
          <div className="bg-wybe-bg-primary border border-wybe-border rounded-lg p-3">
            <EvalMetricsTable metrics={evalMetrics} />
          </div>
        </div>
      )}
    </div>
  );
}
