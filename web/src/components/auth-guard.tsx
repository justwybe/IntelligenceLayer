"use client";

import { useSyncExternalStore } from "react";
import { usePathname, useRouter } from "next/navigation";

function getCookie(): boolean {
  if (typeof document === "undefined") return false;
  return document.cookie.includes("wybe_api_key=");
}

function subscribe(cb: () => void): () => void {
  // Re-check on visibilitychange (covers tab-switch cookie changes)
  document.addEventListener("visibilitychange", cb);
  return () => document.removeEventListener("visibilitychange", cb);
}

export function AuthGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const hasKey = useSyncExternalStore(subscribe, getCookie, () => false);

  if (pathname === "/login") {
    return <>{children}</>;
  }

  if (!hasKey) {
    router.replace("/login");
    return null;
  }

  return <>{children}</>;
}
