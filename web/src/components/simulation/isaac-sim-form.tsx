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

export function IsaacSimForm({ projectId, activeRunId, onRunStarted }: Props) {
  const { data: constants } = useSimulationConstants();
  const { data: models } = useModels(projectId);
  const createRun = useCreateRun(projectId);
  const stopRun = useStopRun();

  const [env, setEnv] = useState("LIBERO");
  const [task, setTask] = useState("");
  const [modelPath, setModelPath] = useState("");
  const [useServer, setUseServer] = useState(false);
  const [serverHost, setServerHost] = useState("localhost");
  const [serverPort, setServerPort] = useState(5555);
  const [maxSteps, setMaxSteps] = useState(504);
  const [nActionSteps, setNActionSteps] = useState(8);
  const [nEpisodes, setNEpisodes] = useState(10);
  const [nEnvs, setNEnvs] = useState(1);

  const envs = constants ? Object.keys(constants.sim_tasks) : ["LIBERO"];
  const tasks = constants?.sim_tasks[env] ?? [];

  // Set default task when constants load or env changes
  const currentTask = task || (tasks.length > 0 ? tasks[0] : "");

  const modelChoices = models?.map((m) => `${m.name} | ${m.path}`) ?? [];

  function handleLaunch() {
    if (!projectId) return;
    const selectedTask = currentTask;
    if (!selectedTask) return;
    if (!useServer && !modelPath.trim()) return;

    createRun.mutate(
      {
        run_type: "simulation",
        config: {
          env_name: env,
          task: selectedTask,
          model_path: modelPath,
          use_server: useServer,
          server_host: serverHost,
          server_port: serverPort,
          max_steps: maxSteps,
          n_action_steps: nActionSteps,
          n_episodes: nEpisodes,
          n_envs: nEnvs,
        },
      },
      { onSuccess: (run) => onRunStarted(run.id) },
    );
  }

  return (
    <div className="space-y-4">
      {/* Environment */}
      <div>
        <label className="block text-xs text-wybe-text-muted mb-1">
          Environment
        </label>
        <div className="flex gap-2">
          {envs.map((e) => (
            <button
              key={e}
              onClick={() => {
                setEnv(e);
                setTask("");
              }}
              className={`px-3 py-1 text-xs font-medium rounded transition-colors ${
                env === e
                  ? "bg-wybe-accent text-wybe-bg-primary"
                  : "bg-wybe-bg-tertiary text-wybe-text-muted hover:text-wybe-text"
              }`}
            >
              {e}
            </button>
          ))}
        </div>
      </div>

      {/* Task */}
      <div>
        <label className="block text-xs text-wybe-text-muted mb-1">Task</label>
        <select
          value={currentTask}
          onChange={(e) => setTask(e.target.value)}
          className="w-full bg-wybe-bg-tertiary border border-wybe-border rounded px-3 py-1.5 text-sm text-wybe-text focus:outline-none focus:border-wybe-accent"
        >
          {tasks.map((t) => (
            <option key={t} value={t}>
              {t.split("/").pop()}
            </option>
          ))}
        </select>
      </div>

      {/* Model */}
      <div>
        <label className="block text-xs text-wybe-text-muted mb-1">
          Model
        </label>
        <select
          value={modelPath}
          onChange={(e) => setModelPath(e.target.value)}
          disabled={useServer}
          className="w-full bg-wybe-bg-tertiary border border-wybe-border rounded px-3 py-1.5 text-sm text-wybe-text focus:outline-none focus:border-wybe-accent disabled:opacity-50"
        >
          <option value="">Select model...</option>
          {modelChoices.map((m) => (
            <option key={m} value={m}>
              {m}
            </option>
          ))}
        </select>
      </div>

      {/* Policy Server */}
      <div>
        <label className="flex items-center gap-2 text-sm text-wybe-text cursor-pointer">
          <input
            type="checkbox"
            checked={useServer}
            onChange={(e) => setUseServer(e.target.checked)}
            className="rounded border-wybe-border bg-wybe-bg-tertiary accent-wybe-accent"
          />
          Use Policy Server
        </label>
        {useServer && (
          <div className="grid grid-cols-2 gap-3 mt-2">
            <div>
              <label className="block text-xs text-wybe-text-muted mb-1">
                Host
              </label>
              <input
                type="text"
                value={serverHost}
                onChange={(e) => setServerHost(e.target.value)}
                className="w-full bg-wybe-bg-tertiary border border-wybe-border rounded px-3 py-1.5 text-sm text-wybe-text focus:outline-none focus:border-wybe-accent"
              />
            </div>
            <div>
              <label className="block text-xs text-wybe-text-muted mb-1">
                Port
              </label>
              <input
                type="number"
                value={serverPort}
                onChange={(e) => setServerPort(parseInt(e.target.value) || 0)}
                className="w-full bg-wybe-bg-tertiary border border-wybe-border rounded px-3 py-1.5 text-sm text-wybe-text focus:outline-none focus:border-wybe-accent"
              />
            </div>
          </div>
        )}
      </div>

      {/* Parameters */}
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-xs text-wybe-text-muted mb-1">
            Max Steps
          </label>
          <input
            type="number"
            value={maxSteps}
            onChange={(e) => setMaxSteps(parseInt(e.target.value) || 0)}
            min={100}
            max={2000}
            step={10}
            className="w-full bg-wybe-bg-tertiary border border-wybe-border rounded px-3 py-1.5 text-sm text-wybe-text focus:outline-none focus:border-wybe-accent"
          />
        </div>
        <div>
          <label className="block text-xs text-wybe-text-muted mb-1">
            N Action Steps
          </label>
          <input
            type="number"
            value={nActionSteps}
            onChange={(e) => setNActionSteps(parseInt(e.target.value) || 0)}
            min={1}
            max={32}
            className="w-full bg-wybe-bg-tertiary border border-wybe-border rounded px-3 py-1.5 text-sm text-wybe-text focus:outline-none focus:border-wybe-accent"
          />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-xs text-wybe-text-muted mb-1">
            N Episodes
          </label>
          <input
            type="number"
            value={nEpisodes}
            onChange={(e) => setNEpisodes(parseInt(e.target.value) || 0)}
            min={1}
            max={100}
            className="w-full bg-wybe-bg-tertiary border border-wybe-border rounded px-3 py-1.5 text-sm text-wybe-text focus:outline-none focus:border-wybe-accent"
          />
        </div>
        <div>
          <label className="block text-xs text-wybe-text-muted mb-1">
            N Envs
          </label>
          <input
            type="number"
            value={nEnvs}
            onChange={(e) => setNEnvs(parseInt(e.target.value) || 0)}
            min={1}
            className="w-full bg-wybe-bg-tertiary border border-wybe-border rounded px-3 py-1.5 text-sm text-wybe-text focus:outline-none focus:border-wybe-accent"
          />
        </div>
      </div>

      {/* Action buttons */}
      <div className="flex gap-2">
        <button
          onClick={handleLaunch}
          disabled={
            !projectId ||
            (!useServer && !modelPath.trim()) ||
            createRun.isPending
          }
          className="px-4 py-1.5 bg-wybe-accent text-wybe-bg-primary text-sm font-medium rounded hover:bg-wybe-accent-hover transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {createRun.isPending ? "Launching..." : "Launch Simulation"}
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
