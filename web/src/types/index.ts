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
