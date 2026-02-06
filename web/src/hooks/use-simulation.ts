"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import type {
  SimulationConstants,
  EvalMetrics,
  Artifact,
  Evaluation,
  CompareEntry,
} from "@/types";

export function useSimulationConstants() {
  return useQuery({
    queryKey: ["simulation-constants"],
    queryFn: () => api.get<SimulationConstants>("/api/simulation/constants"),
    staleTime: Infinity,
  });
}

export function useEvalMetrics(runId: string | null, enabled: boolean = true) {
  return useQuery({
    queryKey: ["eval-metrics", runId],
    queryFn: () => api.get<EvalMetrics>(`/api/runs/${runId}/eval-metrics`),
    enabled: !!runId && enabled,
    refetchInterval: (query) => {
      // Stop polling if we have metrics and the run seems done
      const data = query.state.data;
      if (!data) return 4000;
      // Keep polling while active
      return 4000;
    },
  });
}

export function useRunArtifacts(runId: string | null, enabled: boolean = true) {
  return useQuery({
    queryKey: ["run-artifacts", runId],
    queryFn: () =>
      api
        .get<{ artifacts: Artifact[] }>(`/api/runs/${runId}/artifacts`)
        .then((r) => r.artifacts),
    enabled: !!runId && enabled,
    refetchInterval: 5000,
  });
}

export function useEvaluations(modelId?: string, runId?: string) {
  const params = new URLSearchParams();
  if (modelId) params.set("model_id", modelId);
  if (runId) params.set("run_id", runId);
  const qs = params.toString();

  return useQuery({
    queryKey: ["evaluations", modelId, runId],
    queryFn: () =>
      api
        .get<{ evaluations: Evaluation[] }>(
          `/api/evaluations${qs ? `?${qs}` : ""}`,
        )
        .then((r) => r.evaluations),
  });
}

export function useCompareModels(projectId: string | null) {
  return useQuery({
    queryKey: ["compare-models", projectId],
    queryFn: () =>
      api
        .get<{ entries: CompareEntry[] }>(
          `/api/evaluations/compare${projectId ? `?project_id=${projectId}` : ""}`,
        )
        .then((r) => r.entries),
    enabled: false, // Only fetch on demand via refetch()
  });
}
