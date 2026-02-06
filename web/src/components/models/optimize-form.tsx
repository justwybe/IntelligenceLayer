"use client";

import { useState } from "react";
import { useModelsConstants } from "@/hooks/use-models";
import { useCreateRun, useRunStatus } from "@/hooks/use-runs";

interface Props {
  projectId: string | null;
}

export function OptimizeForm({ projectId }: Props) {
  const { data: constants } = useModelsConstants();
  const createRun = useCreateRun(projectId);

  // ONNX Export state
  const [onnxModelPath, setOnnxModelPath] = useState("");
  const [onnxDatasetPath, setOnnxDatasetPath] = useState("");
  const [onnxEmbodiment, setOnnxEmbodiment] = useState("new_embodiment");
  const [onnxOutputDir, setOnnxOutputDir] = useState("");
  const [onnxRunId, setOnnxRunId] = useState<string | null>(null);

  // TensorRT state
  const [trtOnnxPath, setTrtOnnxPath] = useState("");
  const [trtPrecision, setTrtPrecision] = useState("bf16");
  const [trtRunId, setTrtRunId] = useState<string | null>(null);

  const { data: onnxStatus } = useRunStatus(onnxRunId);
  const { data: trtStatus } = useRunStatus(trtRunId);

  const embodimentChoices = constants?.embodiment_choices ?? ["new_embodiment"];

  function handleOnnxExport() {
    if (
      !onnxModelPath.trim() ||
      !onnxDatasetPath.trim() ||
      !onnxOutputDir.trim() ||
      !projectId
    )
      return;
    createRun.mutate(
      {
        run_type: "onnx_export",
        config: {
          model_path: onnxModelPath,
          dataset_path: onnxDatasetPath,
          embodiment_tag: onnxEmbodiment,
          output_dir: onnxOutputDir,
        },
      },
      {
        onSuccess: (run) => {
          setOnnxRunId(run.id);
          // Auto-fill TRT onnx path
          const expectedOnnx = `${onnxOutputDir}/dit_model.onnx`;
          setTrtOnnxPath(expectedOnnx);
        },
      },
    );
  }

  function handleTrtBuild() {
    if (!trtOnnxPath.trim() || !projectId) return;
    const enginePath = trtOnnxPath.replace(".onnx", `.${trtPrecision}.trt`);
    createRun.mutate(
      {
        run_type: "tensorrt_build",
        config: {
          onnx_path: trtOnnxPath,
          engine_path: enginePath,
          precision: trtPrecision,
        },
      },
      { onSuccess: (run) => setTrtRunId(run.id) },
    );
  }

  return (
    <div className="space-y-6">
      {/* ONNX Export */}
      <div className="space-y-3">
        <h2 className="text-sm font-semibold text-wybe-text-bright">
          Export to ONNX
        </h2>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs text-wybe-text-muted mb-1">
              Model Path
            </label>
            <input
              type="text"
              value={onnxModelPath}
              onChange={(e) => setOnnxModelPath(e.target.value)}
              placeholder="/path/to/model"
              className="w-full bg-wybe-bg-tertiary border border-wybe-border rounded px-3 py-1.5 text-sm text-wybe-text focus:outline-none focus:border-wybe-accent"
            />
          </div>
          <div>
            <label className="block text-xs text-wybe-text-muted mb-1">
              Dataset Path
            </label>
            <input
              type="text"
              value={onnxDatasetPath}
              onChange={(e) => setOnnxDatasetPath(e.target.value)}
              placeholder="/path/to/dataset"
              className="w-full bg-wybe-bg-tertiary border border-wybe-border rounded px-3 py-1.5 text-sm text-wybe-text focus:outline-none focus:border-wybe-accent"
            />
          </div>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs text-wybe-text-muted mb-1">
              Embodiment Tag
            </label>
            <select
              value={onnxEmbodiment}
              onChange={(e) => setOnnxEmbodiment(e.target.value)}
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
              Output Dir
            </label>
            <input
              type="text"
              value={onnxOutputDir}
              onChange={(e) => setOnnxOutputDir(e.target.value)}
              placeholder="/path/to/onnx_output"
              className="w-full bg-wybe-bg-tertiary border border-wybe-border rounded px-3 py-1.5 text-sm text-wybe-text focus:outline-none focus:border-wybe-accent"
            />
          </div>
        </div>
        <button
          onClick={handleOnnxExport}
          disabled={
            !onnxModelPath.trim() ||
            !onnxDatasetPath.trim() ||
            !onnxOutputDir.trim() ||
            !projectId ||
            createRun.isPending
          }
          className="px-4 py-1.5 bg-wybe-accent text-wybe-bg-primary text-sm font-medium rounded hover:bg-wybe-accent-hover transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Export ONNX
        </button>

        {onnxStatus && (
          <div className="space-y-2">
            <div className="text-xs text-wybe-text-muted">
              Status: <span className="text-wybe-text">{onnxStatus.status}</span>
            </div>
            {onnxStatus.log_tail && (
              <pre className="bg-wybe-bg-primary border border-wybe-border rounded p-3 text-xs text-wybe-text-muted font-mono max-h-48 overflow-y-auto whitespace-pre-wrap">
                {onnxStatus.log_tail}
              </pre>
            )}
          </div>
        )}
      </div>

      <hr className="border-wybe-border" />

      {/* TensorRT Build */}
      <div className="space-y-3">
        <h2 className="text-sm font-semibold text-wybe-text-bright">
          Build TensorRT Engine
        </h2>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs text-wybe-text-muted mb-1">
              ONNX Path
            </label>
            <input
              type="text"
              value={trtOnnxPath}
              onChange={(e) => setTrtOnnxPath(e.target.value)}
              placeholder="Auto-filled from ONNX export"
              className="w-full bg-wybe-bg-tertiary border border-wybe-border rounded px-3 py-1.5 text-sm text-wybe-text focus:outline-none focus:border-wybe-accent"
            />
          </div>
          <div>
            <label className="block text-xs text-wybe-text-muted mb-1">
              Precision
            </label>
            <select
              value={trtPrecision}
              onChange={(e) => setTrtPrecision(e.target.value)}
              className="w-full bg-wybe-bg-tertiary border border-wybe-border rounded px-3 py-1.5 text-sm text-wybe-text focus:outline-none focus:border-wybe-accent"
            >
              <option value="bf16">bf16</option>
              <option value="fp16">fp16</option>
              <option value="fp32">fp32</option>
            </select>
          </div>
        </div>
        <button
          onClick={handleTrtBuild}
          disabled={!trtOnnxPath.trim() || !projectId || createRun.isPending}
          className="px-4 py-1.5 bg-wybe-accent text-wybe-bg-primary text-sm font-medium rounded hover:bg-wybe-accent-hover transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Build Engine
        </button>

        {trtStatus && (
          <div className="space-y-2">
            <div className="text-xs text-wybe-text-muted">
              Status: <span className="text-wybe-text">{trtStatus.status}</span>
            </div>
            {trtStatus.log_tail && (
              <pre className="bg-wybe-bg-primary border border-wybe-border rounded p-3 text-xs text-wybe-text-muted font-mono max-h-48 overflow-y-auto whitespace-pre-wrap">
                {trtStatus.log_tail}
              </pre>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
