export function MetricCard({
  label,
  value,
}: {
  label: string;
  value: string | number;
}) {
  return (
    <div className="bg-wybe-bg-secondary border border-wybe-border rounded-xl p-5 hover:border-wybe-accent transition-colors">
      <div className="text-xs text-wybe-text-muted uppercase tracking-wide mb-2">
        {label}
      </div>
      <div className="text-[28px] font-bold text-wybe-text-bright">{value}</div>
    </div>
  );
}
