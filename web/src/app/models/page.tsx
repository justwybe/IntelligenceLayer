"use client";

import { useState } from "react";
import { useProjectStore } from "@/stores/project-store";
import { ModelRegistry } from "@/components/models/model-registry";
import { DeployForm } from "@/components/models/deploy-form";
import { OptimizeForm } from "@/components/models/optimize-form";
import { BenchmarkForm } from "@/components/models/benchmark-form";
import { BenchmarkHistory } from "@/components/models/benchmark-history";

const TABS = ["Deploy to Fleet", "Optimize", "Benchmark"] as const;
type Tab = (typeof TABS)[number];

export default function ModelsPage() {
  const projectId = useProjectStore((s) => s.currentProjectId);
  const [activeTab, setActiveTab] = useState<Tab>("Deploy to Fleet");

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-[22px] font-bold text-wybe-text-bright">Models</h1>
        <p className="text-sm text-wybe-text-muted mt-1">Version & deploy</p>
      </div>

      {!projectId && (
        <div className="bg-wybe-bg-secondary border border-wybe-border rounded-xl p-6 text-center">
          <p className="text-sm text-wybe-text-muted">
            Select a project from the header to get started.
          </p>
        </div>
      )}

      {/* Model Registry (always visible) */}
      <div className="bg-wybe-bg-secondary border border-wybe-border rounded-xl p-4">
        <ModelRegistry projectId={projectId} />
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

      {/* Tab content */}
      {activeTab === "Deploy to Fleet" && (
        <div className="bg-wybe-bg-secondary border border-wybe-border rounded-xl p-4">
          <DeployForm projectId={projectId} />
        </div>
      )}

      {activeTab === "Optimize" && (
        <div className="bg-wybe-bg-secondary border border-wybe-border rounded-xl p-4">
          <OptimizeForm projectId={projectId} />
        </div>
      )}

      {activeTab === "Benchmark" && (
        <>
          <div className="bg-wybe-bg-secondary border border-wybe-border rounded-xl p-4">
            <BenchmarkForm projectId={projectId} />
          </div>
          <div className="bg-wybe-bg-secondary border border-wybe-border rounded-xl p-4">
            <BenchmarkHistory projectId={projectId} />
          </div>
        </>
      )}
    </div>
  );
}
