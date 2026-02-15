"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import type { ChatMessage, ChatSource } from "@/lib/types";

export function ChatPanel() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [expandedSources, setExpandedSources] = useState<number | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Load history on mount
  useEffect(() => {
    fetch("/api/chat")
      .then((r) => r.json())
      .then((data) => {
        if (Array.isArray(data)) {
          setMessages(
            data.map((d: Record<string, unknown>) => ({
              id: d.id as number,
              question: d.question as string,
              answer: d.answer as string,
              timestamp: d.created_at as string,
            })),
          );
        }
      })
      .catch(() => {});
  }, []);

  // Auto-scroll
  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages, loading]);

  const send = useCallback(async () => {
    const q = input.trim();
    if (!q || loading) return;
    setInput("");
    setLoading(true);

    const tempMsg: ChatMessage = { question: q, answer: "" };
    setMessages((prev) => [...prev, tempMsg]);

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: q }),
      });
      const data = await res.json();

      setMessages((prev) => {
        const updated = [...prev];
        updated[updated.length - 1] = {
          question: q,
          answer: data.answer || data.error || "No response",
          sources: data.sources,
          total: data.total,
        };
        return updated;
      });
    } catch (e) {
      setMessages((prev) => {
        const updated = [...prev];
        updated[updated.length - 1] = {
          question: q,
          answer: `Error: ${e instanceof Error ? e.message : "Request failed"}`,
        };
        return updated;
      });
    } finally {
      setLoading(false);
    }
  }, [input, loading]);

  return (
    <div className="flex flex-col h-full">
      {/* Messages */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto px-3 py-2 space-y-4"
      >
        {messages.length === 0 && !loading && (
          <div className="text-center text-dim text-xs py-8">
            <p className="mb-2">Ask questions about the corpus</p>
            <div className="space-y-1 text-zinc-600">
              <p>&quot;Papers about blackboard architecture&quot;</p>
              <p>&quot;Contract net protocol in modern systems&quot;</p>
              <p>&quot;Multi-agent debate and verification&quot;</p>
            </div>
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} className="space-y-2">
            {/* Question */}
            <div className="flex justify-end">
              <div className="bg-accent/10 border border-accent/20 rounded-lg px-3 py-2 max-w-[85%] text-xs text-zinc-200">
                {msg.question}
              </div>
            </div>
            {/* Answer */}
            {msg.answer ? (
              <div className="space-y-1">
                <div className="bg-card border border-border rounded-lg px-3 py-2 text-xs text-zinc-300 leading-relaxed whitespace-pre-wrap">
                  {msg.answer}
                </div>
                {/* Sources toggle */}
                {msg.sources && msg.sources.length > 0 && (
                  <div>
                    <button
                      className="text-[10px] text-accent/60 hover:text-accent px-1 cursor-pointer"
                      onClick={() =>
                        setExpandedSources(expandedSources === i ? null : i)
                      }
                    >
                      {expandedSources === i
                        ? "hide sources"
                        : `${msg.sources.length} sources`}
                    </button>
                    {expandedSources === i && (
                      <SourceCards sources={msg.sources} />
                    )}
                  </div>
                )}
                {msg.total !== undefined && !msg.sources?.length && (
                  <div className="text-[10px] text-zinc-600 px-1">
                    {msg.total} results
                  </div>
                )}
              </div>
            ) : loading && i === messages.length - 1 ? (
              <div className="flex gap-1 px-3 py-2 text-accent">
                <span className="thinking-dot text-lg">.</span>
                <span className="thinking-dot text-lg">.</span>
                <span className="thinking-dot text-lg">.</span>
              </div>
            ) : null}
          </div>
        ))}
      </div>

      {/* Input */}
      <div className="border-t border-border p-2 flex gap-2">
        <input
          className="flex-1 bg-[#0a0a0f] border border-border rounded-md px-3 py-2 text-xs text-zinc-300 placeholder:text-zinc-600 focus:outline-none focus:border-accent/50 transition"
          placeholder="Ask about the corpus..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && send()}
          disabled={loading}
        />
        <button
          className="bg-accent/15 border border-accent/30 rounded-md px-3 py-1 text-xs text-accent hover:bg-accent/25 disabled:opacity-30 transition cursor-pointer"
          onClick={send}
          disabled={loading || !input.trim()}
        >
          &#x2192;
        </button>
      </div>
    </div>
  );
}

function SourceCards({ sources }: { sources: ChatSource[] }) {
  return (
    <div className="space-y-1 mt-1 max-h-48 overflow-y-auto">
      {sources.map((s) => (
        <a
          key={s.id}
          href={s.link}
          target="_blank"
          rel="noopener noreferrer"
          className="block border border-border/50 rounded px-2 py-1.5 hover:border-accent/30 transition"
        >
          <div className="text-[11px] text-zinc-200 truncate">{s.title}</div>
          <div className="flex gap-2 text-[10px] text-zinc-500 mt-0.5">
            <span>{s.year || "?"}</span>
            <span>{s.citations} cites</span>
            {s.pattern && s.pattern !== "none" && (
              <span className="text-accent/70">{s.pattern}</span>
            )}
            {s.classical && <span className="text-amber-400/70">classical</span>}
          </div>
        </a>
      ))}
    </div>
  );
}
