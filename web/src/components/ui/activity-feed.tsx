import type { ActivityEntry } from "@/types";

const ICONS: Record<string, { bg: string; icon: string }> = {
  project_created: { bg: "bg-wybe-accent/20", icon: "+" },
  dataset_registered: { bg: "bg-wybe-cyan/20", icon: "D" },
  run_created: { bg: "bg-wybe-purple/20", icon: "R" },
  model_registered: { bg: "bg-wybe-warning/20", icon: "M" },
};

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

export function ActivityFeed({ entries }: { entries: ActivityEntry[] }) {
  if (entries.length === 0) {
    return (
      <p className="text-sm text-wybe-text-muted py-4">No recent activity</p>
    );
  }
  return (
    <div className="space-y-0">
      {entries.map((e) => {
        const icon = ICONS[e.event_type] ?? { bg: "bg-wybe-bg-tertiary", icon: "?" };
        return (
          <div
            key={e.id}
            className="flex items-start gap-2.5 py-2 border-b border-wybe-border/50 last:border-0"
          >
            <div
              className={`w-7 h-7 rounded-full flex items-center justify-center text-xs shrink-0 ${icon.bg} text-wybe-text`}
            >
              {icon.icon}
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-[13px] text-wybe-text truncate">{e.message}</p>
              <p className="text-[11px] text-wybe-text-muted">
                {timeAgo(e.created_at)}
              </p>
            </div>
          </div>
        );
      })}
    </div>
  );
}
