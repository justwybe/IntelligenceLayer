export interface Project {
  id: string;
  name: string;
  embodiment_tag: string;
  base_model: string;
  created_at: string;
  notes: string | null;
  dataset_count?: number;
  model_count?: number;
  run_count?: number;
}

export interface GPUInfo {
  name: string;
  utilization_pct: number;
  memory_used_mb: number;
  memory_total_mb: number;
  temperature_c: number;
  power_w: number;
}

export interface ActivityEntry {
  id: number;
  project_id: string | null;
  event_type: string;
  entity_type: string | null;
  entity_id: string | null;
  message: string;
  created_at: string;
}

export interface ServerInfo {
  model_path: string;
  embodiment_tag: string;
  port: number;
  status: string;
  alive: boolean;
}

export interface HealthInfo {
  status: string;
  gpu_available: boolean;
  gpu_count: number;
  db_ok: boolean;
  uptime_seconds: number;
}

// ── Datasets ────────────────────────────────────────────────────────

export interface Dataset {
  id: string;
  project_id: string | null;
  name: string;
  path: string;
  source: string | null;
  parent_dataset_id: string | null;
  episode_count: number | null;
  created_at: string;
  metadata: string | null;
}

export interface TrajectoryTrace {
  name: string;
  y: number[];
}

export interface EpisodeData {
  video_path: string | null;
  state_traces: TrajectoryTrace[];
  action_traces: TrajectoryTrace[];
  task_description: string;
}

export interface InspectResult {
  info: string;
  modality: string;
  tasks: string;
  stats: string;
}

export interface DatasetConstants {
  embodiment_choices: string[];
  mimic_envs: string[];
  source_options: string[];
}

// ── Runs ────────────────────────────────────────────────────────────

export interface Run {
  id: string;
  project_id: string | null;
  run_type: string;
  dataset_id: string | null;
  model_id: string | null;
  config: string;
  status: string;
  started_at: string | null;
  completed_at: string | null;
  log_path: string | null;
  metrics: string | null;
  pid: number | null;
}

export interface RunStatus {
  status: string;
  log_tail: string;
}

// ── Training ─────────────────────────────────────────────────────────

export interface TrainingPreset {
  learning_rate: number;
  max_steps: number;
  global_batch_size: number;
  weight_decay: number;
  warmup_ratio: number;
  save_steps: number;
  shard_size: number;
  episode_sampling_rate: number;
}

export interface TrainingConstants {
  presets: Record<string, TrainingPreset>;
  embodiment_choices: string[];
  isaac_lab_envs: string[];
  rl_algorithms: string[];
  optimizer_choices: string[];
  lr_scheduler_choices: string[];
  deepspeed_stages: string[];
}

export interface LossPoint {
  step: number;
  loss: number;
}

export interface CheckpointInfo {
  path: string;
  step: number | null;
}

export interface TrainingMetrics {
  loss_curve: LossPoint[];
  checkpoints: CheckpointInfo[];
  current_step: number;
  max_steps: number;
  progress_pct: number;
  status: string;
}

// ── Models ───────────────────────────────────────────────────────────

export interface Model {
  id: string;
  project_id: string | null;
  name: string;
  path: string;
  source_run_id: string | null;
  base_model: string | null;
  embodiment_tag: string | null;
  step: number | null;
  created_at: string;
  notes: string | null;
}

// ── Simulation ──────────────────────────────────────────────────────

export interface SimulationConstants {
  sim_tasks: Record<string, string[]>;
  embodiment_choices: string[];
}

export interface SimMetric {
  name: string;
  value: string;
}

export interface EvalMetric {
  trajectory: number;
  mse: number;
  mae: number;
}

export interface EvalMetrics {
  sim_metrics: SimMetric[];
  eval_metrics: EvalMetric[];
}

export interface Artifact {
  filename: string;
  url: string;
}

// ── Evaluations ─────────────────────────────────────────────────────

export interface Evaluation {
  id: string;
  run_id: string;
  model_id: string | null;
  eval_type: string;
  metrics: string | null;
  artifacts: string | null;
  created_at: string;
}

export interface CompareEntry {
  model_name: string;
  model_id: string;
  eval_type: string;
  metrics: Record<string, number | string>;
}
