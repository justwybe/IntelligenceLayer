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
          <Section title="GR00T-Mimic Data Generation">
            <MimicStub />
          </Section>

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

function MimicStub() {
  const [env, setEnv] = useState("GR00T-Mimic-Cube-v0");
  const [numDemos, setNumDemos] = useState(10);

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <span className="text-xs font-medium bg-wybe-warning/20 text-wybe-warning px-2 py-0.5 rounded">
          Coming Soon
        </span>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-xs text-wybe-text-muted mb-1">Environment</label>
          <select
            value={env}
            onChange={(e) => setEnv(e.target.value)}
            className="w-full bg-wybe-bg-tertiary border border-wybe-border rounded px-3 py-1.5 text-sm text-wybe-text focus:outline-none focus:border-wybe-accent"
          >
            {[
              "GR00T-Mimic-Cube-v0",
              "GR00T-Mimic-PickPlace-v0",
              "GR00T-Mimic-Stack-v0",
              "GR00T-Mimic-Kitchen-v0",
              "GR00T-Mimic-Drawer-v0",
            ].map((e) => (
              <option key={e} value={e}>{e}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-xs text-wybe-text-muted mb-1">
            Num Demos: {numDemos}
          </label>
          <input
            type="range"
            min={1}
            max={100}
            value={numDemos}
            onChange={(e) => setNumDemos(parseInt(e.target.value))}
            className="w-full accent-wybe-accent"
          />
        </div>
      </div>
      <button
        disabled
        className="px-4 py-1.5 bg-wybe-accent text-wybe-bg-primary text-sm font-medium rounded opacity-50 cursor-not-allowed"
      >
        Generate Demos
      </button>
      <p className="text-xs text-wybe-text-muted">
        GR00T-Mimic synthetic data generation is not yet available.
      </p>
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
