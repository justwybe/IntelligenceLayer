"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { api } from "@/lib/api-client";

export default function LoginPage() {
  const router = useRouter();
  const [key, setKey] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      // Temporarily set cookie to test the key
      document.cookie = `wybe_api_key=${encodeURIComponent(key.trim())}; path=/; max-age=${60 * 60 * 24 * 365}; SameSite=Lax`;

      // Validate by hitting the authenticated projects endpoint
      await api.get<{ projects: unknown[] }>("/api/projects");
      router.replace("/datasets");
    } catch {
      // Clear the invalid cookie
      document.cookie =
        "wybe_api_key=; path=/; max-age=0; SameSite=Lax";
      setError("Invalid API key. Check your WYBE_API_KEY.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex items-center justify-center min-h-[calc(100vh-7rem)]">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-wybe-text-bright">
            wybe<span className="text-wybe-accent">.</span>
          </h1>
          <p className="text-sm text-wybe-text-muted mt-2">
            Enter your API key to continue
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <input
              type="password"
              value={key}
              onChange={(e) => setKey(e.target.value)}
              placeholder="WYBE_API_KEY"
              className="w-full bg-wybe-bg-secondary border border-wybe-border rounded-lg px-4 py-3 text-sm text-wybe-text placeholder:text-wybe-text-muted focus:outline-none focus:border-wybe-accent font-mono"
              autoFocus
            />
          </div>

          {error && (
            <p className="text-sm text-wybe-danger">{error}</p>
          )}

          <button
            type="submit"
            disabled={!key.trim() || loading}
            className="w-full bg-wybe-accent-dim hover:bg-wybe-accent text-white font-medium py-3 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? "Verifying..." : "Sign In"}
          </button>
        </form>

        <p className="text-xs text-wybe-text-muted text-center mt-6">
          Find your key in the <code className="font-mono">.env</code> file on
          the pod
        </p>
      </div>
    </div>
  );
}
