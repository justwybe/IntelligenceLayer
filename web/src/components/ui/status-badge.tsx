const VARIANTS: Record<string, { bg: string; text: string; dot: string }> = {
  running: {
    bg: "bg-wybe-success/15",
    text: "text-wybe-accent-hover",
    dot: "bg-wybe-success animate-pulse-dot",
  },
  completed: {
    bg: "bg-wybe-success/15",
    text: "text-wybe-accent-hover",
    dot: "bg-wybe-success",
  },
  failed: {
    bg: "bg-wybe-danger/15",
    text: "text-red-400",
    dot: "bg-wybe-danger",
  },
  pending: {
    bg: "bg-slate-500/15",
    text: "text-slate-400",
    dot: "bg-slate-500",
  },
  stopped: {
    bg: "bg-wybe-warning/15",
    text: "text-yellow-300",
    dot: "bg-wybe-warning",
  },
};

export function StatusBadge({ status }: { status: string }) {
  const v = VARIANTS[status] ?? VARIANTS.pending;
  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium ${v.bg} ${v.text}`}
    >
      <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${v.dot}`} />
      {status}
    </span>
  );
}
