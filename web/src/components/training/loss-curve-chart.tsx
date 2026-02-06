"use client";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import type { LossPoint } from "@/types";

interface Props {
  data: LossPoint[];
}

export function LossCurveChart({ data }: Props) {
  if (data.length === 0) {
    return (
      <div className="h-[280px] flex items-center justify-center text-sm text-wybe-text-muted">
        No loss data yet
      </div>
    );
  }

  return (
    <div className="h-[280px]">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
          <XAxis
            dataKey="step"
            stroke="rgba(255,255,255,0.3)"
            tick={{ fontSize: 11 }}
            tickFormatter={(v: number) => v.toLocaleString()}
          />
          <YAxis
            stroke="rgba(255,255,255,0.3)"
            tick={{ fontSize: 11 }}
            tickFormatter={(v: number) => v.toFixed(3)}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: "rgba(20,20,30,0.95)",
              border: "1px solid rgba(255,255,255,0.1)",
              borderRadius: "8px",
              fontSize: 12,
            }}
            labelFormatter={(v) => `Step ${Number(v).toLocaleString()}`}
            formatter={(v) => [Number(v).toFixed(5), "Loss"]}
          />
          <Line
            type="monotone"
            dataKey="loss"
            stroke="#3b82f6"
            strokeWidth={1.5}
            dot={false}
            activeDot={{ r: 3, fill: "#3b82f6" }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
