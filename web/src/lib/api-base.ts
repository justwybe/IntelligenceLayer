/**
 * Shared utility for resolving the FastAPI base URL.
 *
 * On RunPod, the browser loads the Next.js app via the port-3000 proxy.
 * Rather than double-proxying API calls through Next.js rewrites, we swap
 * the hostname to the port-8000 proxy so the browser talks directly to
 * FastAPI (same pattern the WebSocket client already uses).
 */

export function getApiBase(): string {
  // Explicit override always wins
  const env = process.env.NEXT_PUBLIC_API_URL;
  if (env) return env;

  // During SSR there is no window — fall back to Next.js rewrites
  if (typeof window === "undefined") return "";

  const { hostname, protocol } = window.location;

  // Local development → call FastAPI directly
  if (hostname === "localhost" || hostname === "127.0.0.1") {
    return "http://localhost:8000";
  }

  // RunPod proxy: swap port-3000 to port-8000
  if (hostname.includes("-3000.proxy.runpod.net")) {
    const apiHost = hostname.replace(/-3000\.proxy\.runpod\.net$/, "-8000.proxy.runpod.net");
    const scheme = protocol === "https:" ? "https:" : "http:";
    return `${scheme}//${apiHost}`;
  }

  // Unknown environment — fall back to Next.js rewrites
  return "";
}

export function getWsBase(): string {
  const env = process.env.NEXT_PUBLIC_WS_URL;
  if (env) return env;

  const httpBase = getApiBase();

  // No base resolved (SSR or unknown) — default to localhost WS
  if (!httpBase) {
    return typeof window === "undefined"
      ? "ws://localhost:8000"
      : "";
  }

  // Convert http(s) → ws(s)
  return httpBase.replace(/^http/, "ws");
}
