"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import type {
  Dataset,
  DatasetConstants,
  EpisodeData,
  InspectResult,
} from "@/types";

export function useDatasets(projectId: string | null) {
  return useQuery({
    queryKey: ["datasets", projectId],
    queryFn: () =>
      api
        .get<{ datasets: Dataset[] }>(
          `/api/datasets${projectId ? `?project_id=${projectId}` : ""}`,
        )
        .then((r) => r.datasets),
    enabled: !!projectId,
  });
}

export function useDataset(id: string | null) {
  return useQuery({
    queryKey: ["dataset", id],
    queryFn: () => api.get<Dataset>(`/api/datasets/${id}`),
    enabled: !!id,
  });
}

export function useCreateDataset(projectId: string | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { name: string; path: string; source: string }) =>
      api.post<Dataset>(`/api/datasets?project_id=${projectId}`, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["datasets", projectId] });
    },
  });
}

export function useDeleteDataset(projectId: string | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.del(`/api/datasets/${id}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["datasets", projectId] });
    },
  });
}

export function useDatasetConstants() {
  return useQuery({
    queryKey: ["dataset-constants"],
    queryFn: () => api.get<DatasetConstants>("/api/datasets/constants"),
    staleTime: Infinity,
  });
}

export function useInspectDataset() {
  return useMutation({
    mutationFn: (datasetPath: string) =>
      api.post<InspectResult>("/api/datasets/inspect", {
        dataset_path: datasetPath,
      }),
  });
}

export function useEpisodeData() {
  return useMutation({
    mutationFn: (params: { dataset_path: string; episode_index: number }) =>
      api.post<EpisodeData>("/api/datasets/episode", params),
  });
}

export function useEmbodimentConfig(tag: string | null) {
  return useQuery({
    queryKey: ["embodiment-config", tag],
    queryFn: () => api.get<Record<string, unknown>>(`/api/datasets/embodiment/${tag}`),
    enabled: !!tag,
  });
}
