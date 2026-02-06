"use client";

import { useEffect, useRef, useState } from "react";

import type { GPUInfo } from "@/types";
import { ReconnectingWebSocket } from "@/lib/ws-client";

function getApiKey(): string {
  if (typeof document === "undefined") return "";
  const match = document.cookie.match(/(?:^|; )wybe_api_key=([^;]*)/);
  return match ? decodeURIComponent(match[1]) : "";
}

export function useGpu() {
  const [gpus, setGpus] = useState<GPUInfo[]>([]);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<ReconnectingWebSocket | null>(null);

  useEffect(() => {
    const token = getApiKey();
    const ws = new ReconnectingWebSocket("/ws/gpu", token);
    wsRef.current = ws;

    const interval = setInterval(() => {
      setConnected(ws.connected);
    }, 1000);

    const unsub = ws.onMessage((data) => {
      const msg = data as { gpus?: GPUInfo[] };
      if (msg.gpus) {
        setGpus(msg.gpus);
      }
    });

    return () => {
      clearInterval(interval);
      unsub();
      ws.dispose();
    };
  }, []);

  return { gpus, connected };
}
