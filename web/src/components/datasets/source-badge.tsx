"use client";

const COLORS: Record<string, { bg: string; text: string }> = {
  imported: { bg: "bg-blue-500/15", text: "text-blue-400" },
  recorded: { bg: "bg-wybe-success/15", text: "text-wybe-accent-hover" },
  mimic: { bg: "bg-wybe-purple/15", text: "text-purple-400" },
  dreams: { bg: "bg-wybe-cyan/15", text: "text-cyan-400" },
  urban_memory: { bg: "bg-wybe-warning/15", text: "text-yellow-300" },
};

export function SourceBadge({ source }: { source: string | null }) {
  const s = source ?? "imported";
  const c = COLORS[s] ?? COLORS.imported;
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium ${c.bg} ${c.text}`}
    >
      {s}
    </span>
  );
}
