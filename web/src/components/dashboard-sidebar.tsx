"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api-client";
import type { ActivityEntry, Project, ServerInfo } from "@/types";
import { useProjectStore } from "@/stores/project-store";
import { useGpu } from "@/hooks/use-gpu";
import { GpuCard } from "@/components/ui/gpu-card";
import { ActivityFeed } from "@/components/ui/activity-feed";
import { StatusBadge } from "@/components/ui/status-badge";

interface SystemInfo {
  platform: string;
  python_version: string;
  pytorch_version: string;
  cuda_version: string;
  transformers_version: string;
}

export function DashboardSidebar() {
  const { sidebarVisible, setSidebarVisible, currentProjectId } =
    useProjectStore();
  const { gpus, connected } = useGpu();
  const [sysInfoOpen, setSysInfoOpen] = useState(false);

  const { data: projectDetail } = useQuery({
    queryKey: ["project-detail", currentProjectId],
    queryFn: () =>
      api.get<Project>(`/api/projects/${currentProjectId}`),
    enabled: !!currentProjectId,
    staleTime: 10_000,
  });

  const { data: serverInfo } = useQuery({
    queryKey: ["server"],
    queryFn: () => api.get<ServerInfo>("/api/server"),
    refetchInterval: 10_000,
  });

  const { data: systemInfo } = useQuery({
    queryKey: ["system-info"],
    queryFn: () => api.get<SystemInfo>("/api/system-info"),
    staleTime: 60_000,
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
        {/* Summary Metrics */}
        {projectDetail && (
          <div className="mb-6">
            <h3 className="text-sm font-semibold text-wybe-text mb-3">
              Project Summary
            </h3>
            <div className="grid grid-cols-3 gap-2">
              <MetricCard label="Datasets" value={projectDetail.dataset_count ?? 0} />
              <MetricCard label="Models" value={projectDetail.model_count ?? 0} />
              <MetricCard label="Runs" value={projectDetail.run_count ?? 0} />
            </div>
          </div>
        )}

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

        {/* System Info */}
        <div className="mb-6">
          <button
            onClick={() => setSysInfoOpen(!sysInfoOpen)}
            className="flex items-center justify-between w-full text-sm font-semibold text-wybe-text mb-2"
          >
            System Info
            <span className="text-xs text-wybe-text-muted">
              {sysInfoOpen ? "collapse" : "expand"}
            </span>
          </button>
          {sysInfoOpen && systemInfo && (
            <div className="bg-wybe-bg-secondary border border-wybe-border rounded-lg p-3 space-y-1.5">
              <InfoRow label="Platform" value={systemInfo.platform} />
              <InfoRow label="Python" value={systemInfo.python_version} />
              <InfoRow label="PyTorch" value={systemInfo.pytorch_version} />
              <InfoRow label="CUDA" value={systemInfo.cuda_version} />
              <InfoRow label="Transformers" value={systemInfo.transformers_version} />
            </div>
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

function MetricCard({ label, value }: { label: string; value: number }) {
  return (
    <div className="bg-wybe-bg-tertiary border border-wybe-border rounded-lg p-2 text-center">
      <div className="text-lg font-bold text-wybe-text-bright">{value}</div>
      <div className="text-[10px] text-wybe-text-muted">{label}</div>
    </div>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-start justify-between gap-2">
      <span className="text-xs text-wybe-text-muted shrink-0">{label}</span>
      <span className="text-xs text-wybe-text font-mono text-right truncate">
        {value}
      </span>
    </div>
  );
}
