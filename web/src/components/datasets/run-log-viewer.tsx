"use client";

import { useRunStatus, useStopRun } from "@/hooks/use-runs";
import { StatusBadge } from "@/components/ui/status-badge";

interface Props {
  runId: string | null;
}

export function RunLogViewer({ runId }: Props) {
  const { data } = useRunStatus(runId, !!runId);
  const stopMutation = useStopRun();

  if (!runId || !data) return null;

  const isActive = data.status === "running" || data.status === "pending";

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-3">
        <StatusBadge status={data.status} />
        {isActive && (
          <button
            onClick={() => stopMutation.mutate(runId)}
            disabled={stopMutation.isPending}
            className="text-xs text-wybe-danger hover:text-red-300 transition-colors"
          >
            Stop
          </button>
        )}
      </div>
      {data.log_tail && (
        <pre className="bg-wybe-bg-primary border border-wybe-border rounded-lg p-3 text-xs text-wybe-text font-mono max-h-64 overflow-auto whitespace-pre-wrap">
          {data.log_tail}
        </pre>
      )}
    </div>
  );
}
