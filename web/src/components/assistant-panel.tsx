"use client";

import { useEffect, useRef, useState } from "react";
import { usePathname } from "next/navigation";

import { useProjectStore } from "@/stores/project-store";
import { useChat, type ChatMessage, type ToolActivity } from "@/hooks/use-chat";

const GREETING =
  "Hey — I'm your Wybe assistant. I know the full GR00T N1.6 pipeline inside and out: " +
  "**data → training → simulation → deployment**.\n\n" +
  "I can help you with anything:\n" +
  '- **"Walk me through the whole workflow"** — I\'ll guide you step by step\n' +
  '- **"Import my dataset"** — I\'ll handle the LeRobot v2 format\n' +
  '- **"What learning rate should I use?"** — I\'ll explain the trade-offs\n' +
  '- **"Train on my data"** — I\'ll configure and launch it\n' +
  '- **"Evaluate my model"** — open-loop eval, sim rollouts, benchmarks\n' +
  '- **"Deploy to my robot"** — policy server, ONNX, TensorRT\n\n' +
  "What are you working on?";

function pageFromPathname(pathname: string): string {
  if (pathname.includes("/training")) return "training";
  if (pathname.includes("/simulation")) return "simulation";
  if (pathname.includes("/models")) return "models";
  return "datasets";
}

function ToolBlock({ tool }: { tool: ToolActivity }) {
  return (
    <details className="mt-1 border border-wybe-border rounded-md text-xs">
      <summary className="px-2 py-1 cursor-pointer text-wybe-text-muted hover:text-wybe-text">
        {tool.isError ? "⚠ " : "⚙ "}
        {tool.name}
        {tool.output != null && (
          <span className="ml-1 text-wybe-text-muted">— done</span>
        )}
      </summary>
      {tool.input && (
        <pre className="px-2 py-1 bg-wybe-bg overflow-x-auto text-wybe-text-muted whitespace-pre-wrap">
          {JSON.stringify(tool.input, null, 2)}
        </pre>
      )}
      {tool.output != null && (
        <pre className="px-2 py-1 bg-wybe-bg border-t border-wybe-border overflow-x-auto text-wybe-text-muted whitespace-pre-wrap">
          {tool.output.length > 500
            ? tool.output.slice(0, 500) + "…"
            : tool.output}
        </pre>
      )}
    </details>
  );
}

/** Render markdown-like bold (**text**) and line breaks. */
function SimpleMarkdown({ text }: { text: string }) {
  const lines = text.split("\n");
  return (
    <div className="space-y-1">
      {lines.map((line, i) => (
        <p key={i} className={line === "" ? "h-2" : ""}>
          {line.split(/(\*\*[^*]+\*\*)/).map((seg, j) =>
            seg.startsWith("**") && seg.endsWith("**") ? (
              <strong key={j} className="text-wybe-text-bright font-semibold">
                {seg.slice(2, -2)}
              </strong>
            ) : (
              <span key={j}>{seg}</span>
            ),
          )}
        </p>
      ))}
    </div>
  );
}

function MessageBubble({ msg }: { msg: ChatMessage }) {
  const isUser = msg.role === "user";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[85%] rounded-lg px-3 py-2 text-sm ${
          isUser
            ? "bg-wybe-accent/20 text-wybe-text"
            : "bg-wybe-bg-tertiary text-wybe-text"
        }`}
      >
        <SimpleMarkdown text={msg.content} />
        {msg.toolCalls?.map((tool, i) => <ToolBlock key={i} tool={tool} />)}
      </div>
    </div>
  );
}

export function AssistantPanel() {
  const { assistantVisible, setAssistantVisible, currentProjectId } =
    useProjectStore();
  const pathname = usePathname();
  const currentPage = pageFromPathname(pathname);

  const { messages, status, sendMessage, stop, clearMessages } = useChat({
    projectId: currentProjectId,
    currentPage,
  });

  const [input, setInput] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Auto-scroll on new messages
  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages]);

  // Focus input when panel opens
  useEffect(() => {
    if (assistantVisible) inputRef.current?.focus();
  }, [assistantVisible]);

  if (!assistantVisible) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;
    sendMessage(input);
    setInput("");
  };

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-40"
        onClick={() => setAssistantVisible(false)}
      />

      {/* Panel */}
      <div className="fixed right-0 top-14 w-96 h-[calc(100vh-3.5rem)] bg-wybe-bg-secondary border-l border-wybe-border z-50 flex flex-col shadow-[-4px_0_12px_rgba(0,0,0,0.3)]">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-wybe-border">
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-semibold text-wybe-text-bright">
              Wybe Assistant
            </h3>
            <span
              className={`w-2 h-2 rounded-full ${
                status === "streaming"
                  ? "bg-wybe-accent animate-pulse-dot"
                  : status === "error"
                    ? "bg-wybe-danger"
                    : "bg-wybe-success"
              }`}
            />
          </div>
          <button
            onClick={clearMessages}
            className="text-xs text-wybe-text-muted hover:text-wybe-text"
          >
            Clear
          </button>
        </div>

        {/* Messages */}
        <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-3">
          {/* Greeting */}
          {messages.length === 0 && (
            <div className="bg-wybe-bg-tertiary rounded-lg px-3 py-2 text-sm text-wybe-text">
              <SimpleMarkdown text={GREETING} />
            </div>
          )}
          {messages.map((msg, i) => (
            <MessageBubble key={i} msg={msg} />
          ))}
          {status === "streaming" &&
            messages.length > 0 &&
            messages[messages.length - 1].content === "" &&
            !messages[messages.length - 1].toolCalls?.length && (
              <div className="flex justify-start">
                <div className="bg-wybe-bg-tertiary rounded-lg px-3 py-2 text-sm text-wybe-text-muted animate-pulse">
                  Thinking…
                </div>
              </div>
            )}
        </div>

        {/* Input */}
        <form
          onSubmit={handleSubmit}
          className="border-t border-wybe-border px-4 py-3 flex items-center gap-2"
        >
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask anything…"
            className="flex-1 bg-wybe-bg-tertiary border border-wybe-border rounded-lg px-3 py-2 text-sm text-wybe-text placeholder:text-wybe-text-muted focus:outline-none focus:border-wybe-accent"
            disabled={status === "streaming"}
          />
          {status === "streaming" ? (
            <button
              type="button"
              onClick={stop}
              className="bg-wybe-danger/20 text-wybe-danger border border-wybe-danger/30 rounded-lg px-3 py-2 text-sm hover:bg-wybe-danger/30 transition-colors"
            >
              Stop
            </button>
          ) : (
            <button
              type="submit"
              disabled={!input.trim()}
              className="bg-wybe-accent/20 text-wybe-accent border border-wybe-accent/30 rounded-lg px-3 py-2 text-sm hover:bg-wybe-accent/30 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
            >
              Send
            </button>
          )}
        </form>
      </div>
    </>
  );
}
