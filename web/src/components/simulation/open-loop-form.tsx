"use client";

import { useState } from "react";
import { useSimulationConstants } from "@/hooks/use-simulation";
import { useModels } from "@/hooks/use-models";
import { useCreateRun, useStopRun } from "@/hooks/use-runs";

interface Props {
  projectId: string | null;
  activeRunId: string | null;
  onRunStarted: (runId: string) => void;
}

export function OpenLoopForm({ projectId, activeRunId, onRunStarted }: Props) {
  const { data: constants } = useSimulationConstants();
  const { data: models } = useModels(projectId);
  const createRun = useCreateRun(projectId);
  const stopRun = useStopRun();

  const [datasetPath, setDatasetPath] = useState("demo_data/cube_to_bowl_5/");
  const [modelPath, setModelPath] = useState("");
  const [embodiment, setEmbodiment] = useState("new_embodiment");
  const [trajIds, setTrajIds] = useState("0");
  const [steps, setSteps] = useState(200);
  const [actionHorizon, setActionHorizon] = useState(16);

  const embodimentChoices = constants?.embodiment_choices ?? ["new_embodiment"];
  const modelChoices = models?.map((m) => `${m.name} | ${m.path}`) ?? [];

  function handleLaunch() {
    if (!projectId) return;

    createRun.mutate(
      {
        run_type: "evaluation",
        config: {
          dataset_path: datasetPath,
          model_path: modelPath,
          embodiment_tag: embodiment,
          traj_ids: trajIds,
          steps,
          action_horizon: actionHorizon,
        },
      },
      { onSuccess: (run) => onRunStarted(run.id) },
    );
  }

  return (
    <div className="space-y-4">
      {/* Dataset Path */}
      <div>
        <label className="block text-xs text-wybe-text-muted mb-1">
          Dataset Path
        </label>
        <input
          type="text"
          value={datasetPath}
          onChange={(e) => setDatasetPath(e.target.value)}
          className="w-full bg-wybe-bg-tertiary border border-wybe-border rounded px-3 py-1.5 text-sm text-wybe-text focus:outline-none focus:border-wybe-accent"
        />
      </div>

      {/* Model */}
      <div>
        <label className="block text-xs text-wybe-text-muted mb-1">
          Model
        </label>
        <select
          value={modelPath}
          onChange={(e) => setModelPath(e.target.value)}
          className="w-full bg-wybe-bg-tertiary border border-wybe-border rounded px-3 py-1.5 text-sm text-wybe-text focus:outline-none focus:border-wybe-accent"
        >
          <option value="">Select model...</option>
          {modelChoices.map((m) => (
            <option key={m} value={m}>
              {m}
            </option>
          ))}
        </select>
      </div>

      {/* Embodiment Tag */}
      <div>
        <label className="block text-xs text-wybe-text-muted mb-1">
          Embodiment Tag
        </label>
        <select
          value={embodiment}
          onChange={(e) => setEmbodiment(e.target.value)}
          className="w-full bg-wybe-bg-tertiary border border-wybe-border rounded px-3 py-1.5 text-sm text-wybe-text focus:outline-none focus:border-wybe-accent max-w-xs"
        >
          {embodimentChoices.map((e) => (
            <option key={e} value={e}>
              {e}
            </option>
          ))}
        </select>
      </div>

      {/* Trajectory IDs */}
      <div>
        <label className="block text-xs text-wybe-text-muted mb-1">
          Trajectory IDs (comma-separated)
        </label>
        <input
          type="text"
          value={trajIds}
          onChange={(e) => setTrajIds(e.target.value)}
          placeholder="0, 1, 2"
          className="w-full bg-wybe-bg-tertiary border border-wybe-border rounded px-3 py-1.5 text-sm text-wybe-text focus:outline-none focus:border-wybe-accent"
        />
      </div>

      {/* Parameters */}
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-xs text-wybe-text-muted mb-1">
            Max Steps
          </label>
          <input
            type="number"
            value={steps}
            onChange={(e) => setSteps(parseInt(e.target.value) || 0)}
            min={10}
            max={1000}
            step={10}
            className="w-full bg-wybe-bg-tertiary border border-wybe-border rounded px-3 py-1.5 text-sm text-wybe-text focus:outline-none focus:border-wybe-accent"
          />
        </div>
        <div>
          <label className="block text-xs text-wybe-text-muted mb-1">
            Action Horizon
          </label>
          <input
            type="number"
            value={actionHorizon}
            onChange={(e) => setActionHorizon(parseInt(e.target.value) || 0)}
            min={1}
            max={64}
            className="w-full bg-wybe-bg-tertiary border border-wybe-border rounded px-3 py-1.5 text-sm text-wybe-text focus:outline-none focus:border-wybe-accent"
          />
        </div>
      </div>

      {/* Action buttons */}
      <div className="flex gap-2">
        <button
          onClick={handleLaunch}
          disabled={!projectId || createRun.isPending}
          className="px-4 py-1.5 bg-wybe-accent text-wybe-bg-primary text-sm font-medium rounded hover:bg-wybe-accent-hover transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {createRun.isPending ? "Launching..." : "Run Eval"}
        </button>
        {activeRunId && (
          <button
            onClick={() => stopRun.mutate(activeRunId)}
            disabled={stopRun.isPending}
            className="px-4 py-1.5 bg-wybe-danger/20 text-wybe-danger text-sm font-medium rounded hover:bg-wybe-danger/30 transition-colors disabled:opacity-50"
          >
            Stop
          </button>
        )}
      </div>

      {createRun.isError && (
        <p className="text-xs text-wybe-danger">
          {(createRun.error as Error).message}
        </p>
      )}
    </div>
  );
}
