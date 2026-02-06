"use client";

import { useCallback, useRef, useState } from "react";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function getApiKey(): string {
  if (typeof document === "undefined") return "";
  const match = document.cookie.match(/(?:^|; )wybe_api_key=([^;]*)/);
  return match ? decodeURIComponent(match[1]) : "";
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  toolCalls?: ToolActivity[];
}

export interface ToolActivity {
  name: string;
  input?: Record<string, unknown>;
  output?: string;
  isError?: boolean;
}

type ChatStatus = "ready" | "streaming" | "error";

interface UseChatOptions {
  projectId?: string | null;
  currentPage?: string;
}

export function useChat({ projectId, currentPage }: UseChatOptions = {}) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [status, setStatus] = useState<ChatStatus>("ready");
  const sessionIdRef = useRef<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const sendMessage = useCallback(
    async (text: string) => {
      if (!text.trim() || status === "streaming") return;

      // Add user message
      const userMsg: ChatMessage = { role: "user", content: text };
      setMessages((prev) => [...prev, userMsg]);
      setStatus("streaming");

      // Prepare assistant message placeholder
      let assistantContent = "";
      const toolCalls: ToolActivity[] = [];
      let pendingTool: Partial<ToolActivity> | null = null;

      const updateAssistant = () => {
        setMessages((prev) => {
          const next = [...prev];
          const lastIdx = next.length - 1;
          if (lastIdx >= 0 && next[lastIdx].role === "assistant") {
            next[lastIdx] = {
              role: "assistant",
              content: assistantContent,
              toolCalls: toolCalls.length > 0 ? [...toolCalls] : undefined,
            };
          } else {
            next.push({
              role: "assistant",
              content: assistantContent,
              toolCalls: toolCalls.length > 0 ? [...toolCalls] : undefined,
            });
          }
          return next;
        });
      };

      // Add initial empty assistant message
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "" },
      ]);

      const abort = new AbortController();
      abortRef.current = abort;

      try {
        const headers: Record<string, string> = {
          "Content-Type": "application/json",
        };
        const key = getApiKey();
        if (key) headers["Authorization"] = `Bearer ${key}`;

        const res = await fetch(`${BASE_URL}/api/chat`, {
          method: "POST",
          headers,
          body: JSON.stringify({
            message: text,
            session_id: sessionIdRef.current,
            project_id: projectId ?? undefined,
            current_page: currentPage ?? undefined,
          }),
          signal: abort.signal,
        });

        if (!res.ok) {
          const errText = await res.text().catch(() => res.statusText);
          throw new Error(`API ${res.status}: ${errText}`);
        }

        const reader = res.body?.getReader();
        if (!reader) throw new Error("No response body");

        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          // Keep the last (possibly incomplete) line in the buffer
          buffer = lines.pop() ?? "";

          for (const line of lines) {
            if (!line.startsWith("data: ")) continue;
            const payload = line.slice(6);
            if (payload === "[DONE]") continue;

            let event: Record<string, unknown>;
            try {
              event = JSON.parse(payload);
            } catch {
              continue;
            }

            switch (event.type) {
              case "session":
                sessionIdRef.current = event.session_id as string;
                break;
              case "text":
                assistantContent += event.content as string;
                updateAssistant();
                break;
              case "tool_call":
                // Flush any pending tool
                if (pendingTool) {
                  toolCalls.push(pendingTool as ToolActivity);
                }
                pendingTool = {
                  name: event.name as string,
                  input: event.input as Record<string, unknown>,
                };
                updateAssistant();
                break;
              case "tool_result":
                if (pendingTool && pendingTool.name === event.name) {
                  pendingTool.output = event.output as string;
                  pendingTool.isError = event.is_error as boolean;
                  toolCalls.push(pendingTool as ToolActivity);
                  pendingTool = null;
                } else {
                  toolCalls.push({
                    name: event.name as string,
                    output: event.output as string,
                    isError: event.is_error as boolean,
                  });
                }
                updateAssistant();
                break;
              case "error":
                assistantContent += event.content as string;
                updateAssistant();
                setStatus("error");
                return;
            }
          }
        }

        // Flush any remaining pending tool
        if (pendingTool) {
          toolCalls.push(pendingTool as ToolActivity);
          updateAssistant();
        }

        setStatus("ready");
      } catch (err) {
        if ((err as Error).name === "AbortError") {
          setStatus("ready");
          return;
        }
        assistantContent += `\n\n*Error: ${(err as Error).message}*`;
        updateAssistant();
        setStatus("error");
      } finally {
        abortRef.current = null;
      }
    },
    [status, projectId, currentPage],
  );

  const stop = useCallback(() => {
    abortRef.current?.abort();
  }, []);

  const clearMessages = useCallback(() => {
    setMessages([]);
    sessionIdRef.current = null;
  }, []);

  return { messages, status, sendMessage, stop, clearMessages };
}
