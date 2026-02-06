"use client";

import { useRuns } from "@/hooks/use-runs";
import { useQueryClient } from "@tanstack/react-query";

interface Props {
  projectId: string | null;
}

interface ParsedRun {
  model: string;
  mode: string;
  e2e: string;
  frequency: string;
  date: string;
}

const BAR_COLORS = ["#3b82f6", "#eab308", "#22c55e", "#ef4444", "#a855f7"];

export function BenchmarkHistory({ projectId }: Props) {
  const { data: runs } = useRuns(projectId, "benchmark");
  const qc = useQueryClient();

  const parsedRuns: ParsedRun[] = (runs ?? []).map((r) => {
    let metrics: Record<string, string> = {};
    let config: Record<string, string> = {};
    try {
      if (r.metrics) {
        metrics =
          typeof r.metrics === "string" ? JSON.parse(r.metrics) : r.metrics;
      }
      config = typeof r.config === "string" ? JSON.parse(r.config) : r.config;
    } catch {
      /* ignore */
    }
    let model = config.model_path ?? "-";
    if (model.length > 30) model = "..." + model.slice(-27);
    return {
      model,
      mode: metrics.mode ?? "-",
      e2e: String(metrics.e2e_ms ?? "-"),
      frequency: String(metrics.frequency_hz ?? "-"),
      date: r.started_at ? r.started_at.slice(0, 16) : "",
    };
  });

  // Chart data: frequency comparison
  const chartData = parsedRuns
    .map((r) => {
      const val = parseFloat(r.frequency.replace(/Hz/gi, "").trim());
      return isNaN(val) ? null : { label: r.model, value: val };
    })
    .filter((d): d is { label: string; value: number } => d !== null);

  const maxVal = Math.max(...chartData.map((d) => d.value), 1);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-wybe-text-bright">
          Benchmark History
        </h2>
        <button
          onClick={() =>
            qc.invalidateQueries({
              queryKey: ["runs", projectId, "benchmark"],
            })
          }
          className="px-3 py-1 text-xs font-medium bg-wybe-bg-tertiary text-wybe-text-muted rounded hover:text-wybe-text transition-colors"
        >
          Refresh
        </button>
      </div>

      <div className="bg-wybe-bg-secondary border border-wybe-border rounded-xl overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-wybe-border text-wybe-text-muted text-xs">
              <th className="text-left px-4 py-2 font-medium">Model</th>
              <th className="text-left px-4 py-2 font-medium">Mode</th>
              <th className="text-left px-4 py-2 font-medium">E2E (ms)</th>
              <th className="text-left px-4 py-2 font-medium">Freq (Hz)</th>
              <th className="text-left px-4 py-2 font-medium">Date</th>
            </tr>
          </thead>
          <tbody>
            {parsedRuns.length === 0 ? (
              <tr>
                <td
                  colSpan={5}
                  className="px-4 py-3 text-center text-wybe-text-muted"
                >
                  No benchmark runs
                </td>
              </tr>
            ) : (
              parsedRuns.map((r, i) => (
                <tr
                  key={i}
                  className="border-b border-wybe-border last:border-0"
                >
                  <td
                    className="px-4 py-2 text-wybe-text font-mono text-xs truncate max-w-[180px]"
                    title={r.model}
                  >
                    {r.model}
                  </td>
                  <td className="px-4 py-2 text-wybe-text-muted">{r.mode}</td>
                  <td className="px-4 py-2 text-wybe-text font-mono text-xs">
                    {r.e2e}
                  </td>
                  <td className="px-4 py-2 text-wybe-text font-mono text-xs">
                    {r.frequency}
                  </td>
                  <td className="px-4 py-2 text-wybe-text-muted text-xs">
                    {r.date}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Frequency Comparison Chart */}
      {chartData.length > 0 && (
        <div className="bg-wybe-bg-secondary border border-wybe-border rounded-xl p-4">
          <h3 className="text-xs font-semibold text-wybe-text-bright mb-3">
            Benchmark Frequency Comparison (Hz)
          </h3>
          <div className="flex items-end gap-4 h-40">
            {chartData.map((d, i) => (
              <div key={i} className="flex flex-col items-center flex-1">
                <div className="w-full flex flex-col items-center justify-end h-32">
                  <span className="text-xs text-wybe-text mb-1">
                    {d.value.toFixed(1)}
                  </span>
                  <div
                    className="w-full max-w-[40px] rounded-t"
                    style={{
                      height: `${(d.value / maxVal) * 100}%`,
                      backgroundColor: BAR_COLORS[i % BAR_COLORS.length],
                      minHeight: d.value > 0 ? "4px" : "0",
                    }}
                  />
                </div>
                <span className="text-xs text-wybe-text-muted mt-1 truncate max-w-full text-center">
                  {d.label}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
