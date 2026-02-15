"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import type { Insight } from "@/lib/types";

const TYPE_STYLES: Record<string, { color: string; bg: string; icon: string }> = {
  lost_canary: { color: "#fbbf24", bg: "rgba(251,191,36,0.1)", icon: "&#x1F426;" },
  pattern_distribution: { color: "#34d399", bg: "rgba(52,211,153,0.1)", icon: "&#x1F4CA;" },
  grounding_gaps: { color: "#f87171", bg: "rgba(248,113,113,0.1)", icon: "&#x26A0;" },
  rosetta_entries: { color: "#60a5fa", bg: "rgba(96,165,250,0.1)", icon: "&#x1F5FA;" },
  cross_era_bridges: { color: "#a78bfa", bg: "rgba(167,139,250,0.1)", icon: "&#x1F309;" },
};

export function InsightsPanel() {
  const [insights, setInsights] = useState<Insight[]>([]);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState<number | null>(null);

  useEffect(() => {
    setLoading(true);
    fetch("/api/insights")
      .then((r) => r.json())
      .then((data) => {
        if (Array.isArray(data)) setInsights(data);
        else if (data.error) setInsights([]);
      })
      .catch(() => setInsights([]))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full text-dim text-xs">
        <span className="animate-pulse-dot inline-block w-2 h-2 rounded-full bg-accent mr-2" />
        Synthesizing insights from {">"}960 analyzed papers...
      </div>
    );
  }

  if (insights.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-dim text-xs">
        No insights generated yet. Ensure papers have been analyzed by Agent 3b.
      </div>
    );
  }

  return (
    <div className="overflow-y-auto h-full px-3 py-2 space-y-2">
      {insights.map((insight, i) => {
        const style = TYPE_STYLES[insight.type] || TYPE_STYLES.pattern_distribution;
        const synth = insight.synthesis;

        return (
          <div
            key={i}
            className="border rounded-lg px-3 py-2 cursor-pointer transition hover:border-opacity-60"
            style={{
              borderColor: style.color + "40",
              background: style.bg,
            }}
            onClick={() => setExpanded(expanded === i ? null : i)}
          >
            <div className="flex items-start gap-2">
              <span
                className="text-sm mt-0.5"
                dangerouslySetInnerHTML={{ __html: style.icon }}
              />
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <span
                    className="text-[10px] font-semibold uppercase tracking-wider"
                    style={{ color: style.color }}
                  >
                    {insight.type.replace(/_/g, " ")}
                  </span>
                  <span className="text-[10px] text-zinc-600">
                    {insight.count} items
                  </span>
                  {synth?.significance === "high" && (
                    <span className="text-[9px] font-bold text-red-400">HIGH</span>
                  )}
                  <Link
                    href={`/insight/${insight.type}`}
                    className="text-[10px] text-accent/60 hover:text-accent transition ml-auto"
                    onClick={(e) => e.stopPropagation()}
                  >
                    Full view &#x2197;
                  </Link>
                </div>
                <div className="text-xs text-zinc-200 font-medium">
                  {synth?.title || insight.title}
                </div>
                {(synth?.content || insight.content) && (
                  <div className="text-[11px] text-zinc-400 mt-1 leading-relaxed">
                    {synth?.content || (typeof insight.content === 'string' ? insight.content.slice(0, 200) : '')}
                  </div>
                )}
              </div>
            </div>

            {expanded === i && (
              <div className="mt-3 pt-2 border-t border-border/50 space-y-2">
                {synth?.questions && synth.questions.length > 0 && (
                  <div>
                    <div className="text-[10px] text-zinc-600 uppercase tracking-wider mb-1">
                      Follow-up questions
                    </div>
                    {synth.questions.map((q, qi) => (
                      <div key={qi} className="text-[11px] text-zinc-400 pl-2 border-l border-accent/30 mb-1">
                        {q}
                      </div>
                    ))}
                  </div>
                )}
                {insight.type === "lost_canary" && insight.data && insight.data.length > 0 ? (
                  <div>
                    <div className="text-[10px] text-zinc-600 uppercase tracking-wider mb-1">
                      Classical concepts missing from modern papers
                    </div>
                    <div className="space-y-1.5 max-h-52 overflow-y-auto">
                      {(() => {
                        const maxCnt = Math.max(...insight.data.map(d => Number(d.cnt) || 0));
                        return insight.data.map((item, di) => {
                          const cnt = Number(item.cnt) || 0;
                          const pct = maxCnt > 0 ? (cnt / maxCnt) * 100 : 0;
                          const papers = Array.isArray(item.example_papers)
                            ? (item.example_papers as string[]).filter(Boolean).slice(0, 2)
                            : [];
                          return (
                            <div key={di}>
                              <div className="flex items-center gap-2">
                                <span className="text-[10px] text-zinc-300 w-28 shrink-0 truncate">
                                  {String(item.concept)}
                                </span>
                                <div className="flex-1 h-3 bg-zinc-800 rounded-sm overflow-hidden">
                                  <div
                                    className="h-full rounded-sm"
                                    style={{
                                      width: `${pct}%`,
                                      background: `linear-gradient(90deg, ${style.color}80, ${style.color})`,
                                    }}
                                  />
                                </div>
                                <span className="text-[10px] text-zinc-400 w-10 text-right shrink-0">
                                  {cnt}
                                </span>
                              </div>
                              {papers.length > 0 && (
                                <div className="text-[9px] text-zinc-600 ml-28 pl-2 truncate">
                                  e.g. {papers.join("; ")}
                                </div>
                              )}
                            </div>
                          );
                        });
                      })()}
                    </div>
                  </div>
                ) : insight.data && insight.data.length > 0 ? (
                  <div>
                    <div className="text-[10px] text-zinc-600 uppercase tracking-wider mb-1">
                      Evidence ({insight.data.length} items)
                    </div>
                    <div className="space-y-1 max-h-40 overflow-y-auto">
                      {insight.data.slice(0, 8).map((item, di) => (
                        <div key={di} className="text-[10px] text-zinc-500 truncate">
                          {JSON.stringify(item).slice(0, 120)}
                        </div>
                      ))}
                    </div>
                  </div>
                ) : null}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
