"use client";

import { useCompareModels } from "@/hooks/use-simulation";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import type { CompareEntry } from "@/types";

interface Props {
  projectId: string | null;
}

function buildChartData(entries: CompareEntry[]) {
  // Collect all numeric metric keys
  const numericKeys = new Set<string>();
  for (const e of entries) {
    for (const [k, v] of Object.entries(e.metrics)) {
      if (typeof v === "number") numericKeys.add(k);
    }
  }

  if (numericKeys.size === 0) return { data: [], keys: [] };

  const data = entries.map((e) => ({
    model: e.model_name,
    ...Object.fromEntries(
      [...numericKeys].map((k) => [k, (e.metrics[k] as number) ?? 0]),
    ),
  }));

  return { data, keys: [...numericKeys].sort() };
}

const COLORS = ["#22c55e", "#06b6d4", "#a855f7", "#f59e0b", "#ef4444", "#ec4899"];

export function CompareModels({ projectId }: Props) {
  const { data: entries, refetch, isFetching } = useCompareModels(projectId);

  const hasEntries = entries && entries.length > 0;
  const { data: chartData, keys } = hasEntries
    ? buildChartData(entries)
    : { data: [], keys: [] };

  return (
    <div className="space-y-4">
      <button
        onClick={() => refetch()}
        disabled={isFetching}
        className="px-4 py-1.5 bg-wybe-accent text-wybe-bg-primary text-sm font-medium rounded hover:bg-wybe-accent-hover transition-colors disabled:opacity-50"
      >
        {isFetching ? "Loading..." : "Load Comparison"}
      </button>

      {hasEntries ? (
        <>
          {/* Table */}
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-wybe-border">
                  <th className="text-left py-2 text-wybe-text-muted font-medium">
                    Model
                  </th>
                  <th className="text-left py-2 text-wybe-text-muted font-medium">
                    Eval Type
                  </th>
                  <th className="text-left py-2 text-wybe-text-muted font-medium">
                    Metrics
                  </th>
                </tr>
              </thead>
              <tbody>
                {entries.map((e, i) => (
                  <tr
                    key={`${e.model_id}-${i}`}
                    className="border-b border-wybe-border/50"
                  >
                    <td className="py-2 text-wybe-text">{e.model_name}</td>
                    <td className="py-2 text-wybe-text">{e.eval_type}</td>
                    <td className="py-2 text-wybe-text font-mono">
                      {Object.entries(e.metrics)
                        .map(([k, v]) => `${k}=${v}`)
                        .join(", ") || "-"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Chart */}
          {chartData.length >= 2 && keys.length > 0 && (
            <div className="bg-wybe-bg-primary border border-wybe-border rounded-lg p-4">
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                  <XAxis
                    dataKey="model"
                    tick={{ fill: "#94a3b8", fontSize: 11 }}
                  />
                  <YAxis tick={{ fill: "#94a3b8", fontSize: 11 }} />
                  <Tooltip
                    contentStyle={{
                      background: "#1e1e2e",
                      border: "1px solid #333",
                      borderRadius: 8,
                      fontSize: 12,
                    }}
                  />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                  {keys.map((key, idx) => (
                    <Bar
                      key={key}
                      dataKey={key}
                      fill={COLORS[idx % COLORS.length]}
                    />
                  ))}
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </>
      ) : entries !== undefined ? (
        <p className="text-xs text-wybe-text-muted py-4 text-center">
          No model evaluations found. Run evaluations first, then compare.
        </p>
      ) : null}
    </div>
  );
}
