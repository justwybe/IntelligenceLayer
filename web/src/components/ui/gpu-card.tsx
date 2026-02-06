import type { GPUInfo } from "@/types";

function barColor(pct: number): string {
  if (pct > 90) return "bg-wybe-danger";
  if (pct > 70) return "bg-wybe-warning";
  return "bg-wybe-accent";
}

function BarRow({
  label,
  pct,
  detail,
}: {
  label: string;
  pct: number;
  detail: string;
}) {
  return (
    <div className="flex items-center gap-2 mb-1.5">
      <span className="text-[11px] text-wybe-text-muted w-12 shrink-0">
        {label}
      </span>
      <div className="flex-1 h-2 bg-wybe-bg-primary rounded overflow-hidden">
        <div
          className={`h-full rounded transition-all duration-500 ${barColor(pct)}`}
          style={{ width: `${Math.min(pct, 100)}%` }}
        />
      </div>
      <span className="text-[11px] text-wybe-text-muted w-11 text-right font-mono">
        {detail}
      </span>
    </div>
  );
}

export function GpuCard({ gpu, index }: { gpu: GPUInfo; index: number }) {
  const vramPct =
    gpu.memory_total_mb > 0
      ? (gpu.memory_used_mb / gpu.memory_total_mb) * 100
      : 0;

  return (
    <div className="bg-wybe-bg-secondary border border-wybe-border rounded-lg p-3 mb-2">
      <div className="text-[13px] font-semibold text-wybe-text mb-2">
        GPU {index}: {gpu.name}
      </div>
      <BarRow
        label="Util"
        pct={gpu.utilization_pct}
        detail={`${gpu.utilization_pct.toFixed(0)}%`}
      />
      <BarRow
        label="VRAM"
        pct={vramPct}
        detail={`${(gpu.memory_used_mb / 1024).toFixed(1)}G`}
      />
      <BarRow
        label="Temp"
        pct={gpu.temperature_c}
        detail={`${gpu.temperature_c.toFixed(0)}\u00b0C`}
      />
    </div>
  );
}
