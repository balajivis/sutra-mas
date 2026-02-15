"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";

const FEAS: Record<number, string> = {
  1: "Very hard",
  2: "Hard",
  3: "Moderate",
  4: "Feasible",
  5: "Easy",
};

interface FeasRow { score: number; count: number }
interface GenRow { gen: number; count: number }

export function ScoutCard() {
  const [data, setData] = useState<{
    with_code: number;
    without_code: number;
    feasibility: FeasRow[];
    generations: GenRow[];
  } | null>(null);

  const load = useCallback(async () => {
    try {
      const res = await fetch("/api/scout");
      if (res.ok) setData(await res.json());
    } catch { /* ignore */ }
  }, []);

  useEffect(() => {
    load();
    const iv = setInterval(load, 15_000);
    return () => clearInterval(iv);
  }, [load]);

  if (!data) return null;

  const maxFeas = Math.max(...data.feasibility.map((f) => f.count), 1);
  const maxGen = Math.max(...data.generations.map((g) => g.count), 1);
  const showGenerations = data.generations.length > 1 || data.generations.some((g) => g.gen > 0);

  return (
    <div className="space-y-3">
      {/* Scout + Feasibility */}
      <div className="border border-border rounded-lg p-4">
        <h3 className="text-[10px] uppercase tracking-widest text-accent font-semibold mb-3">
          Scout + Feasibility (Agents 4-5)
        </h3>

        <div className="flex gap-6 mb-4">
          <Link href="/papers?has_code=true&min_relevance=0" className="group">
            <span className="text-xs text-dim group-hover:text-text transition">With code: </span>
            <span className="text-sm font-bold text-emerald-400">{data.with_code.toLocaleString()}</span>
          </Link>
          <Link href="/papers?has_code=false&min_relevance=0" className="group">
            <span className="text-xs text-dim group-hover:text-text transition">No code: </span>
            <span className="text-sm font-bold text-zinc-400">{data.without_code.toLocaleString()}</span>
          </Link>
        </div>

        {data.feasibility.length > 0 && (
          <div className="space-y-1.5">
            {data.feasibility.map((f) => (
              <Link
                key={f.score}
                href={`/papers?feasibility=${f.score}&min_relevance=0`}
                className="flex items-center gap-2 text-xs group"
              >
                <span className="w-28 text-dim shrink-0 group-hover:text-text transition">
                  {f.score}/5 {FEAS[f.score] || "?"}
                </span>
                <div className="flex-1 h-4 bg-zinc-900 rounded overflow-hidden">
                  <div
                    className="h-full rounded group-hover:opacity-80 transition"
                    style={{
                      width: `${(f.count / maxFeas) * 100}%`,
                      backgroundColor: f.score >= 4 ? "#34d399" : f.score === 3 ? "#fbbf24" : "#ef4444",
                    }}
                  />
                </div>
                <span className="w-12 text-right tabular-nums text-dim font-mono">
                  {f.count.toLocaleString()}
                </span>
              </Link>
            ))}
          </div>
        )}
      </div>

      {/* Feedback Generations */}
      {showGenerations && (
        <div className="border border-border rounded-lg p-4">
          <h3 className="text-[10px] uppercase tracking-widest text-accent font-semibold mb-3">
            Feedback Generations
          </h3>
          <div className="space-y-1.5">
            {data.generations.map((g) => (
              <div key={g.gen} className="flex items-center gap-2 text-xs">
                <span className="w-20 text-dim shrink-0">
                  {g.gen === 0 ? "Original" : `Gen ${g.gen}`}
                </span>
                <div className="flex-1 h-4 bg-zinc-900 rounded overflow-hidden">
                  <div
                    className="h-full bg-cyan-500 rounded"
                    style={{ width: `${(g.count / maxGen) * 100}%` }}
                  />
                </div>
                <span className="w-16 text-right tabular-nums text-dim font-mono">
                  {g.count.toLocaleString()}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
