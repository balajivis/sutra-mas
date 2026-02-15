"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";

interface PatternRow {
  pattern: string;
  count: number;
}

interface MissingRow {
  concept: string;
  count: number;
}

interface AnalysisData {
  patterns: PatternRow[];
  analyzedCount: number;
  missingClassical: MissingRow[];
  mergedMap?: Record<string, string[]>;
}

const BAR_COLORS: Record<string, string> = {
  hierarchical: "#22d3ee",
  hybrid: "#e879f9",
  none: "#71717a",
  peer: "#60a5fa",
  supervisor: "#34d399",
  blackboard: "#fbbf24",
  auction: "#818cf8",
  contract_net: "#f87171",
  stigmergy: "#a78bfa",
  debate: "#f472b6",
  bdi: "#4ade80",
  generator_critic: "#fb923c",
  other: "#52525b",
};

function getColor(pattern: string): string {
  return BAR_COLORS[pattern] || "#34d399";
}

/** Build the pattern query param — includes merged variant names */
function patternParam(pattern: string, mergedMap?: Record<string, string[]>): string {
  const variants = mergedMap?.[pattern];
  if (variants && variants.length > 0) {
    return [pattern, ...variants].join(",");
  }
  return pattern;
}

export function AnalysisCard() {
  const [data, setData] = useState<AnalysisData | null>(null);

  const load = useCallback(async () => {
    try {
      const res = await fetch("/api/analysis");
      setData(await res.json());
    } catch {
      // ignore
    }
  }, []);

  useEffect(() => {
    load();
    const iv = setInterval(load, 15_000);
    return () => clearInterval(iv);
  }, [load]);

  if (!data || data.patterns.length === 0) return null;

  const maxCount = Math.max(...data.patterns.map((p) => p.count), 1);

  return (
    <div
      className="rounded-lg border border-border p-4"
      style={{ background: "var(--card)" }}
    >
      <h2 className="text-[11px] uppercase tracking-[1.5px] text-accent mb-3 pb-1.5 border-b border-border">
        Deep Analysis (Agent 3/3b) &mdash; {data.analyzedCount} papers
      </h2>

      <div className="text-[10px] uppercase tracking-[1px] text-dim mb-2">
        Coordination Patterns
      </div>

      <table className="w-full border-collapse">
        <tbody>
          {data.patterns.map((p) => {
            const pct = ((p.count / maxCount) * 100).toFixed(1);
            const color = getColor(p.pattern);
            const merged = data.mergedMap?.[p.pattern];
            const href = `/papers?pattern=${encodeURIComponent(patternParam(p.pattern, data.mergedMap))}`;

            return (
              <tr key={p.pattern} className="group">
                <td className="py-[3px] pr-2 text-xs whitespace-nowrap">
                  <Link
                    href={href}
                    className="hover:underline transition-colors"
                    style={{ color: "var(--text)" }}
                    title={merged ? `Includes: ${merged.join(", ")}` : undefined}
                  >
                    {p.pattern === "null" ? (
                      <span className="text-dim italic">null</span>
                    ) : (
                      p.pattern.replace(/_/g, " ")
                    )}
                    {merged && merged.length > 0 && (
                      <span className="text-dim text-[10px] ml-1">
                        +{merged.length}
                      </span>
                    )}
                  </Link>
                </td>
                <td className="py-[3px] pr-2 text-xs text-right tabular-nums font-semibold w-12">
                  <Link href={href} className="hover:underline" style={{ color: "var(--text)" }}>
                    {p.count}
                  </Link>
                </td>
                <td className="py-[3px] w-[45%]">
                  <Link href={href} className="block">
                    <div
                      className="h-3 rounded-sm overflow-hidden"
                      style={{ background: "var(--border)" }}
                    >
                      <div
                        className="h-full rounded-sm transition-[width] duration-400"
                        style={{
                          width: `${pct}%`,
                          background: `linear-gradient(90deg, ${color}99, ${color})`,
                        }}
                      />
                    </div>
                  </Link>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

export function LostCanaryCard() {
  const [data, setData] = useState<AnalysisData | null>(null);

  const load = useCallback(async () => {
    try {
      const res = await fetch("/api/analysis");
      setData(await res.json());
    } catch {
      // ignore
    }
  }, []);

  useEffect(() => {
    load();
    const iv = setInterval(load, 15_000);
    return () => clearInterval(iv);
  }, [load]);

  if (!data || data.missingClassical.length === 0) return null;

  const maxCount = Math.max(...data.missingClassical.map((m) => m.count), 1);

  return (
    <div
      className="rounded-lg border border-border p-4"
      style={{ background: "var(--card)" }}
    >
      <h2
        className="text-[11px] uppercase tracking-[1.5px] mb-3 pb-1.5 border-b border-border"
        style={{ color: "var(--amber)" }}
      >
        Lost Canary Signal &mdash; Missing Classical Concepts
      </h2>

      <div className="space-y-1.5">
        {data.missingClassical.map((m, i) => (
          <Link
            key={i}
            href={`/papers?q=${encodeURIComponent(m.concept)}`}
            className="flex items-center gap-2 group"
          >
            <span className="text-[11px] text-text w-[140px] shrink-0 truncate group-hover:text-amber-400 transition">
              {m.concept}
            </span>
            <div className="flex-1 h-4 bg-zinc-900 rounded overflow-hidden">
              <div
                className="h-full rounded group-hover:opacity-80 transition"
                style={{
                  width: `${(m.count / maxCount) * 100}%`,
                  background: "var(--amber)",
                  opacity: 0.6,
                }}
              />
            </div>
            <span className="text-[11px] text-dim tabular-nums w-8 text-right">
              {m.count}
            </span>
          </Link>
        ))}
      </div>
    </div>
  );
}
