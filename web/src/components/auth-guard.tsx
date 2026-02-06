"use client";

import { useRouter, usePathname } from "next/navigation";

function hasApiKeyCookie(): boolean {
  if (typeof document === "undefined") return false;
  return document.cookie.includes("wybe_api_key=");
}

export function AuthGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();

  // Skip guard on the login page itself
  if (pathname === "/login") {
    return <>{children}</>;
  }

  // Check for auth cookie — redirect to login if missing
  if (typeof document !== "undefined" && !hasApiKeyCookie()) {
    router.replace("/login");
    return null;
  }

  return <>{children}</>;
}
