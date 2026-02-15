"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";

interface Candidate {
  id: number;
  title: string;
  year: number | null;
  citations: number;
  pattern: string;
  pattern_color: string;
  has_code: boolean;
  feasibility: number | null;
}

interface Stats {
  ready: number;
  needs_work: number;
  pattern_no_code: number;
}

export function ExperimentationCard() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [candidates, setCandidates] = useState<Candidate[]>([]);

  const load = useCallback(async () => {
    try {
      const res = await fetch("/api/experiments");
      if (res.ok) {
        const data = await res.json();
        setStats(data.stats);
        setCandidates(data.candidates);
      }
    } catch {
      /* ignore */
    }
  }, []);

  useEffect(() => {
    load();
    const iv = setInterval(load, 30_000);
    return () => clearInterval(iv);
  }, [load]);

  if (!stats) return null;

  return (
    <div className="border border-border rounded-lg p-4">
      <h3 className="text-[10px] uppercase tracking-widest text-accent font-semibold mb-3">
        Experimentation Candidates
      </h3>

      {/* Stats strip */}
      <div className="flex items-center gap-6 mb-4 text-xs">
        <Link
          href="/papers?has_code=true&feasibility=4,5&min_relevance=4"
          className="group"
        >
          <span className="text-dim group-hover:text-text transition">
            Ready (code + feasible){" "}
          </span>
          <span className="font-bold text-emerald-400 tabular-nums">
            {stats.ready.toLocaleString()}
          </span>
        </Link>
        <Link
          href="/papers?has_code=true&min_relevance=4"
          className="group"
        >
          <span className="text-dim group-hover:text-text transition">
            Has code, needs work{" "}
          </span>
          <span className="font-bold text-amber-400 tabular-nums">
            {stats.needs_work.toLocaleString()}
          </span>
        </Link>
        <span className="text-dim">
          Has pattern (no code){" "}
          <span className="font-bold text-zinc-400 tabular-nums">
            {stats.pattern_no_code.toLocaleString()}
          </span>
        </span>
      </div>

      {/* Candidates table */}
      {candidates.length > 0 && (
        <div className="overflow-y-auto max-h-[280px]">
          <table className="w-full text-xs">
            <thead>
              <tr className="text-[10px] uppercase tracking-widest text-dim">
                <th className="text-left py-1 pr-3 font-normal">Title</th>
                <th className="text-right py-1 px-2 font-normal w-16">Year</th>
                <th className="text-right py-1 px-2 font-normal w-20">Cites</th>
                <th className="text-left py-1 px-2 font-normal w-28">Pattern</th>
                <th className="text-center py-1 px-2 font-normal w-14">Code</th>
                <th className="text-right py-1 pl-2 font-normal w-14">Feas.</th>
              </tr>
            </thead>
            <tbody>
              {candidates.map((c) => (
                <tr key={c.id} className="group border-t border-border/30">
                  <td className="py-1.5 pr-3 max-w-[280px]">
                    <Link
                      href={`/paper/${c.id}`}
                      className="text-text group-hover:text-accent transition truncate block"
                    >
                      {c.title.length > 40
                        ? c.title.slice(0, 40) + "..."
                        : c.title}
                    </Link>
                  </td>
                  <td className="text-right py-1.5 px-2 text-dim tabular-nums">
                    {c.year || "?"}
                  </td>
                  <td className="text-right py-1.5 px-2 text-dim tabular-nums font-semibold">
                    {c.citations.toLocaleString()}
                  </td>
                  <td className="py-1.5 px-2">
                    {c.pattern !== "none" && c.pattern !== "null" && (
                      <span
                        className="inline-block text-[10px] px-1.5 py-0.5 rounded"
                        style={{
                          background: `${c.pattern_color}18`,
                          color: c.pattern_color,
                        }}
                      >
                        {c.pattern.replace(/_/g, " ")}
                      </span>
                    )}
                  </td>
                  <td className="text-center py-1.5 px-2 text-emerald-400">
                    {c.has_code ? "\u2713" : ""}
                  </td>
                  <td className="text-right py-1.5 pl-2 font-bold text-emerald-400">
                    {c.feasibility ? `${c.feasibility}/5` : ""}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
