"use client";

import { useState } from "react";
import { useRegisterModel } from "@/hooks/use-models";

interface Props {
  projectId: string | null;
  defaultPath?: string;
}

export function RegisterModelForm({ projectId, defaultPath = "" }: Props) {
  const [path, setPath] = useState(defaultPath);
  const [name, setName] = useState("");
  const registerModel = useRegisterModel(projectId);

  function handleRegister() {
    if (!path.trim() || !name.trim() || !projectId) return;

    const stepMatch = path.match(/checkpoint-(\d+)/);
    registerModel.mutate(
      {
        name,
        path,
        step: stepMatch ? parseInt(stepMatch[1]) : undefined,
      },
      {
        onSuccess: () => {
          setName("");
          setPath("");
        },
      },
    );
  }

  // Sync defaultPath prop changes
  if (defaultPath && defaultPath !== path && !registerModel.isSuccess) {
    setPath(defaultPath);
  }

  return (
    <div className="space-y-2">
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
        <div>
          <label className="block text-xs text-wybe-text-muted mb-1">
            Checkpoint Path
          </label>
          <input
            type="text"
            value={path}
            onChange={(e) => setPath(e.target.value)}
            placeholder="/outputs/checkpoint-5000"
            className="w-full bg-wybe-bg-tertiary border border-wybe-border rounded px-3 py-1.5 text-sm text-wybe-text focus:outline-none focus:border-wybe-accent"
          />
        </div>
        <div>
          <label className="block text-xs text-wybe-text-muted mb-1">
            Model Name
          </label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="my-model-v1"
            className="w-full bg-wybe-bg-tertiary border border-wybe-border rounded px-3 py-1.5 text-sm text-wybe-text focus:outline-none focus:border-wybe-accent"
          />
        </div>
      </div>
      <button
        onClick={handleRegister}
        disabled={!path.trim() || !name.trim() || !projectId || registerModel.isPending}
        className="px-3 py-1.5 bg-wybe-accent text-wybe-bg-primary text-xs font-medium rounded hover:bg-wybe-accent-hover transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {registerModel.isPending ? "Registering..." : "Register as Model"}
      </button>
      {registerModel.isSuccess && (
        <p className="text-xs text-wybe-success">Model registered successfully</p>
      )}
      {registerModel.isError && (
        <p className="text-xs text-wybe-danger">
          {(registerModel.error as Error).message}
        </p>
      )}
    </div>
  );
}
