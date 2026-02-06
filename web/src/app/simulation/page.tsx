"use client";

import { useState } from "react";
import { useProjectStore } from "@/stores/project-store";
import { IsaacSimForm } from "@/components/simulation/isaac-sim-form";
import { IsaacSimMonitor } from "@/components/simulation/isaac-sim-monitor";
import { OpenLoopForm } from "@/components/simulation/open-loop-form";
import { OpenLoopMonitor } from "@/components/simulation/open-loop-monitor";
import { CompareModels } from "@/components/simulation/compare-models";
import { EvalHistory } from "@/components/simulation/eval-history";

const TABS = ["Isaac Sim Eval", "Open-Loop", "Compare"] as const;
type Tab = (typeof TABS)[number];

export default function SimulationPage() {
  const projectId = useProjectStore((s) => s.currentProjectId);
  const [activeTab, setActiveTab] = useState<Tab>("Isaac Sim Eval");
  const [simRunId, setSimRunId] = useState<string | null>(null);
  const [olRunId, setOlRunId] = useState<string | null>(null);

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-[22px] font-bold text-wybe-text-bright">
          Simulation
        </h1>
        <p className="text-sm text-wybe-text-muted mt-1">
          Test in virtual world
        </p>
      </div>

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

      {/* Isaac Sim Eval */}
      {activeTab === "Isaac Sim Eval" && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div>
            <h2 className="text-sm font-semibold text-wybe-text-bright mb-3">
              Simulation Configuration
            </h2>
            <div className="bg-wybe-bg-secondary border border-wybe-border rounded-xl p-4">
              <IsaacSimForm
                projectId={projectId}
                activeRunId={simRunId}
                onRunStarted={setSimRunId}
              />
            </div>
          </div>
          <div>
            <h2 className="text-sm font-semibold text-wybe-text-bright mb-3">
              Simulation Monitor
            </h2>
            <div className="bg-wybe-bg-secondary border border-wybe-border rounded-xl p-4">
              <IsaacSimMonitor runId={simRunId} />
            </div>
          </div>
        </div>
      )}

      {/* Open-Loop Evaluation */}
      {activeTab === "Open-Loop" && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div>
            <h2 className="text-sm font-semibold text-wybe-text-bright mb-3">
              Evaluation Configuration
            </h2>
            <div className="bg-wybe-bg-secondary border border-wybe-border rounded-xl p-4">
              <OpenLoopForm
                projectId={projectId}
                activeRunId={olRunId}
                onRunStarted={setOlRunId}
              />
            </div>
          </div>
          <div>
            <h2 className="text-sm font-semibold text-wybe-text-bright mb-3">
              Evaluation Results
            </h2>
            <div className="bg-wybe-bg-secondary border border-wybe-border rounded-xl p-4">
              <OpenLoopMonitor runId={olRunId} />
            </div>
          </div>
        </div>
      )}

      {/* Compare Models */}
      {activeTab === "Compare" && (
        <div className="bg-wybe-bg-secondary border border-wybe-border rounded-xl p-4">
          <CompareModels projectId={projectId} />
        </div>
      )}

      {/* Evaluation History (always visible) */}
      <div>
        <h2 className="text-sm font-semibold text-wybe-text-bright mb-3">
          Evaluation History
        </h2>
        <div className="bg-wybe-bg-secondary border border-wybe-border rounded-xl p-4">
          <EvalHistory projectId={projectId} />
        </div>
      </div>
    </div>
  );
}
