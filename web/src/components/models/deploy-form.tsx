"use client";

import { useState } from "react";
import {
  useModels,
  useModelsConstants,
  useServerInfo,
  useDeployModel,
  useStopServer,
} from "@/hooks/use-models";

interface Props {
  projectId: string | null;
}

export function DeployForm({ projectId }: Props) {
  const { data: models } = useModels(projectId);
  const { data: constants } = useModelsConstants();
  const { data: serverInfo } = useServerInfo();
  const deployModel = useDeployModel();
  const stopServer = useStopServer();

  const [modelPath, setModelPath] = useState("");
  const [embodiment, setEmbodiment] = useState("new_embodiment");
  const [port, setPort] = useState(5555);
  const [exportPath, setExportPath] = useState("");
  const [showExport, setShowExport] = useState(false);

  const embodimentChoices = constants?.embodiment_choices ?? ["new_embodiment"];
  const modelChoices = models?.map((m) => `${m.name} | ${m.path}`) ?? [];

  function handleDeploy() {
    const path = modelPath.includes("|")
      ? modelPath.split("|").pop()!.trim()
      : modelPath;
    if (!path.trim()) return;
    deployModel.mutate({ model_path: path, embodiment_tag: embodiment, port });
  }

  const isRunning =
    serverInfo?.status === "running" || serverInfo?.alive === true;

  const exportCmd = exportPath.trim()
    ? `python -m gr00t.eval.run_gr00t_server --model_path ${exportPath} --embodiment_tag ${embodiment} --port ${port} --device cuda --host 0.0.0.0`
    : "";

  return (
    <div className="space-y-4">
      <h2 className="text-sm font-semibold text-wybe-text-bright">
        Deploy to Server
      </h2>

      <div className="grid grid-cols-3 gap-3">
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
        <div>
          <label className="block text-xs text-wybe-text-muted mb-1">
            Embodiment
          </label>
          <select
            value={embodiment}
            onChange={(e) => setEmbodiment(e.target.value)}
            className="w-full bg-wybe-bg-tertiary border border-wybe-border rounded px-3 py-1.5 text-sm text-wybe-text focus:outline-none focus:border-wybe-accent"
          >
            {embodimentChoices.map((e) => (
              <option key={e} value={e}>
                {e}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-xs text-wybe-text-muted mb-1">
            Port
          </label>
          <input
            type="number"
            value={port}
            onChange={(e) => setPort(parseInt(e.target.value) || 5555)}
            className="w-full bg-wybe-bg-tertiary border border-wybe-border rounded px-3 py-1.5 text-sm text-wybe-text focus:outline-none focus:border-wybe-accent"
          />
        </div>
      </div>

      <div className="flex gap-2">
        <button
          onClick={handleDeploy}
          disabled={!modelPath.trim() || deployModel.isPending}
          className="px-4 py-1.5 bg-wybe-accent text-wybe-bg-primary text-sm font-medium rounded hover:bg-wybe-accent-hover transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {deployModel.isPending ? "Deploying..." : "Deploy"}
        </button>
        <button
          onClick={() => stopServer.mutate()}
          disabled={!isRunning || stopServer.isPending}
          className="px-4 py-1.5 bg-wybe-danger/20 text-wybe-danger text-sm font-medium rounded hover:bg-wybe-danger/30 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {stopServer.isPending ? "Stopping..." : "Stop Server"}
        </button>
      </div>

      {(deployModel.isError || stopServer.isError) && (
        <p className="text-xs text-wybe-danger">
          {((deployModel.error || stopServer.error) as Error)?.message}
        </p>
      )}

      {/* Server Status */}
      {serverInfo && (
        <div className="bg-wybe-bg-tertiary border border-wybe-border rounded-lg p-3 text-sm space-y-1">
          <div className="flex items-center gap-2">
            <span
              className={`w-2 h-2 rounded-full ${isRunning ? "bg-green-500" : "bg-wybe-text-muted"}`}
            />
            <span className="text-wybe-text-muted">
              Status:{" "}
              <span className="text-wybe-text">
                {serverInfo.status}
                {serverInfo.alive ? " (alive)" : ""}
              </span>
            </span>
          </div>
          {serverInfo.model_path && (
            <div className="text-xs text-wybe-text-muted">
              Model: {serverInfo.model_path}
            </div>
          )}
          {serverInfo.port > 0 && (
            <div className="text-xs text-wybe-text-muted">
              Port: {serverInfo.port}
            </div>
          )}
        </div>
      )}

      {/* Export Command Accordion */}
      <div className="bg-wybe-bg-secondary border border-wybe-border rounded-xl">
        <button
          onClick={() => setShowExport(!showExport)}
          className="w-full flex items-center justify-between px-4 py-3 text-sm font-medium text-wybe-text-bright hover:bg-wybe-bg-tertiary/50 transition-colors rounded-xl"
        >
          Export / Launch Command
          <span className="text-wybe-text-muted">
            {showExport ? "−" : "+"}
          </span>
        </button>
        {showExport && (
          <div className="px-4 pb-4 space-y-3">
            <div>
              <label className="block text-xs text-wybe-text-muted mb-1">
                Model Path
              </label>
              <input
                type="text"
                value={exportPath}
                onChange={(e) => setExportPath(e.target.value)}
                placeholder="Path to model checkpoint"
                className="w-full bg-wybe-bg-tertiary border border-wybe-border rounded px-3 py-1.5 text-sm text-wybe-text focus:outline-none focus:border-wybe-accent"
              />
            </div>
            {exportCmd && (
              <pre className="bg-wybe-bg-primary border border-wybe-border rounded p-3 text-xs text-wybe-text font-mono overflow-x-auto whitespace-pre-wrap">
                {exportCmd}
              </pre>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
