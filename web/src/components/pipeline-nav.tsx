"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const TABS = [
  { label: "Datasets", href: "/datasets" },
  { label: "Training", href: "/training" },
  { label: "Simulation", href: "/simulation" },
  { label: "Models", href: "/models" },
] as const;

export function PipelineNav() {
  const pathname = usePathname();

  return (
    <nav className="flex border-b border-wybe-border bg-wybe-bg-secondary px-2">
      {TABS.map((tab) => {
        const active = pathname.startsWith(tab.href);
        return (
          <Link
            key={tab.href}
            href={tab.href}
            className={`
              px-5 py-2.5 text-sm font-medium border-b-2 transition-colors
              ${
                active
                  ? "text-wybe-accent border-wybe-accent"
                  : "text-wybe-text-muted border-transparent hover:text-wybe-text"
              }
            `}
          >
            {tab.label}
          </Link>
        );
      })}
    </nav>
  );
}
