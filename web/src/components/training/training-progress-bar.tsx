"use client";

interface Props {
  currentStep: number;
  maxSteps: number;
  progressPct: number;
  status: string;
}

export function TrainingProgressBar({ currentStep, maxSteps, progressPct, status }: Props) {
  const isActive = status === "running" || status === "pending";

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-xs text-wybe-text-muted">
        <span>
          {currentStep.toLocaleString()} / {maxSteps.toLocaleString()} steps
        </span>
        <span>{progressPct.toFixed(1)}%</span>
      </div>
      <div className="w-full bg-wybe-bg-tertiary rounded-full h-2.5 overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-500 ${
            isActive ? "bg-wybe-accent animate-pulse" : "bg-wybe-success"
          }`}
          style={{ width: `${Math.min(progressPct, 100)}%` }}
        />
      </div>
    </div>
  );
}
