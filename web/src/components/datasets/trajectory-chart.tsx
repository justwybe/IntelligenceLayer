"use client";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import type { TrajectoryTrace } from "@/types";

const COLORS = [
  "#22c55e",
  "#3b82f6",
  "#ef4444",
  "#eab308",
  "#a855f7",
  "#06b6d4",
  "#f97316",
  "#ec4899",
  "#14b8a6",
  "#8b5cf6",
  "#f43f5e",
  "#84cc16",
];

interface Props {
  title: string;
  traces: TrajectoryTrace[];
}

export function TrajectoryChart({ title, traces }: Props) {
  if (traces.length === 0) {
    return (
      <div className="bg-wybe-bg-secondary border border-wybe-border rounded-lg p-4 h-[300px] flex items-center justify-center">
        <p className="text-sm text-wybe-text-muted">No {title.toLowerCase()} data</p>
      </div>
    );
  }

  // Convert traces to recharts data format: [{step: 0, trace1: val, trace2: val}, ...]
  const maxLen = Math.max(...traces.map((t) => t.y.length));
  const data = Array.from({ length: maxLen }, (_, i) => {
    const point: Record<string, number> = { step: i };
    for (const trace of traces) {
      if (i < trace.y.length) {
        point[trace.name] = trace.y[i];
      }
    }
    return point;
  });

  return (
    <div className="bg-wybe-bg-secondary border border-wybe-border rounded-lg p-4">
      <h4 className="text-xs font-medium text-wybe-text-muted mb-2">{title}</h4>
      <ResponsiveContainer width="100%" height={260}>
        <LineChart data={data}>
          <XAxis
            dataKey="step"
            tick={{ fill: "#64748b", fontSize: 10 }}
            axisLine={{ stroke: "#334155" }}
            tickLine={false}
          />
          <YAxis
            tick={{ fill: "#64748b", fontSize: 10 }}
            axisLine={{ stroke: "#334155" }}
            tickLine={false}
            width={50}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: "#1e293b",
              border: "1px solid #334155",
              borderRadius: "6px",
              fontSize: "11px",
            }}
            labelStyle={{ color: "#e2e8f0" }}
          />
          <Legend
            wrapperStyle={{ fontSize: "10px" }}
            iconSize={8}
          />
          {traces.map((trace, i) => (
            <Line
              key={trace.name}
              type="monotone"
              dataKey={trace.name}
              stroke={COLORS[i % COLORS.length]}
              dot={false}
              strokeWidth={1.5}
              isAnimationActive={false}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
