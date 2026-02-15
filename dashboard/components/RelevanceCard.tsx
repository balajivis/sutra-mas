"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";

interface ScoreRow {
  score: number;
  label: string;
  count: number;
  pct: number;
}

interface BranchRow {
  branch: string;
  count: number;
}

interface RelevanceData {
  scores: ScoreRow[];
  scored: number;
  branches: BranchRow[];
}

const SCORE_COLORS: Record<number, string> = {
  1: "#71717a",
  2: "#f87171",
  3: "#fbbf24",
  4: "#34d399",
  5: "#34d399",
};

export function RelevanceCard() {
  const [data, setData] = useState<RelevanceData | null>(null);

  const refresh = useCallback(() => {
    fetch("/api/relevance")
      .then((r) => r.json())
      .then((d) => {
        if (d.scores) setData(d);
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    refresh();
    const iv = setInterval(refresh, 10_000);
    return () => clearInterval(iv);
  }, [refresh]);

  if (!data) {
    return (
      <div className="border border-border rounded-lg p-4 h-64 flex items-center justify-center text-dim text-xs">
        Loading...
      </div>
    );
  }

  const scoreMax = Math.max(...data.scores.map((s) => s.count), 1);
  const branchMax = Math.max(...data.branches.map((b) => b.count), 1);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
      {/* Relevance Scores */}
      <div className="border border-border rounded-lg p-4">
        <h3 className="text-xs font-bold uppercase tracking-widest text-accent mb-3 pb-2 border-b border-border">
          Relevance Scores (Agent 2) &mdash;{" "}
          {data.scored.toLocaleString()} Scored
        </h3>
        <div className="space-y-2">
          {data.scores.map((row) => (
            <Link
              key={row.score}
              href={`/papers?relevance=${row.score}`}
              className="grid items-center gap-x-3 hover:bg-white/[0.03] rounded px-1 -mx-1 transition"
              style={{ gridTemplateColumns: "130px 60px 50px 1fr" }}
            >
              <span className="text-sm text-text">
                {row.score}/5 {row.label}
              </span>
              <span className="text-sm text-text text-right tabular-nums">
                {row.count.toLocaleString()}
              </span>
              <span className="text-sm text-dim text-right tabular-nums">
                {row.pct}%
              </span>
              <div className="h-4 bg-zinc-900 rounded overflow-hidden">
                <div
                  className="h-full rounded"
                  style={{
                    width: `${(row.count / scoreMax) * 100}%`,
                    background: SCORE_COLORS[row.score] || "#71717a",
                    opacity: 0.85,
                  }}
                />
              </div>
            </Link>
          ))}
        </div>
      </div>

      {/* MAS Branches */}
      <div className="border border-border rounded-lg p-4">
        <h3 className="text-xs font-bold uppercase tracking-widest text-accent mb-3 pb-2 border-b border-border">
          MAS Branches
        </h3>
        <div className="space-y-2">
          {data.branches.map((row) => (
            <Link
              key={row.branch}
              href={`/papers?branch=${encodeURIComponent(row.branch)}`}
              className="grid items-center gap-x-3 hover:bg-white/[0.03] rounded px-1 -mx-1 transition"
              style={{ gridTemplateColumns: "130px 1fr 60px" }}
            >
              <span className="text-sm text-text">{row.branch}</span>
              <div className="h-4 bg-zinc-900 rounded overflow-hidden">
                <div
                  className="h-full rounded"
                  style={{
                    width: `${(row.count / branchMax) * 100}%`,
                    background: "#a78bfa",
                    opacity: 0.8,
                  }}
                />
              </div>
              <span className="text-sm text-text text-right tabular-nums">
                {row.count.toLocaleString()}
              </span>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
