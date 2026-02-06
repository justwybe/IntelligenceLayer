"use client";

import { useState, useCallback } from "react";
import { useDatasets } from "@/hooks/use-datasets";
import { useModels } from "@/hooks/use-models";
import { useCreateRun, useStopRun } from "@/hooks/use-runs";
import { useTrainingConstants } from "@/hooks/use-training";
import {
  AdvancedTrainingConfig,
  DEFAULT_ADVANCED,
  type AdvancedConfig,
} from "./advanced-training-config";
import { ResumeTrainingForm } from "./resume-training-form";
import type { TrainingPreset } from "@/types";

interface Props {
  projectId: string | null;
  onRunStarted: (runId: string) => void;
  activeRunId: string | null;
}

export function TrainingConfigForm({ projectId, onRunStarted, activeRunId }: Props) {
  const { data: constants } = useTrainingConstants();
  const { data: datasets } = useDatasets(projectId);
  const { data: models } = useModels(projectId);
  const createRun = useCreateRun(projectId);
  const stopRun = useStopRun();

  // Mode
  const [configMode, setConfigMode] = useState<"Quick Start" | "Custom">("Quick Start");
  const [preset, setPreset] = useState("Quick Start");

  // Core config
  const [dataset, setDataset] = useState("");
  const [baseModel, setBaseModel] = useState("nvidia/GR00T-N1.6-3B");
  const [embodiment, setEmbodiment] = useState("new_embodiment");

  // Tuning flags
  const [tuneLlm, setTuneLlm] = useState(false);
  const [tuneVisual, setTuneVisual] = useState(false);
  const [tuneProjector, setTuneProjector] = useState(true);
  const [tuneDiffusion, setTuneDiffusion] = useState(true);

  // Hyperparameters
  const [lr, setLr] = useState(1e-4);
  const [maxSteps, setMaxSteps] = useState(10000);
  const [batchSize, setBatchSize] = useState(64);
  const [weightDecay, setWeightDecay] = useState(1e-5);
  const [warmupRatio, setWarmupRatio] = useState(0.05);
  const [saveSteps, setSaveSteps] = useState(1000);
  const [shardSize, setShardSize] = useState(1024);
  const [episodeRate, setEpisodeRate] = useState(0.1);

  // Output
  const [outputDir, setOutputDir] = useState("./outputs");
  const [useWandb, setUseWandb] = useState(false);

  // Advanced
  const [advanced, setAdvanced] = useState<AdvancedConfig>(DEFAULT_ADVANCED);

  const presetNames = constants ? Object.keys(constants.presets) : ["Quick Start"];
  const embodimentChoices = constants?.embodiment_choices ?? ["new_embodiment"];

  const modelChoices = [
    "nvidia/GR00T-N1.6-3B",
    ...(models?.map((m) => `${m.name} | ${m.path}`) ?? []),
  ];

  const applyPreset = useCallback(
    (name: string) => {
      const p: TrainingPreset | undefined = constants?.presets[name];
      if (!p) return;
      setLr(p.learning_rate);
      setMaxSteps(p.max_steps);
      setBatchSize(p.global_batch_size);
      setWeightDecay(p.weight_decay);
      setWarmupRatio(p.warmup_ratio);
      setSaveSteps(p.save_steps);
      setShardSize(p.shard_size);
      setEpisodeRate(p.episode_sampling_rate);
    },
    [constants],
  );

  function buildConfig(resumeCheckpointPath?: string) {
    return {
      dataset_path: dataset,
      base_model: baseModel,
      embodiment_tag: embodiment,
      tune_llm: tuneLlm,
      tune_visual: tuneVisual,
      tune_projector: tuneProjector,
      tune_diffusion: tuneDiffusion,
      learning_rate: lr,
      max_steps: maxSteps,
      global_batch_size: batchSize,
      weight_decay: weightDecay,
      warmup_ratio: warmupRatio,
      save_steps: saveSteps,
      shard_size: shardSize,
      episode_sampling_rate: episodeRate,
      output_dir: outputDir,
      use_wandb: useWandb,
      ...advanced,
      ...(resumeCheckpointPath ? { resume_checkpoint_path: resumeCheckpointPath } : {}),
    };
  }

  function handleLaunch() {
    const datasetPath = dataset.includes("|") ? dataset.split("|")[1].trim() : dataset;
    if (!datasetPath.trim() || !projectId) return;

    createRun.mutate(
      {
        run_type: "training",
        config: buildConfig(),
      },
      { onSuccess: (run) => onRunStarted(run.id) },
    );
  }

  function handleResume(checkpointPath: string) {
    const datasetPath = dataset.includes("|") ? dataset.split("|")[1].trim() : dataset;
    if (!datasetPath.trim() || !projectId) return;

    createRun.mutate(
      {
        run_type: "training",
        config: buildConfig(checkpointPath),
      },
      { onSuccess: (run) => onRunStarted(run.id) },
    );
  }

  return (
    <div className="space-y-4">
      {/* Mode toggle */}
      <div className="flex gap-2">
        {(["Quick Start", "Custom"] as const).map((mode) => (
          <button
            key={mode}
            onClick={() => setConfigMode(mode)}
            className={`px-3 py-1 text-xs font-medium rounded transition-colors ${
              configMode === mode
                ? "bg-wybe-accent text-wybe-bg-primary"
                : "bg-wybe-bg-tertiary text-wybe-text-muted hover:text-wybe-text"
            }`}
          >
            {mode}
          </button>
        ))}
      </div>

      {/* Preset */}
      <div>
        <label className="block text-xs text-wybe-text-muted mb-1">Preset</label>
        <select
          value={preset}
          onChange={(e) => {
            setPreset(e.target.value);
            applyPreset(e.target.value);
          }}
          className="w-full bg-wybe-bg-tertiary border border-wybe-border rounded px-3 py-1.5 text-sm text-wybe-text focus:outline-none focus:border-wybe-accent"
        >
          {presetNames.map((p) => (
            <option key={p} value={p}>
              {p}
            </option>
          ))}
        </select>
      </div>

      {/* Dataset + Base Model + Embodiment */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div>
          <label className="block text-xs text-wybe-text-muted mb-1">Dataset</label>
          <select
            value={dataset}
            onChange={(e) => setDataset(e.target.value)}
            className="w-full bg-wybe-bg-tertiary border border-wybe-border rounded px-3 py-1.5 text-sm text-wybe-text focus:outline-none focus:border-wybe-accent"
          >
            <option value="">Select dataset...</option>
            {datasets?.map((ds) => (
              <option key={ds.id} value={`${ds.name} | ${ds.path}`}>
                {ds.name}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-xs text-wybe-text-muted mb-1">Base Model</label>
          <select
            value={baseModel}
            onChange={(e) => setBaseModel(e.target.value)}
            className="w-full bg-wybe-bg-tertiary border border-wybe-border rounded px-3 py-1.5 text-sm text-wybe-text focus:outline-none focus:border-wybe-accent"
          >
            {modelChoices.map((m) => (
              <option key={m} value={m}>
                {m}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div>
        <label className="block text-xs text-wybe-text-muted mb-1">Embodiment Tag</label>
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

      {/* Tuning Flags */}
      <div>
        <p className="text-xs font-semibold text-wybe-text-bright mb-2">Tuning Flags</p>
        <div className="flex gap-6">
          {[
            { label: "LLM", checked: tuneLlm, set: setTuneLlm },
            { label: "Visual", checked: tuneVisual, set: setTuneVisual },
            { label: "Projector", checked: tuneProjector, set: setTuneProjector },
            { label: "Diffusion", checked: tuneDiffusion, set: setTuneDiffusion },
          ].map(({ label, checked, set: setFn }) => (
            <label
              key={label}
              className="flex items-center gap-2 text-sm text-wybe-text cursor-pointer"
            >
              <input
                type="checkbox"
                checked={checked}
                onChange={(e) => setFn(e.target.checked)}
                className="rounded border-wybe-border bg-wybe-bg-tertiary accent-wybe-accent"
              />
              {label}
            </label>
          ))}
        </div>
      </div>

      {/* Hyperparameters */}
      {configMode === "Custom" && (
        <>
          <p className="text-xs font-semibold text-wybe-text-bright">Hyperparameters</p>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs text-wybe-text-muted mb-1">Learning Rate</label>
              <input
                type="number"
                value={lr}
                onChange={(e) => setLr(parseFloat(e.target.value) || 0)}
                step={1e-6}
                className="w-full bg-wybe-bg-tertiary border border-wybe-border rounded px-3 py-1.5 text-sm text-wybe-text focus:outline-none focus:border-wybe-accent"
              />
            </div>
            <div>
              <label className="block text-xs text-wybe-text-muted mb-1">Max Steps</label>
              <input
                type="number"
                value={maxSteps}
                onChange={(e) => setMaxSteps(parseInt(e.target.value) || 0)}
                step={100}
                className="w-full bg-wybe-bg-tertiary border border-wybe-border rounded px-3 py-1.5 text-sm text-wybe-text focus:outline-none focus:border-wybe-accent"
              />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs text-wybe-text-muted mb-1">Batch Size</label>
              <input
                type="number"
                value={batchSize}
                onChange={(e) => setBatchSize(parseInt(e.target.value) || 0)}
                className="w-full bg-wybe-bg-tertiary border border-wybe-border rounded px-3 py-1.5 text-sm text-wybe-text focus:outline-none focus:border-wybe-accent"
              />
            </div>
            <div>
              <label className="block text-xs text-wybe-text-muted mb-1">Weight Decay</label>
              <input
                type="number"
                value={weightDecay}
                onChange={(e) => setWeightDecay(parseFloat(e.target.value) || 0)}
                step={1e-6}
                className="w-full bg-wybe-bg-tertiary border border-wybe-border rounded px-3 py-1.5 text-sm text-wybe-text focus:outline-none focus:border-wybe-accent"
              />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs text-wybe-text-muted mb-1">Warmup Ratio</label>
              <input
                type="number"
                value={warmupRatio}
                onChange={(e) => setWarmupRatio(parseFloat(e.target.value) || 0)}
                step={0.01}
                min={0}
                max={0.5}
                className="w-full bg-wybe-bg-tertiary border border-wybe-border rounded px-3 py-1.5 text-sm text-wybe-text focus:outline-none focus:border-wybe-accent"
              />
            </div>
            <div>
              <label className="block text-xs text-wybe-text-muted mb-1">Save Steps</label>
              <input
                type="number"
                value={saveSteps}
                onChange={(e) => setSaveSteps(parseInt(e.target.value) || 0)}
                step={100}
                className="w-full bg-wybe-bg-tertiary border border-wybe-border rounded px-3 py-1.5 text-sm text-wybe-text focus:outline-none focus:border-wybe-accent"
              />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs text-wybe-text-muted mb-1">Shard Size</label>
              <input
                type="number"
                value={shardSize}
                onChange={(e) => setShardSize(parseInt(e.target.value) || 0)}
                className="w-full bg-wybe-bg-tertiary border border-wybe-border rounded px-3 py-1.5 text-sm text-wybe-text focus:outline-none focus:border-wybe-accent"
              />
            </div>
            <div>
              <label className="block text-xs text-wybe-text-muted mb-1">Episode Rate</label>
              <input
                type="number"
                value={episodeRate}
                onChange={(e) => setEpisodeRate(parseFloat(e.target.value) || 0)}
                step={0.01}
                min={0.01}
                max={1}
                className="w-full bg-wybe-bg-tertiary border border-wybe-border rounded px-3 py-1.5 text-sm text-wybe-text focus:outline-none focus:border-wybe-accent"
              />
            </div>
          </div>
        </>
      )}

      {/* Output */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div>
          <label className="block text-xs text-wybe-text-muted mb-1">Output Directory</label>
          <input
            type="text"
            value={outputDir}
            onChange={(e) => setOutputDir(e.target.value)}
            className="w-full bg-wybe-bg-tertiary border border-wybe-border rounded px-3 py-1.5 text-sm text-wybe-text focus:outline-none focus:border-wybe-accent"
          />
        </div>
        <div className="flex items-end pb-1">
          <label className="flex items-center gap-2 text-sm text-wybe-text cursor-pointer">
            <input
              type="checkbox"
              checked={useWandb}
              onChange={(e) => setUseWandb(e.target.checked)}
              className="rounded border-wybe-border bg-wybe-bg-tertiary accent-wybe-accent"
            />
            Log to W&B
          </label>
        </div>
      </div>

      {/* Advanced */}
      {configMode === "Custom" && (
        <AdvancedTrainingConfig
          config={advanced}
          onChange={setAdvanced}
          constants={constants}
        />
      )}

      {/* Action buttons */}
      <div className="flex gap-2">
        <button
          onClick={handleLaunch}
          disabled={!projectId || !dataset || createRun.isPending}
          className="px-4 py-1.5 bg-wybe-accent text-wybe-bg-primary text-sm font-medium rounded hover:bg-wybe-accent-hover transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {createRun.isPending ? "Launching..." : "Launch Training"}
        </button>
        {activeRunId && (
          <button
            onClick={() => stopRun.mutate(activeRunId)}
            disabled={stopRun.isPending}
            className="px-4 py-1.5 bg-wybe-danger/20 text-wybe-danger text-sm font-medium rounded hover:bg-wybe-danger/30 transition-colors disabled:opacity-50"
          >
            Stop Training
          </button>
        )}
      </div>

      {createRun.isError && (
        <p className="text-xs text-wybe-danger">
          {(createRun.error as Error).message}
        </p>
      )}

      {/* Resume */}
      <div className="border-t border-wybe-border pt-4">
        <p className="text-xs font-semibold text-wybe-text-bright mb-2">Resume Training</p>
        <ResumeTrainingForm
          onResume={handleResume}
          isPending={createRun.isPending}
        />
      </div>
    </div>
  );
}
