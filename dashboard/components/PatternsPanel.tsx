"use client";

import { useState, useEffect } from "react";
import type { PatternSummary } from "@/lib/types";

const PATTERN_COLORS: Record<string, string> = {
  supervisor: "#34d399",
  peer: "#60a5fa",
  blackboard: "#fbbf24",
  stigmergy: "#a78bfa",
  hierarchical: "#22d3ee",
  debate: "#f472b6",
  generator_critic: "#fb923c",
  contract_net: "#f87171",
  bdi: "#4ade80",
  auction: "#818cf8",
  hybrid: "#e879f9",
  flat: "#71717a",
};

export function PatternsPanel() {
  const [patterns, setPatterns] = useState<PatternSummary[]>([]);
  const [stats, setStats] = useState<Record<string, number>>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("/api/patterns")
      .then((r) => r.json())
      .then((data) => {
        setPatterns(data.patterns || []);
        setStats(data.stats || {});
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full text-dim text-xs">
        Loading patterns...
      </div>
    );
  }

  const maxTotal = Math.max(...patterns.map((p) => Number(p.total)), 1);

  return (
    <div className="overflow-y-auto h-full px-3 py-2">
      {/* Quick stats */}
      <div className="flex gap-4 mb-4 text-[10px] text-zinc-500">
        <span>
          <span className="text-zinc-200 font-semibold">{stats.analyzed || 0}</span> analyzed
        </span>
        <span>
          <span className="text-zinc-200 font-semibold">{stats.pattern_count || 0}</span> patterns
        </span>
        <span>
          <span className="text-amber-400 font-semibold">{stats.classical || 0}</span> classical
        </span>
        <span>
          <span className="text-blue-400 font-semibold">{stats.modern || 0}</span> modern
        </span>
      </div>

      {patterns.length === 0 ? (
        <div className="text-dim text-xs text-center py-8">
          No coordination patterns extracted yet. Run Agent 3b.
        </div>
      ) : (
        <div className="space-y-2">
          {patterns.map((p) => {
            const color = PATTERN_COLORS[p.pattern] || "#71717a";
            const pct = ((Number(p.total) / maxTotal) * 100).toFixed(0);
            return (
              <div key={p.pattern} className="group">
                <div className="flex items-center gap-2 mb-1">
                  <span
                    className="inline-block w-2 h-2 rounded-full shrink-0"
                    style={{ background: color }}
                  />
                  <span className="text-xs text-zinc-200 font-medium flex-1">
                    {p.pattern.replace(/_/g, " ")}
                  </span>
                  <span className="text-xs font-semibold tabular-nums" style={{ color }}>
                    {p.total}
                  </span>
                </div>

                {/* Bar */}
                <div className="h-3 bg-border rounded-sm overflow-hidden ml-4">
                  <div className="h-full flex">
                    {Number(p.classical) > 0 && (
                      <div
                        className="h-full"
                        style={{
                          width: `${(Number(p.classical) / Number(p.total)) * Number(pct)}%`,
                          background: "#fbbf24",
                          opacity: 0.7,
                        }}
                      />
                    )}
                    <div
                      className="h-full"
                      style={{
                        width: `${(Number(p.modern) / Number(p.total)) * Number(pct)}%`,
                        background: "#60a5fa",
                        opacity: 0.7,
                      }}
                    />
                    <div
                      className="h-full"
                      style={{
                        width: `${((Number(p.total) - Number(p.classical) - Number(p.modern)) / Number(p.total)) * Number(pct)}%`,
                        background: color,
                        opacity: 0.5,
                      }}
                    />
                  </div>
                </div>

                {/* Meta */}
                <div className="flex gap-3 ml-4 mt-0.5 text-[10px] text-zinc-600">
                  {Number(p.classical) > 0 && (
                    <span>
                      <span className="text-amber-400/80">{p.classical}</span> classical
                    </span>
                  )}
                  {Number(p.modern) > 0 && (
                    <span>
                      <span className="text-blue-400/80">{p.modern}</span> modern
                    </span>
                  )}
                  {Number(p.avg_cites) > 0 && (
                    <span>avg {p.avg_cites} cites</span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Legend */}
      <div className="mt-4 pt-3 border-t border-border text-[10px] text-zinc-600 flex gap-3">
        <span className="flex items-center gap-1">
          <span className="w-2 h-1.5 bg-amber-400/70 rounded-sm inline-block" /> Classical
        </span>
        <span className="flex items-center gap-1">
          <span className="w-2 h-1.5 bg-blue-400/70 rounded-sm inline-block" /> Modern
        </span>
        <span className="flex items-center gap-1">
          <span className="w-2 h-1.5 bg-zinc-500/50 rounded-sm inline-block" /> Transitional
        </span>
      </div>
    </div>
  );
}
