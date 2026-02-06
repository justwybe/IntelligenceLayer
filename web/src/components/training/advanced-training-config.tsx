"use client";

import { useState } from "react";
import type { TrainingConstants } from "@/types";

export interface AdvancedConfig {
  deepspeed_stage: string;
  num_gpus: number;
  gradient_checkpointing: boolean;
  optimizer: string;
  lr_scheduler: string;
  max_grad_norm: number;
  gradient_accumulation_steps: number;
  bf16: boolean;
  fp16: boolean;
  tf32: boolean;
  eval_enable: boolean;
  eval_steps: number;
  eval_split_ratio: number;
  color_jitter: boolean;
  brightness: number;
  contrast: number;
  saturation: number;
  hue: number;
  random_rotation: number;
  save_total_limit: number;
  state_dropout: number;
  dataloader_num_workers: number;
  enable_profiling: boolean;
}

export const DEFAULT_ADVANCED: AdvancedConfig = {
  deepspeed_stage: "2",
  num_gpus: 1,
  gradient_checkpointing: false,
  optimizer: "adamw_torch_fused",
  lr_scheduler: "cosine",
  max_grad_norm: 1.0,
  gradient_accumulation_steps: 1,
  bf16: true,
  fp16: false,
  tf32: true,
  eval_enable: false,
  eval_steps: 500,
  eval_split_ratio: 0.1,
  color_jitter: false,
  brightness: 0.3,
  contrast: 0.3,
  saturation: 0.3,
  hue: 0.1,
  random_rotation: 0,
  save_total_limit: 5,
  state_dropout: 0,
  dataloader_num_workers: 4,
  enable_profiling: false,
};

interface Props {
  config: AdvancedConfig;
  onChange: (config: AdvancedConfig) => void;
  constants: TrainingConstants | undefined;
}

function Select({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: string;
  options: string[];
  onChange: (v: string) => void;
}) {
  return (
    <div>
      <label className="block text-xs text-wybe-text-muted mb-1">{label}</label>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full bg-wybe-bg-tertiary border border-wybe-border rounded px-3 py-1.5 text-sm text-wybe-text focus:outline-none focus:border-wybe-accent"
      >
        {options.map((o) => (
          <option key={o} value={o}>
            {o}
          </option>
        ))}
      </select>
    </div>
  );
}

function NumberInput({
  label,
  value,
  onChange,
  step,
}: {
  label: string;
  value: number;
  onChange: (v: number) => void;
  step?: number;
}) {
  return (
    <div>
      <label className="block text-xs text-wybe-text-muted mb-1">{label}</label>
      <input
        type="number"
        value={value}
        onChange={(e) => onChange(parseFloat(e.target.value) || 0)}
        step={step}
        className="w-full bg-wybe-bg-tertiary border border-wybe-border rounded px-3 py-1.5 text-sm text-wybe-text focus:outline-none focus:border-wybe-accent"
      />
    </div>
  );
}

function Checkbox({
  label,
  checked,
  onChange,
}: {
  label: string;
  checked: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <label className="flex items-center gap-2 text-sm text-wybe-text cursor-pointer">
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        className="rounded border-wybe-border bg-wybe-bg-tertiary accent-wybe-accent"
      />
      {label}
    </label>
  );
}

export function AdvancedTrainingConfig({ config, onChange, constants }: Props) {
  const [open, setOpen] = useState(false);

  function set<K extends keyof AdvancedConfig>(key: K, value: AdvancedConfig[K]) {
    onChange({ ...config, [key]: value });
  }

  return (
    <div className="border border-wybe-border rounded-lg">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-4 py-3 text-sm font-medium text-wybe-text-bright hover:bg-wybe-bg-secondary transition-colors rounded-lg"
      >
        Advanced Settings
        <span className="text-wybe-text-muted text-xs">
          {open ? "collapse" : "expand"}
        </span>
      </button>
      {open && (
        <div className="px-4 pb-4 space-y-4">
          {/* Distributed */}
          <p className="text-xs font-semibold text-wybe-text-bright mt-2">Distributed</p>
          <div className="grid grid-cols-3 gap-3">
            <Select
              label="DeepSpeed Stage"
              value={config.deepspeed_stage}
              options={constants?.deepspeed_stages ?? ["1", "2", "3"]}
              onChange={(v) => set("deepspeed_stage", v)}
            />
            <NumberInput
              label="Num GPUs"
              value={config.num_gpus}
              onChange={(v) => set("num_gpus", v)}
            />
            <div className="flex items-end pb-1">
              <Checkbox
                label="Gradient Ckpt"
                checked={config.gradient_checkpointing}
                onChange={(v) => set("gradient_checkpointing", v)}
              />
            </div>
          </div>

          {/* Optimization */}
          <p className="text-xs font-semibold text-wybe-text-bright">Optimization</p>
          <div className="grid grid-cols-2 gap-3">
            <Select
              label="Optimizer"
              value={config.optimizer}
              options={constants?.optimizer_choices ?? ["adamw_torch_fused"]}
              onChange={(v) => set("optimizer", v)}
            />
            <Select
              label="LR Scheduler"
              value={config.lr_scheduler}
              options={constants?.lr_scheduler_choices ?? ["cosine"]}
              onChange={(v) => set("lr_scheduler", v)}
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <NumberInput
              label="Max Grad Norm"
              value={config.max_grad_norm}
              onChange={(v) => set("max_grad_norm", v)}
              step={0.1}
            />
            <NumberInput
              label="Gradient Accum Steps"
              value={config.gradient_accumulation_steps}
              onChange={(v) => set("gradient_accumulation_steps", v)}
            />
          </div>

          {/* Precision */}
          <p className="text-xs font-semibold text-wybe-text-bright">Precision</p>
          <div className="flex gap-6">
            <Checkbox label="BF16" checked={config.bf16} onChange={(v) => set("bf16", v)} />
            <Checkbox label="FP16" checked={config.fp16} onChange={(v) => set("fp16", v)} />
            <Checkbox label="TF32" checked={config.tf32} onChange={(v) => set("tf32", v)} />
          </div>

          {/* Evaluation */}
          <p className="text-xs font-semibold text-wybe-text-bright">Evaluation During Training</p>
          <div className="grid grid-cols-3 gap-3">
            <div className="flex items-end pb-1">
              <Checkbox
                label="Enable Eval"
                checked={config.eval_enable}
                onChange={(v) => set("eval_enable", v)}
              />
            </div>
            <NumberInput
              label="Eval Steps"
              value={config.eval_steps}
              onChange={(v) => set("eval_steps", v)}
            />
            <NumberInput
              label="Eval Split Ratio"
              value={config.eval_split_ratio}
              onChange={(v) => set("eval_split_ratio", v)}
              step={0.01}
            />
          </div>

          {/* Image Augmentation */}
          <p className="text-xs font-semibold text-wybe-text-bright">Image Augmentation</p>
          <div className="grid grid-cols-3 gap-3">
            <div className="flex items-end pb-1">
              <Checkbox
                label="Color Jitter"
                checked={config.color_jitter}
                onChange={(v) => set("color_jitter", v)}
              />
            </div>
            <NumberInput
              label="Brightness"
              value={config.brightness}
              onChange={(v) => set("brightness", v)}
              step={0.1}
            />
            <NumberInput
              label="Contrast"
              value={config.contrast}
              onChange={(v) => set("contrast", v)}
              step={0.1}
            />
          </div>
          <div className="grid grid-cols-3 gap-3">
            <NumberInput
              label="Saturation"
              value={config.saturation}
              onChange={(v) => set("saturation", v)}
              step={0.1}
            />
            <NumberInput
              label="Hue"
              value={config.hue}
              onChange={(v) => set("hue", v)}
              step={0.05}
            />
            <NumberInput
              label="Rotation Angle"
              value={config.random_rotation}
              onChange={(v) => set("random_rotation", v)}
            />
          </div>

          {/* Saving & Other */}
          <p className="text-xs font-semibold text-wybe-text-bright">Saving & Other</p>
          <div className="grid grid-cols-2 gap-3">
            <NumberInput
              label="Save Total Limit"
              value={config.save_total_limit}
              onChange={(v) => set("save_total_limit", v)}
            />
            <NumberInput
              label="State Dropout"
              value={config.state_dropout}
              onChange={(v) => set("state_dropout", v)}
              step={0.01}
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <NumberInput
              label="Dataloader Workers"
              value={config.dataloader_num_workers}
              onChange={(v) => set("dataloader_num_workers", v)}
            />
            <div className="flex items-end pb-1">
              <Checkbox
                label="Enable Profiler"
                checked={config.enable_profiling}
                onChange={(v) => set("enable_profiling", v)}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
