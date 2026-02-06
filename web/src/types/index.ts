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
