"use client";

import { useState } from "react";
import { useTrainingMetrics } from "@/hooks/use-training";
import { useRunStatus } from "@/hooks/use-runs";
import { StatusBadge } from "@/components/ui/status-badge";
import { TrainingProgressBar } from "./training-progress-bar";
import { LossCurveChart } from "./loss-curve-chart";
import { CheckpointsTable } from "./checkpoints-table";
import { RegisterModelForm } from "./register-model-form";

interface Props {
  runId: string | null;
  projectId: string | null;
}

export function TrainingMonitor({ runId, projectId }: Props) {
  const { data: metrics } = useTrainingMetrics(runId, !!runId);
  const { data: runStatus } = useRunStatus(runId, !!runId);
  const [selectedCkpt, setSelectedCkpt] = useState("");

  if (!runId) {
    return (
      <div className="flex items-center justify-center h-64 text-sm text-wybe-text-muted">
        Launch a training run to see monitoring here
      </div>
    );
  }

  const status = metrics?.status ?? runStatus?.status ?? "pending";

  return (
    <div className="space-y-4">
      {/* Status */}
      <div className="flex items-center gap-3">
        <StatusBadge status={status} />
        <span className="text-xs text-wybe-text-muted font-mono">
          {runId.slice(0, 8)}
        </span>
      </div>

      {/* Progress */}
      {metrics && (
        <TrainingProgressBar
          currentStep={metrics.current_step}
          maxSteps={metrics.max_steps}
          progressPct={metrics.progress_pct}
          status={status}
        />
      )}

      {/* Log tail */}
      {runStatus?.log_tail && (
        <div>
          <p className="text-xs font-semibold text-wybe-text-bright mb-1">Training Log</p>
          <pre className="bg-wybe-bg-primary border border-wybe-border rounded-lg p-3 text-xs text-wybe-text font-mono max-h-48 overflow-auto whitespace-pre-wrap">
            {runStatus.log_tail}
          </pre>
        </div>
      )}

      {/* Loss curve */}
      {metrics && metrics.loss_curve.length > 0 && (
        <div>
          <p className="text-xs font-semibold text-wybe-text-bright mb-1">Loss Curve</p>
          <div className="bg-wybe-bg-primary border border-wybe-border rounded-lg p-3">
            <LossCurveChart data={metrics.loss_curve} />
          </div>
        </div>
      )}

      {/* Checkpoints */}
      {metrics && metrics.checkpoints.length > 0 && (
        <div>
          <p className="text-xs font-semibold text-wybe-text-bright mb-1">
            Saved Checkpoints
          </p>
          <div className="bg-wybe-bg-primary border border-wybe-border rounded-lg p-3">
            <CheckpointsTable
              checkpoints={metrics.checkpoints}
              onSelect={setSelectedCkpt}
            />
          </div>
        </div>
      )}

      {/* Register model */}
      <div>
        <p className="text-xs font-semibold text-wybe-text-bright mb-1">
          Register Checkpoint as Model
        </p>
        <div className="bg-wybe-bg-primary border border-wybe-border rounded-lg p-3">
          <RegisterModelForm
            projectId={projectId}
            defaultPath={selectedCkpt}
          />
        </div>
      </div>
    </div>
  );
}
