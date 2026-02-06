"use client";

import { useState } from "react";
import { useProjectStore } from "@/stores/project-store";
import { ImportDatasetForm } from "@/components/datasets/import-dataset-form";
import { EpisodeViewer } from "@/components/datasets/episode-viewer";
import { ComputeStatsForm } from "@/components/datasets/compute-stats-form";
import { ConvertDatasetForm } from "@/components/datasets/convert-dataset-form";
import { DatasetInspector } from "@/components/datasets/dataset-inspector";
import { DatasetRegistry } from "@/components/datasets/dataset-registry";
import { EmbodimentBrowser } from "@/components/datasets/embodiment-browser";

const TABS = ["Teleop Demos", "Urban Memory", "Synth / Mimic"] as const;
type Tab = (typeof TABS)[number];

export default function DatasetsPage() {
  const projectId = useProjectStore((s) => s.currentProjectId);
  const [activeTab, setActiveTab] = useState<Tab>("Teleop Demos");

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-[22px] font-bold text-wybe-text-bright">Datasets</h1>

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
      {activeTab === "Teleop Demos" && (
        <div className="space-y-8">
          <Section title="Import Dataset">
            <ImportDatasetForm projectId={projectId} />
          </Section>

          <Section title="Episode Viewer">
            <EpisodeViewer />
          </Section>

          <Section title="Compute Statistics">
            <ComputeStatsForm projectId={projectId} />
          </Section>
        </div>
      )}

      {activeTab === "Urban Memory" && (
        <div className="space-y-8">
          <Section title="Import from Robot Logs">
            <ImportDatasetForm
              projectId={projectId}
              defaultSource="urban_memory"
            />
          </Section>

          <Section title="Episode Viewer">
            <EpisodeViewer />
          </Section>
        </div>
      )}

      {activeTab === "Synth / Mimic" && (
        <div className="space-y-8">
          <Section title="Convert LeRobot v3 Dataset">
            <ConvertDatasetForm projectId={projectId} />
          </Section>

          <Section title="Dataset Inspector">
            <DatasetInspector />
          </Section>
        </div>
      )}

      {/* Shared bottom sections */}
      <Section title="Dataset Registry">
        <DatasetRegistry projectId={projectId} />
      </Section>

      <Collapsible title="Embodiment Config Browser">
        <EmbodimentBrowser />
      </Collapsible>
    </div>
  );
}

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <h2 className="text-sm font-semibold text-wybe-text-bright mb-3">
        {title}
      </h2>
      {children}
    </div>
  );
}

function Collapsible({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  const [open, setOpen] = useState(false);
  return (
    <div className="border border-wybe-border rounded-lg">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-4 py-3 text-sm font-medium text-wybe-text-bright hover:bg-wybe-bg-secondary transition-colors rounded-lg"
      >
        {title}
        <span className="text-wybe-text-muted text-xs">
          {open ? "collapse" : "expand"}
        </span>
      </button>
      {open && <div className="px-4 pb-4">{children}</div>}
    </div>
  );
}
