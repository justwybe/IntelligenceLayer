"use client";

import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api-client";
import type { ActivityEntry, ServerInfo } from "@/types";
import { useProjectStore } from "@/stores/project-store";
import { useGpu } from "@/hooks/use-gpu";
import { GpuCard } from "@/components/ui/gpu-card";
import { ActivityFeed } from "@/components/ui/activity-feed";
import { StatusBadge } from "@/components/ui/status-badge";

export function DashboardSidebar() {
  const { sidebarVisible, setSidebarVisible, currentProjectId } =
    useProjectStore();
  const { gpus, connected } = useGpu();

  const { data: serverInfo } = useQuery({
    queryKey: ["server"],
    queryFn: () => api.get<ServerInfo>("/api/server"),
    refetchInterval: 10_000,
  });

  const { data: activityData } = useQuery({
    queryKey: ["activity", currentProjectId],
    queryFn: () => {
      const params = currentProjectId
        ? `?project_id=${currentProjectId}&limit=20`
        : "?limit=20";
      return api
        .get<{ entries: ActivityEntry[] }>(`/api/activity${params}`)
        .then((r) => r.entries);
    },
    refetchInterval: 10_000,
  });

  if (!sidebarVisible) return null;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-40"
        onClick={() => setSidebarVisible(false)}
      />

      {/* Panel */}
      <div className="fixed right-0 top-14 w-80 h-[calc(100vh-3.5rem)] bg-wybe-bg-secondary border-l border-wybe-border z-50 overflow-y-auto p-4 shadow-[-4px_0_12px_rgba(0,0,0,0.3)]">
        {/* GPU Section */}
        <div className="mb-6">
          <div className="flex items-center gap-2 mb-3">
            <h3 className="text-sm font-semibold text-wybe-text">GPU Status</h3>
            <span
              className={`w-2 h-2 rounded-full ${connected ? "bg-wybe-success animate-pulse-dot" : "bg-wybe-danger"}`}
            />
          </div>
          {gpus.length === 0 ? (
            <p className="text-sm text-wybe-text-muted">No GPUs detected</p>
          ) : (
            gpus.map((gpu, i) => <GpuCard key={i} gpu={gpu} index={i} />)
          )}
        </div>

        {/* Server Status */}
        <div className="mb-6">
          <h3 className="text-sm font-semibold text-wybe-text mb-3">
            Inference Server
          </h3>
          {serverInfo ? (
            <div className="bg-wybe-bg-secondary border border-wybe-border rounded-lg p-3 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs text-wybe-text-muted">Status</span>
                <StatusBadge status={serverInfo.status} />
              </div>
              <div className="flex items-center justify-between">
                <span className="text-xs text-wybe-text-muted">Port</span>
                <span className="text-xs text-wybe-text font-mono">
                  {serverInfo.port}
                </span>
              </div>
              {serverInfo.model_path && (
                <div>
                  <span className="text-xs text-wybe-text-muted">Model</span>
                  <p className="text-xs text-wybe-text truncate">
                    {serverInfo.model_path}
                  </p>
                </div>
              )}
            </div>
          ) : (
            <p className="text-sm text-wybe-text-muted">Loading...</p>
          )}
        </div>

        {/* Activity Feed */}
        <div>
          <h3 className="text-sm font-semibold text-wybe-text mb-3">
            Recent Activity
          </h3>
          <ActivityFeed entries={activityData ?? []} />
        </div>
      </div>
    </>
  );
}
