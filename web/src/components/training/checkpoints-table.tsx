"use client";

import type { CheckpointInfo } from "@/types";

interface Props {
  checkpoints: CheckpointInfo[];
  onSelect?: (path: string) => void;
}

export function CheckpointsTable({ checkpoints, onSelect }: Props) {
  if (checkpoints.length === 0) {
    return (
      <p className="text-xs text-wybe-text-muted">No checkpoints saved yet</p>
    );
  }

  return (
    <div className="overflow-auto max-h-40">
      <table className="w-full text-xs">
        <thead>
          <tr className="text-wybe-text-muted border-b border-wybe-border">
            <th className="text-left py-1.5 pr-4 font-medium">Checkpoint</th>
            <th className="text-left py-1.5 font-medium">Step</th>
          </tr>
        </thead>
        <tbody>
          {checkpoints.map((ckpt, i) => (
            <tr
              key={i}
              onClick={() => onSelect?.(ckpt.path)}
              className={`border-b border-wybe-border/50 ${
                onSelect
                  ? "cursor-pointer hover:bg-wybe-bg-tertiary transition-colors"
                  : ""
              }`}
            >
              <td className="py-1.5 pr-4 text-wybe-text font-mono truncate max-w-[300px]">
                {ckpt.path}
              </td>
              <td className="py-1.5 text-wybe-text-muted">
                {ckpt.step ?? "?"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
