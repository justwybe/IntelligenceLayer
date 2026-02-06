"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import type { Run, RunStatus } from "@/types";

export function useRuns(projectId: string | null, runType?: string) {
  const params = new URLSearchParams();
  if (projectId) params.set("project_id", projectId);
  if (runType) params.set("run_type", runType);
  const qs = params.toString();

  return useQuery({
    queryKey: ["runs", projectId, runType],
    queryFn: () =>
      api.get<{ runs: Run[] }>(`/api/runs${qs ? `?${qs}` : ""}`).then((r) => r.runs),
    enabled: !!projectId,
  });
}

export function useCreateRun(projectId: string | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: {
      run_type: string;
      config: Record<string, unknown>;
      dataset_id?: string;
    }) => api.post<Run>(`/api/runs?project_id=${projectId}`, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["runs", projectId] });
    },
  });
}

export function useRunStatus(runId: string | null, enabled: boolean = true) {
  return useQuery({
    queryKey: ["run-status", runId],
    queryFn: () => api.get<RunStatus>(`/api/runs/${runId}/status`),
    enabled: !!runId && enabled,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status === "completed" || status === "failed" || status === "stopped") {
        return false;
      }
      return 3000;
    },
  });
}

export function useStopRun() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (runId: string) =>
      api.post<{ message: string }>(`/api/runs/${runId}/stop`, {}),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["runs"] });
    },
  });
}
