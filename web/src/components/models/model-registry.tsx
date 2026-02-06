"use client";

import { useState } from "react";
import {
  useModels,
  useModelsConstants,
  useRegisterModel,
} from "@/hooks/use-models";
import { useQueryClient } from "@tanstack/react-query";

interface Props {
  projectId: string | null;
}

export function ModelRegistry({ projectId }: Props) {
  const { data: models, isLoading } = useModels(projectId);
  const { data: constants } = useModelsConstants();
  const registerModel = useRegisterModel(projectId);
  const qc = useQueryClient();

  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [path, setPath] = useState("");
  const [embodiment, setEmbodiment] = useState("new_embodiment");
  const [step, setStep] = useState(0);
  const [baseModel, setBaseModel] = useState("nvidia/GR00T-N1.6-3B");
  const [status, setStatus] = useState("");

  const embodimentChoices = constants?.embodiment_choices ?? ["new_embodiment"];

  function handleRegister() {
    if (!name.trim() || !path.trim() || !projectId) return;
    registerModel.mutate(
      {
        name,
        path,
        embodiment_tag: embodiment,
        step: step || undefined,
        base_model: baseModel || undefined,
      },
      {
        onSuccess: (m) => {
          setStatus(`Model registered: ${m.id}`);
          setName("");
          setPath("");
          setStep(0);
        },
        onError: (err) => setStatus(`Error: ${(err as Error).message}`),
      },
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-wybe-text-bright">
          Model Registry
        </h2>
        <button
          onClick={() =>
            qc.invalidateQueries({ queryKey: ["models", projectId] })
          }
          className="px-3 py-1 text-xs font-medium bg-wybe-bg-tertiary text-wybe-text-muted rounded hover:text-wybe-text transition-colors"
        >
          Refresh
        </button>
      </div>

      <div className="bg-wybe-bg-secondary border border-wybe-border rounded-xl overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-wybe-border text-wybe-text-muted text-xs">
              <th className="text-left px-4 py-2 font-medium">Name</th>
              <th className="text-left px-4 py-2 font-medium">Path</th>
              <th className="text-left px-4 py-2 font-medium">Step</th>
              <th className="text-left px-4 py-2 font-medium">Embodiment</th>
              <th className="text-left px-4 py-2 font-medium">Base Model</th>
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              <tr>
                <td
                  colSpan={5}
                  className="px-4 py-3 text-center text-wybe-text-muted"
                >
                  Loading...
                </td>
              </tr>
            ) : !models || models.length === 0 ? (
              <tr>
                <td
                  colSpan={5}
                  className="px-4 py-3 text-center text-wybe-text-muted"
                >
                  No models registered
                </td>
              </tr>
            ) : (
              models.map((m) => (
                <tr
                  key={m.id}
                  className="border-b border-wybe-border last:border-0 hover:bg-wybe-bg-tertiary/50"
                >
                  <td className="px-4 py-2 text-wybe-text">{m.name}</td>
                  <td
                    className="px-4 py-2 text-wybe-text-muted font-mono text-xs truncate max-w-[200px]"
                    title={m.path}
                  >
                    {m.path}
                  </td>
                  <td className="px-4 py-2 text-wybe-text-muted">
                    {m.step ?? "-"}
                  </td>
                  <td className="px-4 py-2 text-wybe-text-muted">
                    {m.embodiment_tag ?? "-"}
                  </td>
                  <td className="px-4 py-2 text-wybe-text-muted text-xs">
                    {m.base_model ?? "-"}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Register Model Accordion */}
      <div className="bg-wybe-bg-secondary border border-wybe-border rounded-xl">
        <button
          onClick={() => setOpen(!open)}
          className="w-full flex items-center justify-between px-4 py-3 text-sm font-medium text-wybe-text-bright hover:bg-wybe-bg-tertiary/50 transition-colors rounded-xl"
        >
          Register Model Manually
          <span className="text-wybe-text-muted">{open ? "−" : "+"}</span>
        </button>
        {open && (
          <div className="px-4 pb-4 space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs text-wybe-text-muted mb-1">
                  Name
                </label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="my-finetuned-v1"
                  className="w-full bg-wybe-bg-tertiary border border-wybe-border rounded px-3 py-1.5 text-sm text-wybe-text focus:outline-none focus:border-wybe-accent"
                />
              </div>
              <div>
                <label className="block text-xs text-wybe-text-muted mb-1">
                  Checkpoint Path
                </label>
                <input
                  type="text"
                  value={path}
                  onChange={(e) => setPath(e.target.value)}
                  placeholder="/path/to/checkpoint-5000"
                  className="w-full bg-wybe-bg-tertiary border border-wybe-border rounded px-3 py-1.5 text-sm text-wybe-text focus:outline-none focus:border-wybe-accent"
                />
              </div>
            </div>
            <div className="grid grid-cols-3 gap-3">
              <div>
                <label className="block text-xs text-wybe-text-muted mb-1">
                  Embodiment Tag
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
                  Step
                </label>
                <input
                  type="number"
                  value={step}
                  onChange={(e) => setStep(parseInt(e.target.value) || 0)}
                  min={0}
                  className="w-full bg-wybe-bg-tertiary border border-wybe-border rounded px-3 py-1.5 text-sm text-wybe-text focus:outline-none focus:border-wybe-accent"
                />
              </div>
              <div>
                <label className="block text-xs text-wybe-text-muted mb-1">
                  Base Model
                </label>
                <input
                  type="text"
                  value={baseModel}
                  onChange={(e) => setBaseModel(e.target.value)}
                  className="w-full bg-wybe-bg-tertiary border border-wybe-border rounded px-3 py-1.5 text-sm text-wybe-text focus:outline-none focus:border-wybe-accent"
                />
              </div>
            </div>
            <div className="flex items-center gap-3">
              <button
                onClick={handleRegister}
                disabled={!name.trim() || !path.trim() || !projectId || registerModel.isPending}
                className="px-4 py-1.5 bg-wybe-accent text-wybe-bg-primary text-sm font-medium rounded hover:bg-wybe-accent-hover transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {registerModel.isPending ? "Registering..." : "Register Model"}
              </button>
              {status && (
                <span className="text-xs text-wybe-text-muted">{status}</span>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
