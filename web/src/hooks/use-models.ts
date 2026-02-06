"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import type {
  Model,
  ModelsConstants,
  ServerInfo,
  DeployResponse,
  BenchmarkMetrics,
} from "@/types";

export function useModels(projectId: string | null) {
  return useQuery({
    queryKey: ["models", projectId],
    queryFn: () =>
      api
        .get<{ models: Model[] }>(
          `/api/models${projectId ? `?project_id=${projectId}` : ""}`,
        )
        .then((r) => r.models),
    enabled: !!projectId,
  });
}

export function useRegisterModel(projectId: string | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: {
      name: string;
      path: string;
      source_run_id?: string;
      base_model?: string;
      embodiment_tag?: string;
      step?: number;
      notes?: string;
    }) => api.post<Model>(`/api/models?project_id=${projectId}`, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["models", projectId] });
    },
  });
}

export function useModelsConstants() {
  return useQuery({
    queryKey: ["models-constants"],
    queryFn: () => api.get<ModelsConstants>("/api/models/constants"),
  });
}

export function useServerInfo(enabled: boolean = true) {
  return useQuery({
    queryKey: ["server-info"],
    queryFn: () => api.get<ServerInfo>("/api/server"),
    enabled,
    refetchInterval: 5000,
  });
}

export function useDeployModel() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: {
      model_path: string;
      embodiment_tag: string;
      port: number;
    }) => api.post<DeployResponse>("/api/server/deploy", body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["server-info"] });
    },
  });
}

export function useStopServer() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.post<DeployResponse>("/api/server/stop", {}),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["server-info"] });
    },
  });
}

export function useBenchmarkMetrics(
  runId: string | null,
  enabled: boolean = true,
) {
  return useQuery({
    queryKey: ["benchmark-metrics", runId],
    queryFn: () =>
      api.get<BenchmarkMetrics>(`/api/runs/${runId}/benchmark-metrics`),
    enabled: !!runId && enabled,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (
        status === "completed" ||
        status === "failed" ||
        status === "stopped"
      ) {
        return false;
      }
      return 3000;
    },
  });
}
