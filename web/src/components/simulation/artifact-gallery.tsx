"use client";

import type { Artifact } from "@/types";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Props {
  artifacts: Artifact[];
}

export function ArtifactGallery({ artifacts }: Props) {
  if (artifacts.length === 0) {
    return (
      <p className="text-xs text-wybe-text-muted">
        No trajectory plots yet
      </p>
    );
  }

  return (
    <div className="grid grid-cols-2 gap-3">
      {artifacts.map((a) => (
        <div
          key={a.filename}
          className="bg-wybe-bg-primary border border-wybe-border rounded-lg overflow-hidden"
        >
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={`${BASE_URL}${a.url}`}
            alt={a.filename}
            className="w-full h-auto"
          />
          <p className="text-[10px] text-wybe-text-muted px-2 py-1 truncate">
            {a.filename}
          </p>
        </div>
      ))}
    </div>
  );
}
