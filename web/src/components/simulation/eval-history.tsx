"use client";

import { useRuns } from "@/hooks/use-runs";
import { StatusBadge } from "@/components/ui/status-badge";
import type { Run } from "@/types";

interface Props {
  projectId: string | null;
}

const EVAL_TYPES = new Set(["evaluation", "simulation", "benchmark"]);

function parseMetrics(run: Run): string {
  if (!run.metrics) return "-";
  try {
    const m = JSON.parse(run.metrics);
    return Object.entries(m)
      .slice(0, 3)
      .map(([k, v]) => `${k}=${v}`)
      .join(", ");
  } catch {
    return "-";
  }
}

export function EvalHistory({ projectId }: Props) {
  const { data: runs } = useRuns(projectId);
  const evalRuns = runs?.filter((r) => EVAL_TYPES.has(r.run_type)) ?? [];

  if (evalRuns.length === 0) {
    return (
      <p className="text-xs text-wybe-text-muted py-4 text-center">
        No evaluation runs yet
      </p>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs">
        <thead>
          <tr className="border-b border-wybe-border">
            <th className="text-left py-2 text-wybe-text-muted font-medium">
              Run ID
            </th>
            <th className="text-left py-2 text-wybe-text-muted font-medium">
              Type
            </th>
            <th className="text-left py-2 text-wybe-text-muted font-medium">
              Status
            </th>
            <th className="text-left py-2 text-wybe-text-muted font-medium">
              Metrics
            </th>
            <th className="text-left py-2 text-wybe-text-muted font-medium">
              Started
            </th>
          </tr>
        </thead>
        <tbody>
          {evalRuns.map((r) => (
            <tr key={r.id} className="border-b border-wybe-border/50">
              <td className="py-2 text-wybe-text font-mono">
                {r.id.slice(0, 8)}
              </td>
              <td className="py-2 text-wybe-text">{r.run_type}</td>
              <td className="py-2">
                <StatusBadge status={r.status} />
              </td>
              <td className="py-2 text-wybe-text">{parseMetrics(r)}</td>
              <td className="py-2 text-wybe-text-muted">
                {r.started_at?.slice(0, 16) ?? "-"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
