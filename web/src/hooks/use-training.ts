"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import type { TrainingConstants, TrainingMetrics } from "@/types";

export function useTrainingConstants() {
  return useQuery({
    queryKey: ["training-constants"],
    queryFn: () => api.get<TrainingConstants>("/api/training/constants"),
    staleTime: Infinity,
  });
}

export function useTrainingMetrics(runId: string | null, enabled: boolean = true) {
  return useQuery({
    queryKey: ["training-metrics", runId],
    queryFn: () => api.get<TrainingMetrics>(`/api/runs/${runId}/metrics`),
    enabled: !!runId && enabled,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status === "completed" || status === "failed" || status === "stopped") {
        return false;
      }
      return 4000;
    },
  });
}
