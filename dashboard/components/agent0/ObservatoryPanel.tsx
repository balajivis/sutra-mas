"use client";

import { useState, useEffect, useCallback } from "react";

interface AgentState {
  id: string;
  name: string;
  status: "idle" | "running" | "blocked" | "done" | "anomaly";
  color: string;
  lastOutput: string;
  processed: number;
  total: number;
  tokens: number;
  latency: number;
  anomaly?: string;
}

interface PipelineStation {
  id: string;
  name: string;
  color: string;
  desc: string;
  input: number;
  active: number;
  done: number;
  total: number;
}

const STATUS_STYLES: Record<string, { bg: string; text: string; label: string }> = {
  idle: { bg: "#27272a22", text: "#71717a", label: "IDLE" },
  running: { bg: "", text: "", label: "RUNNING" },
  blocked: { bg: "#f8717122", text: "#f87171", label: "BLOCKED" },
  done: { bg: "#71717a22", text: "#71717a", label: "DONE" },
  anomaly: { bg: "#f8717144", text: "#f87171", label: "ANOMALY" },
};

function formatTokens(n: number) {
  if (n === 0) return "\u2014";
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(0)}K`;
  return String(n);
}

function formatLatency(ms: number) {
  if (ms === 0) return "\u2014";
  if (ms >= 1000) return `${(ms / 1000).toFixed(1)}s`;
  return `${ms}ms`;
}

function stationToAgent(s: PipelineStation): AgentState {
  let status: AgentState["status"] = "idle";
  if (s.active > 0) status = "running";
  else if (s.done >= s.total && s.total > 0) status = "done";
  else if (s.input > 0 && s.active === 0 && s.done < s.total) status = "blocked";

  // Build a descriptive last output
  let lastOutput = s.desc;
  if (status === "running") {
    lastOutput = `Processing ${s.active} papers \u2014 ${s.desc}`;
  } else if (status === "done") {
    lastOutput = `Completed: ${s.done.toLocaleString()} papers processed`;
  } else if (status === "blocked") {
    lastOutput = `${s.input} papers waiting \u2014 ${s.desc}`;
  }

  return {
    id: s.id.replace("Agent ", "A"),
    name: s.name,
    status,
    color: s.color,
    lastOutput,
    processed: s.done,
    total: s.total,
    tokens: 0, // not tracked per-agent from this API
    latency: 0,
  };
}

export function ObservatoryPanel() {
  const [agents, setAgents] = useState<AgentState[]>([]);
  const [expandedAgent, setExpandedAgent] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastFetch, setLastFetch] = useState<Date | null>(null);

  const fetchPipeline = useCallback(async () => {
    try {
      const res = await fetch("/api/pipeline");
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();

      // Add Agent 0 (Human) at the top
      const humanAgent: AgentState = {
        id: "A0",
        name: "Human (You)",
        status: "running",
        color: "#34d399",
        lastOutput: "Reviewing pipeline via Agent 0 Console",
        processed: 0,
        total: 0,
        tokens: 0,
        latency: 0,
      };

      const pipelineAgents = (data.stations as PipelineStation[]).map(stationToAgent);
      setAgents([humanAgent, ...pipelineAgents]);
      setError(null);
      setLastFetch(new Date());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to fetch");
    } finally {
      setLoading(false);
    }
  }, []);

  // Initial fetch + 30s polling
  useEffect(() => {
    fetchPipeline();
    const interval = setInterval(fetchPipeline, 30000);
    return () => clearInterval(interval);
  }, [fetchPipeline]);

  const totalProcessed = agents.reduce((s, a) => s + a.processed, 0);
  const activeCount = agents.filter((a) => a.status === "running").length;
  const anomalyCount = agents.filter(
    (a) => a.status === "anomaly" || a.anomaly
  ).length;
  const blockedCount = agents.filter((a) => a.status === "blocked").length;

  if (loading && agents.length === 0) {
    return (
      <div className="flex flex-col h-full items-center justify-center">
        <div className="text-[10px] text-dim animate-pulse">Loading pipeline...</div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="px-3 py-2 border-b border-border">
        <div className="text-[10px] text-dim uppercase tracking-wider flex items-center gap-2">
          Observatory
          <span className="text-accent">P5</span>
          {error && <span className="text-red-400 normal-case">{error}</span>}
        </div>
        <div className="flex items-center gap-3 mt-1 text-[10px]">
          <span className="text-accent">{activeCount} active</span>
          {blockedCount > 0 && (
            <span className="text-amber-400">{blockedCount} blocked</span>
          )}
          {anomalyCount > 0 && (
            <span className="text-red-400">{anomalyCount} anomaly</span>
          )}
          <span className="text-dim">{totalProcessed.toLocaleString()} processed</span>
        </div>
      </div>

      {/* Agent list */}
      <div className="flex-1 overflow-y-auto px-2 py-1 space-y-0.5">
        {agents.map((a) => {
          const style = STATUS_STYLES[a.status];
          const isExpanded = expandedAgent === a.id;
          const pct =
            a.total > 0 ? Math.round((a.processed / a.total) * 100) : 0;
          const statusBg =
            a.status === "running" ? a.color + "22" : style.bg;
          const statusText =
            a.status === "running" ? a.color : style.text;

          return (
            <div key={a.id}>
              <div
                className="flex items-center gap-2 px-2 py-1.5 rounded cursor-pointer transition hover:bg-white/[0.03]"
                onClick={() =>
                  setExpandedAgent(isExpanded ? null : a.id)
                }
              >
                {/* Status dot */}
                <span
                  className={`w-2 h-2 rounded-full shrink-0 ${
                    a.status === "running" ? "animate-pulse-dot" : ""
                  }`}
                  style={{ background: a.color }}
                />

                {/* Agent ID + Name */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-1.5">
                    <span
                      className="text-xs font-bold"
                      style={{ color: a.color }}
                    >
                      {a.id}
                    </span>
                    <span className="text-[10px] text-dim truncate">
                      {a.name}
                    </span>
                  </div>
                </div>

                {/* Status pill */}
                <span
                  className="text-[9px] font-mono px-1.5 py-0.5 rounded shrink-0"
                  style={{ background: statusBg, color: statusText }}
                >
                  {style.label}
                </span>
              </div>

              {/* Expanded detail */}
              {isExpanded && (
                <div className="ml-6 mr-2 mb-2 px-2 py-1.5 rounded bg-zinc-900/50 border border-border/50 space-y-1.5">
                  {/* Last output */}
                  <div className="text-[10px] text-zinc-300 leading-snug">
                    {a.lastOutput}
                  </div>

                  {/* Progress bar */}
                  {a.total > 0 && (
                    <div>
                      <div className="flex items-center gap-2 text-[9px] text-dim mb-0.5">
                        <span>
                          {a.processed.toLocaleString()}/
                          {a.total.toLocaleString()}
                        </span>
                        <span>{pct}%</span>
                      </div>
                      <div className="h-1.5 rounded bg-zinc-800 overflow-hidden">
                        <div
                          className="h-full rounded transition-[width] duration-1000"
                          style={{
                            width: `${pct}%`,
                            background: a.color,
                          }}
                        />
                      </div>
                    </div>
                  )}

                  {/* Metrics */}
                  <div className="flex gap-3 text-[9px]">
                    <span className="text-dim">
                      Tokens:{" "}
                      <span className="text-zinc-300">
                        {formatTokens(a.tokens)}
                      </span>
                    </span>
                    <span className="text-dim">
                      Latency:{" "}
                      <span className="text-zinc-300">
                        {formatLatency(a.latency)}
                      </span>
                    </span>
                  </div>

                  {/* Anomaly alert */}
                  {a.anomaly && (
                    <div className="flex items-start gap-1.5 px-2 py-1 rounded bg-red-400/10 border border-red-400/20">
                      <span className="text-red-400 text-[10px] shrink-0 mt-0.5">
                        !!
                      </span>
                      <span className="text-[10px] text-red-300 leading-snug">
                        {a.anomaly}
                      </span>
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Bottom: cost summary */}
      <div className="px-3 py-2 border-t border-border text-[9px] text-dim">
        <div className="flex justify-between">
          <span>Total processed</span>
          <span className="text-zinc-300">
            {totalProcessed.toLocaleString()}
          </span>
        </div>
        <div className="flex justify-between mt-0.5">
          <span>Last updated</span>
          <span className="text-zinc-300">
            {lastFetch ? lastFetch.toLocaleTimeString() : "\u2014"}
          </span>
        </div>
      </div>
    </div>
  );
}
