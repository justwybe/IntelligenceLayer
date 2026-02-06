"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import type { Model } from "@/types";

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
