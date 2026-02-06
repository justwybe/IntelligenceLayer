"use client";

import { useState } from "react";
import { useModelsConstants, useBenchmarkMetrics } from "@/hooks/use-models";
import { useCreateRun, useRunStatus } from "@/hooks/use-runs";
import type { BenchmarkRow } from "@/types";

interface Props {
  projectId: string | null;
}

const BAR_COLORS = ["#3b82f6", "#eab308", "#22c55e", "#ef4444", "#a855f7", "#06b6d4"];

export function BenchmarkForm({ projectId }: Props) {
  const { data: constants } = useModelsConstants();
  const createRun = useCreateRun(projectId);

  const [modelPath, setModelPath] = useState("");
  const [trtPath, setTrtPath] = useState("");
  const [embodiment, setEmbodiment] = useState("new_embodiment");
  const [numIters, setNumIters] = useState(100);
  const [skipCompile, setSkipCompile] = useState(false);
  const [runId, setRunId] = useState<string | null>(null);

  const { data: runStatus } = useRunStatus(runId);
  const { data: benchMetrics } = useBenchmarkMetrics(runId);

  const embodimentChoices = constants?.embodiment_choices ?? ["new_embodiment"];

  function handleLaunch() {
    if (!modelPath.trim() || !projectId) return;
    createRun.mutate(
      {
        run_type: "benchmark",
        config: {
          model_path: modelPath,
          embodiment_tag: embodiment,
          num_iterations: numIters,
          trt_engine_path: trtPath.trim() || null,
          skip_compile: skipCompile,
        },
      },
      { onSuccess: (run) => setRunId(run.id) },
    );
  }

  const rows: BenchmarkRow[] = benchMetrics?.rows ?? [];

  // Parse E2E values for the bar chart
  const chartData = rows.map((r) => {
    const val = parseFloat(r.e2e.replace(/ms/gi, "").trim()) || 0;
    return { mode: r.mode, value: val };
  });
  const maxVal = Math.max(...chartData.map((d) => d.value), 1);

  return (
    <div className="space-y-4">
      <h2 className="text-sm font-semibold text-wybe-text-bright">
        Benchmark Inference
      </h2>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-xs text-wybe-text-muted mb-1">
            Model Path
          </label>
          <input
            type="text"
            value={modelPath}
            onChange={(e) => setModelPath(e.target.value)}
            placeholder="/path/to/model"
            className="w-full bg-wybe-bg-tertiary border border-wybe-border rounded px-3 py-1.5 text-sm text-wybe-text focus:outline-none focus:border-wybe-accent"
          />
        </div>
        <div>
          <label className="block text-xs text-wybe-text-muted mb-1">
            TensorRT Engine Path (optional)
          </label>
          <input
            type="text"
            value={trtPath}
            onChange={(e) => setTrtPath(e.target.value)}
            className="w-full bg-wybe-bg-tertiary border border-wybe-border rounded px-3 py-1.5 text-sm text-wybe-text focus:outline-none focus:border-wybe-accent"
          />
        </div>
      </div>

      <div className="grid grid-cols-3 gap-3">
        <div>
          <label className="block text-xs text-wybe-text-muted mb-1">
            Embodiment Tag
          </label>
          <select
            value={embodiment}
            onChange={(e) => setEmbodiment(e.target.value)}
            className="w-full bg-wybe-bg-tertiary border border-wybe-border rounded px-3 py-1.5 text-sm text-wybe-text focus:outline-none focus:border-wybe-accent"
          >
            {embodimentChoices.map((e) => (
              <option key={e} value={e}>
                {e}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-xs text-wybe-text-muted mb-1">
            Num Iterations: {numIters}
          </label>
          <input
            type="range"
            value={numIters}
            onChange={(e) => setNumIters(parseInt(e.target.value))}
            min={10}
            max={1000}
            step={10}
            className="w-full accent-wybe-accent"
          />
        </div>
        <div className="flex items-end pb-1">
          <label className="flex items-center gap-2 text-sm text-wybe-text cursor-pointer">
            <input
              type="checkbox"
              checked={skipCompile}
              onChange={(e) => setSkipCompile(e.target.checked)}
              className="rounded border-wybe-border bg-wybe-bg-tertiary accent-wybe-accent"
            />
            Skip Compile
          </label>
        </div>
      </div>

      <button
        onClick={handleLaunch}
        disabled={!modelPath.trim() || !projectId || createRun.isPending}
        className="px-4 py-1.5 bg-wybe-accent text-wybe-bg-primary text-sm font-medium rounded hover:bg-wybe-accent-hover transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {createRun.isPending ? "Launching..." : "Run Benchmark"}
      </button>

      {createRun.isError && (
        <p className="text-xs text-wybe-danger">
          {(createRun.error as Error).message}
        </p>
      )}

      {runStatus && (
        <div className="text-xs text-wybe-text-muted">
          Status: <span className="text-wybe-text">{runStatus.status}</span>
        </div>
      )}

      {/* Results Table */}
      {rows.length > 0 && (
        <div className="bg-wybe-bg-secondary border border-wybe-border rounded-xl overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-wybe-border text-wybe-text-muted text-xs">
                <th className="text-left px-3 py-2 font-medium">Device</th>
                <th className="text-left px-3 py-2 font-medium">Mode</th>
                <th className="text-left px-3 py-2 font-medium">Data Processing</th>
                <th className="text-left px-3 py-2 font-medium">Backbone</th>
                <th className="text-left px-3 py-2 font-medium">Action Head</th>
                <th className="text-left px-3 py-2 font-medium">E2E</th>
                <th className="text-left px-3 py-2 font-medium">Frequency</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r, i) => (
                <tr
                  key={i}
                  className="border-b border-wybe-border last:border-0"
                >
                  <td className="px-3 py-2 text-wybe-text">{r.device}</td>
                  <td className="px-3 py-2 text-wybe-text">{r.mode}</td>
                  <td className="px-3 py-2 text-wybe-text-muted">
                    {r.data_processing}
                  </td>
                  <td className="px-3 py-2 text-wybe-text-muted">
                    {r.backbone}
                  </td>
                  <td className="px-3 py-2 text-wybe-text-muted">
                    {r.action_head}
                  </td>
                  <td className="px-3 py-2 text-wybe-text font-mono text-xs">
                    {r.e2e}
                  </td>
                  <td className="px-3 py-2 text-wybe-text font-mono text-xs">
                    {r.frequency}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Simple Bar Chart */}
      {chartData.length > 0 && (
        <div className="bg-wybe-bg-secondary border border-wybe-border rounded-xl p-4">
          <h3 className="text-xs font-semibold text-wybe-text-bright mb-3">
            Inference Timing (E2E Latency ms)
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
                <span className="text-xs text-wybe-text-muted mt-1 truncate max-w-full">
                  {d.mode}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
