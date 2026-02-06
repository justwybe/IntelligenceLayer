"use client";

import type { EvalMetrics } from "@/types";

interface Props {
  metrics: EvalMetrics;
}

export function EvalMetricsTable({ metrics }: Props) {
  const hasSimMetrics = metrics.sim_metrics.length > 0;
  const hasEvalMetrics = metrics.eval_metrics.length > 0;

  if (!hasSimMetrics && !hasEvalMetrics) {
    return (
      <p className="text-xs text-wybe-text-muted">
        No metrics available yet
      </p>
    );
  }

  return (
    <div className="space-y-3">
      {hasSimMetrics && (
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-wybe-border">
              <th className="text-left py-1.5 text-wybe-text-muted font-medium">
                Metric
              </th>
              <th className="text-right py-1.5 text-wybe-text-muted font-medium">
                Value
              </th>
            </tr>
          </thead>
          <tbody>
            {metrics.sim_metrics.map((m) => (
              <tr key={m.name} className="border-b border-wybe-border/50">
                <td className="py-1.5 text-wybe-text">{m.name}</td>
                <td className="py-1.5 text-right text-wybe-text font-mono">
                  {m.value}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {hasEvalMetrics && (
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-wybe-border">
              <th className="text-left py-1.5 text-wybe-text-muted font-medium">
                Trajectory
              </th>
              <th className="text-right py-1.5 text-wybe-text-muted font-medium">
                MSE
              </th>
              <th className="text-right py-1.5 text-wybe-text-muted font-medium">
                MAE
              </th>
            </tr>
          </thead>
          <tbody>
            {metrics.eval_metrics.map((m) => (
              <tr
                key={m.trajectory}
                className="border-b border-wybe-border/50"
              >
                <td className="py-1.5 text-wybe-text">{m.trajectory}</td>
                <td className="py-1.5 text-right text-wybe-text font-mono">
                  {m.mse.toExponential(3)}
                </td>
                <td className="py-1.5 text-right text-wybe-text font-mono">
                  {m.mae.toExponential(3)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
