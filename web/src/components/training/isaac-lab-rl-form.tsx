"use client";

import { useState } from "react";
import { useTrainingConstants } from "@/hooks/use-training";

interface Props {
  projectId: string | null;
}

export function IsaacLabRlForm({ projectId }: Props) {
  const { data: constants } = useTrainingConstants();

  const [env, setEnv] = useState("");
  const [algorithm, setAlgorithm] = useState("PPO");
  const [numEnvs, setNumEnvs] = useState(1024);
  const [totalTimesteps, setTotalTimesteps] = useState(1000000);
  const [domainRand, setDomainRand] = useState(true);
  const [remoteHost, setRemoteHost] = useState("");
  const [remotePort, setRemotePort] = useState(22);
  const [status, setStatus] = useState("");

  const envChoices = constants?.isaac_lab_envs ?? [];
  const algoChoices = constants?.rl_algorithms ?? ["PPO", "SAC", "RSL-RL"];

  function handleLaunch() {
    if (!projectId) {
      setStatus("Error: select a project first");
      return;
    }
    setStatus("Isaac Lab RL training is not yet available — backend integration pending.");
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* Left: Configuration */}
      <div className="space-y-4">
        <h3 className="text-sm font-semibold text-wybe-text-bright">RL Configuration</h3>

        <div>
          <label className="block text-xs text-wybe-text-muted mb-1">Environment</label>
          <select
            value={env}
            onChange={(e) => setEnv(e.target.value)}
            className="w-full bg-wybe-bg-tertiary border border-wybe-border rounded px-3 py-1.5 text-sm text-wybe-text focus:outline-none focus:border-wybe-accent"
          >
            <option value="">Select environment...</option>
            {envChoices.map((e) => (
              <option key={e} value={e}>
                {e}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-xs text-wybe-text-muted mb-1">RL Algorithm</label>
          <select
            value={algorithm}
            onChange={(e) => setAlgorithm(e.target.value)}
            className="w-full bg-wybe-bg-tertiary border border-wybe-border rounded px-3 py-1.5 text-sm text-wybe-text focus:outline-none focus:border-wybe-accent"
          >
            {algoChoices.map((a) => (
              <option key={a} value={a}>
                {a}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-xs text-wybe-text-muted mb-1">
            Num Parallel Envs: {numEnvs}
          </label>
          <input
            type="range"
            min={1}
            max={4096}
            step={1}
            value={numEnvs}
            onChange={(e) => setNumEnvs(parseInt(e.target.value))}
            className="w-full accent-wybe-accent"
          />
        </div>

        <div>
          <label className="block text-xs text-wybe-text-muted mb-1">
            Total Timesteps: {totalTimesteps.toLocaleString()}
          </label>
          <input
            type="range"
            min={10000}
            max={100000000}
            step={10000}
            value={totalTimesteps}
            onChange={(e) => setTotalTimesteps(parseInt(e.target.value))}
            className="w-full accent-wybe-accent"
          />
        </div>

        <label className="flex items-center gap-2 text-sm text-wybe-text cursor-pointer">
          <input
            type="checkbox"
            checked={domainRand}
            onChange={(e) => setDomainRand(e.target.checked)}
            className="rounded border-wybe-border bg-wybe-bg-tertiary accent-wybe-accent"
          />
          Domain Randomization
        </label>

        <div className="border-t border-wybe-border pt-4">
          <h3 className="text-sm font-semibold text-wybe-text-bright mb-3">
            Remote Execution
          </h3>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs text-wybe-text-muted mb-1">Remote Host</label>
              <input
                type="text"
                value={remoteHost}
                onChange={(e) => setRemoteHost(e.target.value)}
                placeholder="runpod-host.example.com"
                className="w-full bg-wybe-bg-tertiary border border-wybe-border rounded px-3 py-1.5 text-sm text-wybe-text focus:outline-none focus:border-wybe-accent"
              />
            </div>
            <div>
              <label className="block text-xs text-wybe-text-muted mb-1">Port</label>
              <input
                type="number"
                value={remotePort}
                onChange={(e) => setRemotePort(parseInt(e.target.value) || 22)}
                className="w-full bg-wybe-bg-tertiary border border-wybe-border rounded px-3 py-1.5 text-sm text-wybe-text focus:outline-none focus:border-wybe-accent"
              />
            </div>
          </div>
        </div>

        <div className="flex gap-2">
          <button
            onClick={handleLaunch}
            disabled={!projectId || !env}
            className="px-4 py-1.5 bg-wybe-accent text-wybe-bg-primary text-sm font-medium rounded hover:bg-wybe-accent-hover transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Launch RL Training
          </button>
          <button
            disabled
            className="px-4 py-1.5 bg-wybe-danger/20 text-wybe-danger text-sm font-medium rounded opacity-50 cursor-not-allowed"
          >
            Stop
          </button>
        </div>

        {status && (
          <p className="text-xs text-wybe-text-muted bg-wybe-bg-secondary border border-wybe-border rounded p-2">
            {status}
          </p>
        )}
      </div>

      {/* Right: RL Monitor placeholder */}
      <div className="space-y-4">
        <h3 className="text-sm font-semibold text-wybe-text-bright">RL Monitor</h3>
        <div className="flex items-center justify-center h-64 text-sm text-wybe-text-muted border border-wybe-border rounded-lg">
          RL monitoring will be available once backend integration is complete
        </div>
      </div>
    </div>
  );
}
