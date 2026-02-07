"use client";

import { useState } from "react";
import { useEpisodeData } from "@/hooks/use-datasets";
import { TrajectoryChart } from "./trajectory-chart";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "";

function getApiKey(): string {
  if (typeof document === "undefined") return "";
  const match = document.cookie.match(/(?:^|; )wybe_api_key=([^;]*)/);
  return match ? decodeURIComponent(match[1]) : "";
}

export function EpisodeViewer() {
  const [datasetPath, setDatasetPath] = useState("");
  const [episodeIndex, setEpisodeIndex] = useState(0);
  const episodeMutation = useEpisodeData();

  function handleLoad() {
    if (!datasetPath.trim()) return;
    episodeMutation.mutate({
      dataset_path: datasetPath.trim(),
      episode_index: episodeIndex,
    });
  }

  const data = episodeMutation.data;
  const videoUrl = data?.video_path
    ? `${BASE_URL}/api/datasets/video?path=${encodeURIComponent(data.video_path)}&token=${encodeURIComponent(getApiKey())}`
    : null;

  return (
    <div className="space-y-3">
      <div className="flex items-end gap-3">
        <div className="flex-1">
          <label className="block text-xs text-wybe-text-muted mb-1">
            Dataset Path
          </label>
          <input
            type="text"
            value={datasetPath}
            onChange={(e) => setDatasetPath(e.target.value)}
            placeholder="/path/to/lerobot_v2_dataset"
            className="w-full bg-wybe-bg-tertiary border border-wybe-border rounded px-3 py-1.5 text-sm text-wybe-text placeholder:text-wybe-text-muted/50 focus:outline-none focus:border-wybe-accent"
          />
        </div>
        <div className="w-32">
          <label className="block text-xs text-wybe-text-muted mb-1">
            Episode
          </label>
          <input
            type="number"
            min={0}
            max={999}
            value={episodeIndex}
            onChange={(e) => setEpisodeIndex(Number(e.target.value))}
            className="w-full bg-wybe-bg-tertiary border border-wybe-border rounded px-3 py-1.5 text-sm text-wybe-text focus:outline-none focus:border-wybe-accent"
          />
        </div>
        <button
          onClick={handleLoad}
          disabled={episodeMutation.isPending}
          className="px-4 py-1.5 bg-wybe-accent text-wybe-bg-primary text-sm font-medium rounded hover:bg-wybe-accent-hover transition-colors disabled:opacity-50"
        >
          {episodeMutation.isPending ? "Loading..." : "Load Episode"}
        </button>
      </div>

      {episodeMutation.isError && (
        <p className="text-xs text-wybe-danger">
          {(episodeMutation.error as Error).message}
        </p>
      )}

      {data && (
        <>
          {data.task_description && (
            <p className="text-sm text-wybe-text">
              <span className="font-medium">Task:</span> {data.task_description}
            </p>
          )}

          {videoUrl && (
            <video
              src={videoUrl}
              controls
              className="w-full max-w-xl rounded-lg border border-wybe-border"
            />
          )}

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
            <TrajectoryChart
              title="State Trajectories"
              traces={data.state_traces}
            />
            <TrajectoryChart
              title="Action Trajectories"
              traces={data.action_traces}
            />
          </div>
        </>
      )}
    </div>
  );
}
