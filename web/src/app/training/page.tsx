"use client";

import { useState } from "react";
import { useProjectStore } from "@/stores/project-store";
import { TrainingConfigForm } from "@/components/training/training-config-form";
import { TrainingMonitor } from "@/components/training/training-monitor";
import { IsaacLabRlForm } from "@/components/training/isaac-lab-rl-form";
import { TrainingRunHistory } from "@/components/training/training-run-history";

const TABS = ["GR00T Finetune", "Isaac Lab RL"] as const;
type Tab = (typeof TABS)[number];

export default function TrainingPage() {
  const projectId = useProjectStore((s) => s.currentProjectId);
  const [activeTab, setActiveTab] = useState<Tab>("GR00T Finetune");
  const [activeRunId, setActiveRunId] = useState<string | null>(null);

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-[22px] font-bold text-wybe-text-bright">Training</h1>
        <p className="text-sm text-wybe-text-muted mt-1">
          Train policies (RL, IL, VLA)
        </p>
      </div>

      {!projectId && (
        <div className="bg-wybe-bg-secondary border border-wybe-border rounded-xl p-6 text-center">
          <p className="text-sm text-wybe-text-muted">
            Select a project from the header to get started.
          </p>
        </div>
      )}

      {/* Tab bar */}
      <div className="flex gap-1 border-b border-wybe-border">
        {TABS.map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px ${
              activeTab === tab
                ? "text-wybe-accent border-wybe-accent"
                : "text-wybe-text-muted border-transparent hover:text-wybe-text"
            }`}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* GR00T Finetune */}
      {activeTab === "GR00T Finetune" && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Left: Configuration */}
          <div>
            <h2 className="text-sm font-semibold text-wybe-text-bright mb-3">
              Training Configuration
            </h2>
            <div className="bg-wybe-bg-secondary border border-wybe-border rounded-xl p-4">
              <TrainingConfigForm
                projectId={projectId}
                onRunStarted={setActiveRunId}
                activeRunId={activeRunId}
              />
            </div>
          </div>

          {/* Right: Monitoring */}
          <div>
            <h2 className="text-sm font-semibold text-wybe-text-bright mb-3">
              Active Run Monitor
            </h2>
            <div className="bg-wybe-bg-secondary border border-wybe-border rounded-xl p-4">
              <TrainingMonitor
                runId={activeRunId}
                projectId={projectId}
              />
            </div>
          </div>
        </div>
      )}

      {/* Isaac Lab RL */}
      {activeTab === "Isaac Lab RL" && (
        <div className="bg-wybe-bg-secondary border border-wybe-border rounded-xl p-4">
          <IsaacLabRlForm projectId={projectId} />
        </div>
      )}

      {/* Run History (always visible) */}
      <div>
        <h2 className="text-sm font-semibold text-wybe-text-bright mb-3">
          Run History
        </h2>
        <div className="bg-wybe-bg-secondary border border-wybe-border rounded-xl p-4">
          <TrainingRunHistory projectId={projectId} />
        </div>
      </div>
    </div>
  );
}
